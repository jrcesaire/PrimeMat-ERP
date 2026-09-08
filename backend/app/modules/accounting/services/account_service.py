"""
Service Comptabilité — plan comptable OHADA.

Fournit :
- ``seed_ohada_chart`` — insère le plan complet (637 comptes) pour une entreprise
- ``seed_default_journals`` — crée les journaux standards (ACH, VTE, BAN, CAI, OD)
- accès comptes (CRUD léger)

Le type de compte (asset / liability / equity / income / expense) est dérivé
des règles SYSCOHADA pour alimenter les états financiers (bilan, résultat).
"""

from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounting.data.ohada_chart import OHADA_ACCOUNTS
from app.modules.accounting.models.account import Account
from app.modules.accounting.models.journal import Journal

logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Règles de type — dérivation depuis le code OHADA
# ------------------------------------------------------------------ #
def account_type_for(code: str) -> str:
    """Détermine le type comptable d'un compte depuis son code OHADA."""
    cls = code[0]
    if cls == "1":
        # Capitaux propres vs dettes de capitaux
        if code.startswith(
            ("101", "102", "103", "104", "105", "106", "107", "108",
             "11", "12", "13", "14", "15")
        ):
            return "equity"
        return "liability"
    if cls in ("2", "3"):
        return "asset"
    if cls == "4":
        # Clients / TVA déductible / CCA / avances personnel → actifs
        if code.startswith(("41", "4421", "4422", "4423", "481", "488", "421")):
            return "asset"
        # Dépréciations & comptes transitoires → actifs (contre-valeurs)
        if code.startswith(("49", "47")):
            return "asset"
        return "liability"
    if cls == "5":
        # Crédits de trésorerie = dettes ; dépréciations = contre-actif
        if code.startswith("56"):
            return "liability"
        return "asset"
    if cls == "6":
        return "expense"
    if cls == "7":
        return "income"
    if cls == "8":
        # Charges HAO vs Produits HAO
        if code.startswith(("81", "83", "85", "87", "89")):
            return "expense"
        return "income"
    return "off_balance"


DEFAULT_JOURNALS: list[tuple[str, str, str]] = [
    ("VTE", "Ventes", "sale"),
    ("ACH", "Achats", "purchase"),
    ("BAN", "Banque", "bank"),
    ("CAI", "Caisse", "cash"),
    ("PAY", "Paiements reçus", "payment"),
    ("OD", "Opérations diverses", "misc"),
]
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
    async def seed_ohada_chart(
        self, company_id: int, refresh_labels: bool = True
    ) -> int:
        """Insère le plan comptable OHADA complet pour une entreprise.

        Idempotent : ne crée que les comptes absents. Si ``refresh_labels``
        est vrai, met aussi à jour libellés et types des comptes existants
        (le code est la clé de référence du référentiel). Retourne le nombre
        de comptes créés.
        """
        by_code = {
            acc.code: acc
            for acc in await self.list_accounts(company_id, active_only=False, limit=2000)
        }
        created = updated = 0
        for code, name, technical in OHADA_ACCOUNTS:
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
        """Garantit que le plan est chargé (appelé avant toute écriture)."""
        if not await self.get_account(company_id, "411"):
            return await self.seed_ohada_chart(company_id)
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


__all__ = ["AccountService", "account_type_for", "DEFAULT_JOURNALS"]