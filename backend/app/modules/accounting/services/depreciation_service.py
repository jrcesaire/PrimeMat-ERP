"""
Service Amortissements — plans, dotations et comptabilisation (Phase 2 PRD).

Trois responsabilités :

1. **Plan d'amortissement** : ``compute_schedule`` produit une échéance par
   période (linéaire ou dégressif SYSCOHADA) ;
2. **Comptabilisation** : ``post_period`` / ``post_due`` génèrent l'écriture
   ``D 681 (dotations) / C 28x (amortissements)``, idempotente par échéance
   (``source_type="depreciation"`` / ``source_id=depreciation.id``) ;
3. **CRUD** des immobilisations, avec recalcul automatique du plan tant
   qu'aucune dotation n'est comptabilisée.

Le dégressif applique le coefficient SYSCOHADA au taux linéaire (3-4 ans :
1,5 · 5-6 ans : 2 · plus de 6 ans : 2,5) puis **bascule en linéaire** sur la
durée restante dès que le taux linéaire résiduel dépasse le taux dégressif :
le plan se termine ainsi exactement à la valeur résiduelle.
"""

from __future__ import annotations

import calendar
import logging
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounting.models.fixed_asset import Depreciation, FixedAsset
from app.modules.accounting.schemas.fixed_asset import (
    DepreciationRunResult,
    FixedAssetCreate,
    FixedAssetSummary,
    FixedAssetUpdate,
)
from app.modules.accounting.services.journal_service import LedgerService

logger = logging.getLogger(__name__)

__all__ = [
    "DepreciationService",
    "compute_schedule",
    "declining_coefficient",
    "derived_depreciation_account",
]


# ------------------------------------------------------------------ #
# Helpers de calcul
# ------------------------------------------------------------------ #
def round2(value: float | Decimal) -> float:
    """Arrondit à 2 décimales (arrondi commercial)."""
    return float(
        Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    )


def derived_depreciation_account(asset_account: str) -> str:
    """Compte d'amortissement cumulé déduit du compte d'immobilisation.

    Le 2e chiffre de la classe 2 identifie la nature de l'immobilisation
    (1 incorporelle, 2 terrain, 3 bâtiment, 4 matériel, 6 financière) ; le
    compte d'amortissement correspondant est ``28`` + ce chiffre
    (``245`` → ``284``, ``213`` → ``281``).
    """
    if len(asset_account) >= 2 and asset_account.startswith("2"):
        return f"28{asset_account[1]}"
    return "28"


def declining_coefficient(years: int) -> float:
    """Coefficient d'accélération SYSCOHADA selon la durée d'utilité."""
    if years <= 4:
        return 1.5
    if years <= 6:
        return 2.0
    return 2.5


def add_years(value: date, years: int) -> date:
    """Ajoute des années à une date (29 février → 28 février)."""
    try:
        return value.replace(year=value.year + years)
    except ValueError:
        return value.replace(year=value.year + years, day=28)


def add_months(value: date, months: int) -> date:
    """Ajoute des mois à une date, en bornant le jour au dernier du mois."""
    index = value.month - 1 + months
    year = value.year + index // 12
    month = index % 12 + 1
    day = min(value.day, calendar.monthrange(year, month)[1])
    return date(year, month, day)


def last_day_of_month(value: date) -> date:
    """Dernier jour du mois de ``value``."""
    return date(
        value.year, value.month, calendar.monthrange(value.year, value.month)[1]
    )


def _period_date(in_service: date, index: int, monthly: bool) -> date:
    """Date de clôture de la période ``index``.

    - annuel : la veille de l'anniversaire de mise en service ;
    - mensuel : le dernier jour du mois de l'échéance.
    """
    if monthly:
        return last_day_of_month(add_months(in_service, index))
    return add_years(in_service, index) - timedelta(days=1)


def compute_schedule(asset: FixedAsset) -> list[dict]:
    """Plan d'amortissement : une échéance par période.

    - **linéaire annuel** : base / durée ;
    - **linéaire mensuel** : base / (durée × 12) ;
    - **dégressif** (annuel) : taux accéléré sur la VNC, avec basculement en
      linéaire sur la durée restante.

    L'arrondi à 2 décimales est absorbé par la **dernière échéance** : le cumul
    du plan égale exactement la base amortissable.
    """
    base = round2(asset.depreciable_base)
    years = max(int(asset.useful_life_years or 1), 1)
    in_service = asset.in_service_date or asset.acquisition_date
    monthly = asset.periodicity == "monthly"

    if asset.method == "declining":
        # Dégressif : le taux s'applique par exercice → plan annuel.
        count = years
        rate = (1 / years) * declining_coefficient(years)
        raw_amounts: list[float] = []
        net = base
        for index in range(1, years + 1):
            remaining = years - index + 1
            if rate <= 1 / remaining:
                amount = net / remaining  # basculement en linéaire
            else:
                amount = net * rate
            amount = min(amount, net)
            raw_amounts.append(amount)
            net -= amount
        monthly = False
    elif monthly:
        count = years * 12
        raw_amounts = [base / count] * count
    else:
        count = years
        raw_amounts = [base / count] * count

    cost = float(asset.acquisition_cost or 0)
    periods: list[dict] = []
    accumulated = 0.0
    for index, raw in enumerate(raw_amounts, start=1):
        amount = round2(base - accumulated) if index == count else round2(raw)
        opening = round2(base - accumulated)
        accumulated = round2(accumulated + amount)
        periods.append(
            {
                "period_index": index,
                "period_date": _period_date(in_service, index, monthly),
                "opening_value": opening,
                "amount": amount,
                "accumulated": accumulated,
                "net_value": round2(cost - accumulated),
            }
        )
    return periods


# ------------------------------------------------------------------ #
# Service
# ------------------------------------------------------------------ #
class DepreciationService:
    """Immobilisations et amortissements (SYSCOHADA)."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.ledger = LedgerService(session)

    # ------------------------------------------------------------------ #
    # Lecture
    # ------------------------------------------------------------------ #
    async def list_assets(
        self, company_id: int, status: str | None = None
    ) -> list[FixedAsset]:
        """Immobilisations de l'entreprise, triées par code."""
        stmt = (
            select(FixedAsset)
            .where(FixedAsset.company_id == company_id)
            .order_by(FixedAsset.code)
        )
        if status:
            stmt = stmt.where(FixedAsset.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_asset(self, company_id: int, asset_id: int) -> FixedAsset:
        """Immobilisation (le plan d'amortissement est chargé en selectin)."""
        result = await self.session.execute(
            select(FixedAsset).where(
                FixedAsset.company_id == company_id, FixedAsset.id == asset_id
            )
        )
        asset = result.scalar_one_or_none()
        if asset is None:
            raise ValueError(f"Immobilisation {asset_id} introuvable.")
        return asset

    # ------------------------------------------------------------------ #
    # Validation
    # ------------------------------------------------------------------ #
    @staticmethod
    def _validate_state(asset: FixedAsset) -> None:
        """Contrôles de cohérence avant enregistrement."""
        cost = float(asset.acquisition_cost or 0)
        residual = float(asset.residual_value or 0)
        if cost <= 0:
            raise ValueError("La valeur d'acquisition doit être supérieure à zéro.")
        if residual >= cost:
            raise ValueError(
                "La valeur résiduelle doit être inférieure à la valeur "
                "d'acquisition."
            )
        if int(asset.useful_life_years or 0) <= 0:
            raise ValueError("La durée d'utilité doit être d'au moins un an.")
        if asset.method == "declining" and asset.periodicity == "monthly":
            raise ValueError(
                "L'amortissement dégressif n'accepte que la périodicité annuelle."
            )

    async def _assert_accounts_exist(
        self, company_id: int, asset: FixedAsset
    ) -> None:
        """Vérifie comptes et journal : sans eux, aucune dotation ne pourrait
        jamais être comptabilisée."""
        from app.modules.accounting.models.journal import Journal
        from app.modules.accounting.services.account_service import AccountService

        accounts = {
            a.code
            for a in await AccountService(self.session).list_accounts(
                company_id, active_only=False, limit=2000
            )
        }
        for label, code in (
            ("compte d'immobilisation", asset.asset_account),
            ("compte d'amortissement", asset.depreciation_account),
            ("compte de dotation", asset.expense_account),
        ):
            if code not in accounts:
                raise ValueError(
                    f"Le {label} « {code} » est introuvable dans le plan comptable."
                )

        journal = await self.session.execute(
            select(Journal).where(
                Journal.company_id == company_id,
                Journal.code == asset.journal_code,
            )
        )
        if journal.scalar_one_or_none() is None:
            raise ValueError(f"Journal « {asset.journal_code} » introuvable.")

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #
    async def create_asset(
        self, company_id: int, data: FixedAssetCreate
    ) -> FixedAsset:
        """Crée une immobilisation et génère son plan d'amortissement."""
        code = data.code.strip()
        duplicate = await self.session.execute(
            select(FixedAsset.id).where(
                FixedAsset.company_id == company_id, FixedAsset.code == code
            )
        )
        if duplicate.scalar_one_or_none() is not None:
            raise ValueError(
                f"Une immobilisation avec le code « {code} » existe déjà."
            )

        payload = data.model_dump()
        payload["code"] = code
        payload["asset_account"] = data.asset_account.strip()
        payload["in_service_date"] = data.in_service_date or data.acquisition_date
        payload["depreciation_account"] = (
            data.depreciation_account.strip()
            or derived_depreciation_account(payload["asset_account"])
        )
        asset = FixedAsset(company_id=company_id, status="active", **payload)
        self._validate_state(asset)
        await self._assert_accounts_exist(company_id, asset)

        self.session.add(asset)
        await self.session.flush()
        await self._generate_schedule(asset)
        await self.session.commit()
        return await self.get_asset(company_id, asset.id)

    async def update_asset(
        self, company_id: int, asset_id: int, data: FixedAssetUpdate
    ) -> FixedAsset:
        """Met à jour une immobilisation ; le plan est recalculé si nécessaire."""
        asset = await self.get_asset(company_id, asset_id)
        update = data.model_dump(exclude_unset=True)

        for key, value in update.items():
            setattr(asset, key, value)
        # Le compte d'amortissement suit le compte d'immobilisation lorsqu'il
        # n'est pas fourni explicitement.
        if "asset_account" in update and "depreciation_account" not in update:
            asset.depreciation_account = derived_depreciation_account(
                asset.asset_account
            )
        if not asset.depreciation_account:
            asset.depreciation_account = derived_depreciation_account(
                asset.asset_account
            )

        self._validate_state(asset)
        await self._assert_accounts_exist(company_id, asset)

        # Tout changement de paramètre d'amortissement impose un nouveau plan.
        schedule_keys = {
            "asset_account",
            "acquisition_cost",
            "residual_value",
            "useful_life_years",
            "method",
            "periodicity",
            "in_service_date",
        }
        if schedule_keys & set(update):
            await self._generate_schedule(asset)

        await self.session.commit()
        return await self.get_asset(company_id, asset.id)

    async def delete_asset(self, company_id: int, asset_id: int) -> None:
        """Supprime une immobilisation (refus si des dotations sont comptabilisées)."""
        asset = await self.get_asset(company_id, asset_id)
        posted = [d for d in asset.depreciations if d.status == "posted"]
        if posted:
            raise ValueError(
                f"{len(posted)} dotation(s) déjà comptabilisée(s) : retirez "
                "d'abord les écritures d'amortissement."
            )
        await self.session.delete(asset)
        await self.session.commit()

    # ------------------------------------------------------------------ #
    # Plan d'amortissement
    # ------------------------------------------------------------------ #
    async def _existing_depreciations(self, asset_id: int) -> list[Depreciation]:
        """Échéances existantes d'une immobilisation, lues explicitement.

        On n'utilise pas la collection ``asset.depreciations`` : sur une
        immobilisation tout juste créée, y accéder déclencherait un chargement
        paresseux — interdit en contexte async (``MissingGreenlet``).
        """
        result = await self.session.execute(
            select(Depreciation).where(Depreciation.asset_id == asset_id)
        )
        return list(result.scalars().all())

    async def _generate_schedule(self, asset: FixedAsset) -> list[Depreciation]:
        """(Re)génère le plan d'amortissement de l'immobilisation.

        Refusé dès qu'une dotation est comptabilisée : modifier un plan déjà
        partiellement comptabilisé fausserait le cumul des amortissements.
        """
        existing = await self._existing_depreciations(asset.id)
        posted = [d for d in existing if d.status == "posted"]
        if posted:
            raise ValueError(
                f"{len(posted)} dotation(s) déjà comptabilisée(s) : le plan "
                "d'amortissement ne peut plus être recalculé."
            )

        # Remplace les échéances prévues.
        for row in existing:
            await self.session.delete(row)
        await self.session.flush()

        rows: list[Depreciation] = []
        for period in compute_schedule(asset):
            row = Depreciation(
                asset_id=asset.id, company_id=asset.company_id, **period
            )
            self.session.add(row)
            rows.append(row)
        await self.session.flush()
        # La collection en mémoire référence les échéances supprimées : on
        # l'expire pour que le prochain accès recharge le plan depuis la base
        # (``expire_on_commit=False`` : la session ne le fait pas d'elle-même).
        self.session.expire(asset, ["depreciations"])
        logger.info(
            "Plan d'amortissement %s : %d échéance(s)", asset.code, len(rows)
        )
        return rows

    async def summary(self, asset: FixedAsset) -> FixedAssetSummary:
        """Synthèse : cumul, VNC, reste à comptabiliser, prochaine échéance."""
        schedule = list(asset.depreciations)
        posted = [d for d in schedule if d.status == "posted"]
        pending = [d for d in schedule if d.status == "planned"]
        accumulated = round2(sum(float(d.amount or 0) for d in posted))
        cost = round2(float(asset.acquisition_cost or 0))
        next_period = (
            min(pending, key=lambda d: d.period_index) if pending else None
        )
        return FixedAssetSummary(
            asset_id=asset.id,
            code=asset.code,
            name=asset.name,
            acquisition_cost=cost,
            residual_value=round2(float(asset.residual_value or 0)),
            depreciable_base=round2(asset.depreciable_base),
            accumulated=accumulated,
            net_value=round2(cost - accumulated),
            posted_count=len(posted),
            periods_count=len(schedule),
            remaining_to_post=round2(sum(float(d.amount or 0) for d in pending)),
            next_amount=(
                round2(float(next_period.amount or 0)) if next_period else None
            ),
            next_period_date=next_period.period_date if next_period else None,
        )

    # ------------------------------------------------------------------ #
    # Comptabilisation des dotations
    # ------------------------------------------------------------------ #
    async def post_period(self, asset: FixedAsset, depreciation: Depreciation):
        """Comptabilise une dotation : ``D 681 / C 28x`` (idempotent).

        Retourne l'écriture créée, ou ``None`` si la dotation l'était déjà.
        """
        if depreciation.status == "posted":
            return None

        amount = round2(float(depreciation.amount or 0))
        if amount <= 0:
            raise ValueError(
                f"Dotation nulle pour la période {depreciation.period_index}."
            )

        from app.modules.accounting.schemas import (
            JournalEntryCreate,
            JournalEntryLineCreate,
        )

        label = (
            f"Dotation {asset.code} — période {depreciation.period_index}"
            f"/{len(asset.depreciations)}"
        )
        entry = await self.ledger.create_entry(
            asset.company_id,
            JournalEntryCreate(
                entry_date=depreciation.period_date,
                journal_code=asset.journal_code or "OD",
                source_type="depreciation",
                source_id=depreciation.id,
                description=(
                    f"Dotation aux amortissements — {asset.name} "
                    f"(période {depreciation.period_index})"
                ),
                lines=[
                    JournalEntryLineCreate(
                        account_code=asset.expense_account,
                        label=label,
                        debit=amount,
                        credit=0,
                    ),
                    JournalEntryLineCreate(
                        account_code=asset.depreciation_account,
                        label=label,
                        debit=0,
                        credit=amount,
                    ),
                ],
            ),
            post=True,
        )
        depreciation.status = "posted"
        depreciation.journal_entry_id = entry.id
        depreciation.posted_at = datetime.utcnow()
        return entry

    async def post_due(
        self, asset: FixedAsset, as_of: date | None = None
    ) -> DepreciationRunResult:
        """Comptabilise toutes les dotations échues non encore comptabilisées.

        Une dotation dont la date tombe dans un exercice **clôturé** est
        ignorée (le verrouillage d'exercice prime) et signalée dans le message.
        """
        cutoff = as_of or date.today()
        pending = [
            d
            for d in asset.depreciations
            if d.status == "planned" and d.period_date <= cutoff
        ]

        posted = 0
        skipped = 0
        total = 0.0
        references: list[str] = []
        errors: list[str] = []

        for depreciation in pending:
            try:
                entry = await self.post_period(asset, depreciation)
            except ValueError as exc:
                skipped += 1
                errors.append(
                    f"période {depreciation.period_index} "
                    f"({depreciation.period_date}) : {exc}"
                )
                continue
            if entry is None:
                skipped += 1
                continue
            posted += 1
            total += float(depreciation.amount or 0)
            references.append(entry.reference)

        if posted:
            await self.session.commit()
            asset = await self.get_asset(asset.company_id, asset.id)

        if not pending:
            message = "Aucune dotation échue à comptabiliser."
        else:
            message = (
                f"{posted} dotation(s) comptabilisée(s) pour "
                f"{round2(total):.2f}."
            )
            if skipped:
                message += f" {skipped} ignorée(s) — " + " · ".join(errors)

        return DepreciationRunResult(
            asset_id=asset.id,
            posted=posted,
            skipped=skipped,
            total_amount=round2(total),
            references=references,
            message=message,
        )
