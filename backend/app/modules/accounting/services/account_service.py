"""
Service Comptabilité — plan comptable OHADA.

Fournit :
- ``seed_ohada_chart`` — insère le plan du référentiel de l'entreprise
  (SYSCOHADA commercial : 1 411 comptes ; SYCEBNL : 1 103 comptes)
- ``seed_default_journals`` — crée les journaux standards (ACH, VTE, BAN, CAI, OD)
- accès comptes (CRUD léger)

Le référentiel est porté par ``Company.chart_of_accounts`` ; le plan et la
codification en découlent (six chiffres dans les deux cas). Le type de compte
(asset / liability / equity / income / expense) est dérivé du code par
``data.account_type_for`` pour alimenter les états financiers (bilan, résultat).
"""

from __future__ import annotations

import logging

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounting.data import (
    ACCOUNT_CHARTS,
    CHART_LABELS,
    account_type_for,
    chart_key,
    get_chart,
    probe_account,
)
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.journal import Journal
from app.shared.enums import ChartOfAccounts

logger = logging.getLogger(__name__)


class ChartChangeBlocked(ValueError):
    """Le référentiel ne peut pas être changé : la comptabilité n'est pas vierge."""


# ------------------------------------------------------------------ #
# Règles de type — dérivation depuis le code OHADA
# ------------------------------------------------------------------ #
# Le registre des plans, la codification significative et le typage des comptes
# sont définis dans ``app.modules.accounting.data``. ``account_type_for`` y est
# importé puis ré-exporté pour les appelants historiques.
#
# Repères de la classe 1 du SYSCOHADA Révisé — ``10`` capital · ``11`` réserves
# · ``12`` report à nouveau · ``13`` résultat · ``14`` subventions
# d'investissement · ``15`` provisions réglementées (capitaux propres) ;
# ``16`` à ``19`` sont des dettes.


DEFAULT_JOURNALS: list[tuple[str, str, str]] = [
    ("VTE", "Ventes", "sale"),
    ("ACH", "Achats", "purchase"),
    ("BAN", "Banque", "bank"),
    ("CAI", "Caisse", "cash"),
    ("PAY", "Paiements reçus", "payment"),
    ("OD", "Opérations diverses", "misc"),
    ("PAI", "Paie", "misc"),
]

#: Nombre maximal de comptes rapatriés lors d'un seed. Les deux référentiels
#: en comptent moins de 1 500 ; la marge couvre les plans enrichis par l'entité.
ACCOUNT_FETCH_LIMIT = 20_000


class AccountService:
    """Accès aux comptes du plan comptable (multi-entreprise)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------ #
    # Lecture
    # ------------------------------------------------------------------ #
    async def list_accounts(
        self,
        company_id: int,
        account_class: str | None = None,
        active_only: bool = True,
        skip: int = 0,
        limit: int = 500,
    ) -> list[Account]:
        stmt = select(Account).where(Account.company_id == company_id)
        if account_class:
            stmt = stmt.where(Account.class_no == account_class)
        if active_only:
            stmt = stmt.where(Account.is_active.is_(True))
        stmt = stmt.order_by(Account.code).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_account(
        self, company_id: int, code: str
    ) -> Account | None:
        result = await self.session.execute(
            select(Account).where(
                Account.company_id == company_id, Account.code == code
            )
        )
        return result.scalar_one_or_none()

    async def get_by_technical_name(
        self, company_id: int, technical_name: str
    ) -> Account | None:
        """Retrouve un compte via son nom technique stable (ex. ``customers``)."""
        result = await self.session.execute(
            select(Account).where(
                Account.company_id == company_id,
                Account.technical_name == technical_name,
            )
        )
        return result.scalar_one_or_none()

    # ------------------------------------------------------------------ #
    # Seed
    # ------------------------------------------------------------------ #
    async def company_template(self, company_id: int) -> str:
        """Référentiel comptable de l'entreprise (commercial par défaut)."""
        from app.core.models.company import Company

        template = (
            await self.session.execute(
                select(Company.chart_of_accounts).where(Company.id == company_id)
            )
        ).scalar_one_or_none()
        return chart_key(template)

    # ------------------------------------------------------------------ #
    # Référentiel comptable
    # ------------------------------------------------------------------ #
    def chart_options(self) -> list[dict]:
        """Référentiels sélectionnables, avec le nombre de comptes apportés."""
        return [
            {"value": key, "label": CHART_LABELS[key], "account_count": len(chart)}
            for key, chart in sorted(ACCOUNT_CHARTS.items())
        ]

    async def chart_state(self, company_id: int) -> dict:
        """Référentiel courant et possibilité de le modifier."""
        template = await self.company_template(company_id)
        blockers = await self.chart_change_blockers(company_id)
        return {
            "chart_of_accounts": template,
            "label": CHART_LABELS.get(template, template),
            "account_count": len(
                await self.list_accounts(
                    company_id, active_only=False, limit=ACCOUNT_FETCH_LIMIT
                )
            ),
            "can_change": not blockers,
            "blockers": blockers,
            "available": self.chart_options(),
        }

    async def chart_change_blockers(self, company_id: int) -> list[str]:
        """Ce qui interdit de changer de référentiel.

        Un changement **remplace** le plan : l'opération n'est légitime que sur
        une comptabilité vierge. On refuse donc dès qu'une écriture, une
        immobilisation ou une déclaration de TVA référence un compte.
        """
        from app.modules.accounting.models.fixed_asset import FixedAsset
        from app.modules.accounting.models.journal_entry import JournalEntry
        from app.modules.accounting.models.vat_return import VATReturn

        blockers: list[str] = []
        watched = (
            (JournalEntry, "écriture"),
            (FixedAsset, "immobilisation"),
            (VATReturn, "déclaration de TVA"),
        )
        for model, noun in watched:
            count = (
                await self.session.execute(
                    select(func.count())
                    .select_from(model)
                    .where(model.company_id == company_id)
                )
            ).scalar_one()
            if count:
                blockers.append(f"{count} {noun}{'s' if count > 1 else ''}")
        return blockers

    async def change_chart(self, company_id: int, template: str) -> dict:
        """Bascule l'entreprise vers un autre référentiel et recharge le plan.

        L'ancien plan est **supprimé** — ses codes ne signifient plus rien dans
        le nouveau référentiel — puis remplacé par celui du référentiel cible.
        """
        from app.core.models.company import Company

        target = chart_key(template)
        get_chart(target)  # valide le référentiel (lève ValueError sinon)

        if target == await self.company_template(company_id):
            return await self.chart_state(company_id)

        blockers = await self.chart_change_blockers(company_id)
        if blockers:
            raise ChartChangeBlocked(
                "Le référentiel ne peut être changé que sur une comptabilité "
                f"vierge — il reste {', '.join(blockers)}."
            )

        company = (
            await self.session.execute(select(Company).where(Company.id == company_id))
        ).scalar_one()
        company.chart_of_accounts = ChartOfAccounts(target)

        for account in await self.list_accounts(
            company_id, active_only=False, limit=ACCOUNT_FETCH_LIMIT
        ):
            await self.session.delete(account)
        await self.session.flush()

        await self.seed_ohada_chart(company_id, target)
        await self.session.flush()

        logger.info(
            "Référentiel comptable de l'entreprise %s basculé vers %s",
            company_id, target,
        )
        return await self.chart_state(company_id)

    async def seed_ohada_chart(
        self,
        company_id: int,
        template: str | None = None,
        refresh_labels: bool = True,
    ) -> int:
        """Insère le plan comptable du référentiel de l'entreprise.

        ``template`` force un référentiel ; à défaut, celui porté par
        ``Company.chart_of_accounts`` est utilisé.

        Idempotent : ne crée que les comptes absents. Si ``refresh_labels`` est
        vrai, met aussi à jour libellés, nom technique et type des comptes
        existants — le code est la clé de référence du référentiel. Retourne le
        nombre de comptes créés.
        """
        chart = get_chart(
            template if template is not None else await self.company_template(company_id)
        )
        by_code = {
            acc.code: acc
            for acc in await self.list_accounts(
                company_id, active_only=False, limit=ACCOUNT_FETCH_LIMIT
            )
        }
        created = updated = 0
        for code, name, technical in chart:
            acc_type = account_type_for(code)
            acc = by_code.get(code)
            if acc is not None:
                if refresh_labels and (
                    acc.name != name or acc.technical_name != technical or acc.account_type != acc_type
                ):
                    acc.name = name
                    acc.technical_name = technical
                    acc.account_type = acc_type
                    updated += 1
                continue
            self.session.add(
                Account(
                    code=code,
                    name=name,
                    class_no=code[0],
                    account_type=acc_type,
                    technical_name=technical,
                    is_group=False,
                    is_active=True,
                    level=1,
                    company_id=company_id,
                )
            )
            created += 1
        if created or updated:
            await self.session.flush()
            logger.info(
                "Plan OHADA : %d comptes insérés, %d mis à jour pour company %s",
                created, updated, company_id,
            )
        return created

    async def ensure_seeded(self, company_id: int) -> int:
        """Garantit que le plan du référentiel courant est chargé.

        Appelé avant toute écriture. Le témoin est le compte de clients du
        référentiel : une entreprise dont le plan date d'une codification
        antérieure (comptes à 2 à 4 chiffres) échoue au test et est rechargée.
        """
        template = await self.company_template(company_id)
        if not await self.get_account(company_id, probe_account(template)):
            return await self.seed_ohada_chart(company_id, template)
        return 0

    # ------------------------------------------------------------------ #
    # Journaux
    # ------------------------------------------------------------------ #
    async def seed_default_journals(self, company_id: int) -> int:
        """Crée les journaux standards SYSCOHADA s'ils sont absents."""
        existing = {
            j.code
            for j in (
                await self.session.execute(
                    select(Journal).where(Journal.company_id == company_id)
                )
            ).scalars()
        }
        created = 0
        for code, name, jtype in DEFAULT_JOURNALS:
            if code in existing:
                continue
            self.session.add(
                Journal(
                    code=code,
                    name=name,
                    journal_type=jtype,
                    is_active=True,
                    company_id=company_id,
                )
            )
            created += 1
        if created:
            await self.session.flush()
        return created


__all__ = ["AccountService", "ChartChangeBlocked", "account_type_for", "DEFAULT_JOURNALS"]