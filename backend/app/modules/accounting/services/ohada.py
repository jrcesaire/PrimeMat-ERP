
"""
Service OHADA — configuration par pays et gestion de l'exercice comptable.
"""

from __future__ import annotations

import logging
from datetime import date, timedelta
from decimal import Decimal
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounting.models.ohada import OHADAParameter
from app.modules.accounting.models.fiscal_year import FiscalYear
from app.modules.accounting.models.exchange_rate import ExchangeRate
from app.modules.accounting.schemas.ohada import (
    OHADAParameterCreate,
    OHADAParameterUpdate,
    FiscalYearCreate,
    FiscalYearUpdate,
    ExchangeRateCreate,
    OHADACheckConstraint,
)

logger = logging.getLogger(__name__)


class OHADAService:
    """
    Service métier OHADA.

    Activités:
    - Gestion des paramètres OHADA par pays (création, modification, récupération)
    - Gestion des exercices comptables (création, ouverture, clôture)
    - Gestion des taux de change
    - Vérification des contraintes d'OHADA
    """

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------ #
    # Paramètres OHADA
    # ------------------------------------------------------------------ #

    async def get_company_ohada_params(self, company_id: int) -> list[OHADAParameter]:
        """Retourne tous les paramètres OHADA d'une entreprise."""
        result = await self.session.execute(
            select(OHADAParameter).where(OHADAParameter.company_id == company_id)
        )
        return list(result.scalars().all())

    async def get_country_default(
        self, company_id: int, country_code: str
    ) -> Optional[OHADAParameter]:
        """Retourne le paramètre OHADA pour un pays donné, s'il existe."""
        result = await self.session.execute(
            select(OHADAParameter)
            .where(
                OHADAParameter.company_id == company_id,
                OHADAParameter.country_code == country_code,
            )
        )
        return result.scalar_one_or_none()

    async def create_ohada_param(
        self, data: OHADAParameterCreate, company_id: int
    ) -> OHADAParameter:
        """Crée un paramètre OHADA."""
        param = OHADAParameter(company_id=company_id, **data.model_dump())
        self.session.add(param)
        await self.session.commit()
        await self.session.refresh(param)
        return param

    async def update_ohada_param(
        self, company_id: int, parameter_id: int, data: OHADAParameterUpdate
    ) -> OHADAParameter:
        """Met à jour un paramètre OHADA."""
        param = await self._get_ohada_param(company_id, parameter_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(param, key, value)
        await self.session.commit()
        await self.session.refresh(param)
        return param

    async def list_ohada_params(self, company_id: int) -> list[OHADAParameter]:
        """Retourne la liste des paramètres OHADA d'une entreprise."""
        return await self.get_company_ohada_params(company_id)

    async def upsert_ohada_param(
        self, data: OHADAParameterCreate, company_id: int
    ) -> OHADAParameter:
        """Insère ou met à jour un paramètre OHADA selon pays."""
        existing = await self.get_country_default(company_id, data.country_code)
        if existing:
            update_data = data.model_dump(exclude_unset=True)
            for key, value in update_data.items():
                setattr(existing, key, value)
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        return await self.create_ohada_param(data, company_id)
    # ------------------------------------------------------------------ #
    # Exercices comptables
    # ------------------------------------------------------------------ #

    async def get_fiscal_year(self, company_id: int) -> Optional[FiscalYear]:
        """Retourne l'exercice comptable ouvert le plus récent d'une entreprise."""
        result = await self.session.execute(
            select(FiscalYear)
            .where(
                FiscalYear.company_id == company_id,
                FiscalYear.status == "open",
            )
            .order_by(FiscalYear.start_date.desc())
        )
        return result.scalar_one_or_none()

    async def list_fiscal_years(
        self, company_id: int, status: Optional[str] = None
    ) -> list[FiscalYear]:
        """Retourne les exercices comptables d'une entreprise (optionnellement filtrés)."""
        stmt = select(FiscalYear).where(FiscalYear.company_id == company_id)
        if status:
            stmt = stmt.where(FiscalYear.status == status)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_fiscal_year(
        self, data: FiscalYearCreate, company_id: int
    ) -> FiscalYear:
        """Crée un nouvel exercice comptable."""
        year = FiscalYear(
            company_id=company_id,
            status="open",
            **data.model_dump(),
        )
        self.session.add(year)
        await self.session.commit()
        await self.session.refresh(year)
        return year

    async def update_fiscal_year(
        self, company_id: int, year_id: int, data: FiscalYearUpdate
    ) -> FiscalYear:
        """Met à jour un exercice comptable."""
        year = await self._get_fiscal_year(company_id, year_id)
        update_data = data.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            setattr(year, key, value)
        await self.session.commit()
        await self.session.refresh(year)
        return year

    async def close_fiscal_year(self, company_id: int, year_id: int) -> FiscalYear:
        """Clôture un exercice : verrouillage + report à nouveau automatique.

        Déroulé SYSCOHADA :

        1. **Écriture de clôture** (à la date de fin d'exercice) : les comptes
           de charges et de produits (classes 6, 7, 8) sont soldés ; le résultat
           net est porté au crédit de **121** (bénéfice) ou au débit de **129**
           (perte).
        2. **Écriture d'affectation** (premier jour de l'exercice suivant) : le
           résultat est viré au **report à nouveau** — débit 121 / crédit
           **111** pour un bénéfice, débit **119** / crédit 129 pour une perte.
        3. L'exercice passe au statut ``closed`` : toute nouvelle écriture y est
           refusée (verrouillage porté par ``LedgerService``).

        L'exercice suivant est créé automatiquement (année civile) s'il n'existe
        pas encore. Les écritures générées sont idempotentes
        (``source_type``/``source_id``) : rejouer la clôture ne les duplique
        pas. Utilisez ``reopen_fiscal_year`` pour corriger puis re-clôturer.
        """
        from app.modules.accounting.services.journal_service import LedgerService

        year = await self._get_fiscal_year(company_id, year_id)
        if year.status != "open":
            raise ValueError(
                f"L'exercice « {year.name} » est déjà clôturé."
                if year.status == "closed"
                else f"L'exercice « {year.name} » n'est pas ouvert "
                f"(statut {year.status})."
            )

        ledger = LedgerService(self.session)
        plan = await self._pnl_closing_plan(company_id, year)

        # Exercice de report : créé au besoin sur l'année civile suivante.
        next_year = await self._next_fiscal_year(company_id, year)
        if next_year is None:
            next_start = year.end_date + timedelta(days=1)
            next_year = FiscalYear(
                name=f"Exercice {next_start.year}",
                start_date=next_start,
                end_date=date(next_start.year, 12, 31),
                status="open",
                company_id=company_id,
            )
            self.session.add(next_year)
            await self.session.flush()
            logger.info(
                "Exercice suivant créé automatiquement : %s (%s → %s)",
                next_year.name, next_year.start_date, next_year.end_date,
            )
        elif next_year.status == "closed":
            raise ValueError(
                f"L'exercice suivant « {next_year.name} » est déjà clôturé : "
                "impossible d'y reporter le résultat."
            )

        # 1. Clôture (soldage des charges et produits) puis 2. affectation
        await self._post_closing_entry(company_id, year, plan, ledger)
        await self._post_retained_entry(
            company_id, year, plan, next_year, ledger
        )

        # 3. Verrouillage de l'exercice
        year.status = "closed"
        await self.session.commit()
        await self.session.refresh(year)
        logger.info(
            "Exercice %s clôturé (résultat %s, report sur %s)",
            year.name, plan["result"], next_year.name,
        )
        return year

    async def reopen_fiscal_year(self, company_id: int, year_id: int) -> FiscalYear:
        """Réouvre un exercice clôturé pour permettre une correction.

        Les écritures générées par la clôture (soldage des charges/produits et
        affectation du résultat) sont supprimées : une nouvelle clôture les
        régénérera à partir des soldes à jour, sans doublon. Même logique que
        la remise au brouillon d'un document métier, qui retire son écriture.
        """
        year = await self._get_fiscal_year(company_id, year_id)
        if year.status != "closed":
            raise ValueError(f"L'exercice « {year.name} » n'est pas clôturé.")

        next_year = await self._next_fiscal_year(company_id, year)
        if next_year is not None and next_year.status == "closed":
            raise ValueError(
                f"L'exercice suivant « {next_year.name} » est clôturé : "
                "réouvrez d'abord celui-ci."
            )

        removed = 0
        for source_type in ("fiscal_year_closing", "fiscal_year_opening"):
            entry = await self._find_generated_entry(
                company_id, source_type, year.id
            )
            if entry is not None:
                await self.session.delete(entry)
                removed += 1

        year.status = "open"
        await self.session.commit()
        await self.session.refresh(year)
        logger.info(
            "Exercice %s réouvert (%d écriture(s) de clôture retirée(s))",
            year.name, removed,
        )
        return year

    async def is_fiscal_year_closed(self, company_id: int, year_id: int) -> bool:
        """Vérifie si un exercice comptable est clôturé."""
        year = await self._get_fiscal_year(company_id, year_id)
        return year.status == "closed"

    # ------------------------------------------------------------------ #
    # Clôture d'exercice — verrouillage + report à nouveau automatique
    # ------------------------------------------------------------------ #
    #: Comptes de clôture, désignés par **clé métier** et résolus selon le
    #: référentiel de l'entreprise. Les quatre codes coïncident entre le
    #: SYSCOHADA (``131000`` résultat net, ``121000`` report à nouveau) et le
    #: SYCEBNL (``131000`` excédent, ``121000`` report des excédents).
    RESULT_PROFIT_KEY = "result_profit"
    RESULT_LOSS_KEY = "result_loss"
    RETAINED_CREDIT_KEY = "retained_credit"
    RETAINED_DEBIT_KEY = "retained_debit"
    #: Journal des opérations diverses (créé par ``seed_default_journals``).
    CLOSING_JOURNAL = "OD"
    #: Classes soldées à la clôture (charges et produits).
    PNL_CLASSES = ("6", "7", "8")

    async def _closing_codes(self, company_id: int) -> dict[str, str]:
        """Codes des comptes de clôture du référentiel de l'entreprise."""
        from app.modules.accounting.data import resolve_accounts
        from app.modules.accounting.services.account_service import AccountService

        template = await AccountService(self.session).company_template(company_id)
        aliases = resolve_accounts(template)
        return {
            key: aliases[key]
            for key in (
                self.RESULT_PROFIT_KEY,
                self.RESULT_LOSS_KEY,
                self.RETAINED_CREDIT_KEY,
                self.RETAINED_DEBIT_KEY,
            )
        }

    async def year_pnl_balances(
        self, company_id: int, year: FiscalYear
    ) -> list[dict]:
        """Soldes des comptes de charges/produits (classes 6, 7, 8) de l'exercice."""
        from app.modules.accounting.services.journal_service import LedgerService

        balances = await LedgerService(self.session).account_balances(
            company_id, date_from=year.start_date, date_to=year.end_date
        )
        return [
            b for b in balances if b["account_code"][:1] in self.PNL_CLASSES
        ]

    async def _pnl_closing_plan(self, company_id: int, year: FiscalYear) -> dict:
        """Plan de clôture : lignes de soldage, total et résultat de l'exercice.

        Chaque compte de charges/produits non soldé produit une ligne de sens
        **inverse** de son solde (le solde d'un compte = débit − crédit). La
        contrepartie nette est le **résultat** de l'exercice : le solde des
        classes 6/7/8 est l'opposé du résultat (charges débitrices, produits
        créditeurs), d'où ``result = -Σ(soldes)``.
        """
        from app.modules.accounting.services.account_service import AccountService

        balances = await self.year_pnl_balances(company_id, year)
        accounts = {
            a.code: a
            for a in await AccountService(self.session).list_accounts(
                company_id, active_only=False, limit=2000
            )
        }

        lines: list[dict] = []
        raw_result = Decimal("0")
        for b in balances:
            balance = Decimal(str(b["balance"]))
            if balance == 0:
                continue
            acc = accounts.get(b["account_code"])
            lines.append(
                {
                    "account_code": b["account_code"],
                    "account_name": acc.name if acc else b["account_code"],
                    "class_no": b["account_code"][:1],
                    "balance": float(balance),
                    "debit": float(-balance) if balance < 0 else 0.0,
                    "credit": float(balance) if balance > 0 else 0.0,
                }
            )
            raw_result += balance

        result = -raw_result
        codes = await self._closing_codes(company_id)
        result_account = (
            codes[self.RESULT_PROFIT_KEY]
            if result > 0
            else codes[self.RESULT_LOSS_KEY]
            if result < 0
            else None
        )
        return {
            "lines": lines,
            "result": result,
            "result_account": result_account,
            "total_debit": sum(Decimal(str(l["debit"])) for l in lines),
            "total_credit": sum(Decimal(str(l["credit"])) for l in lines),
        }

    async def _next_fiscal_year(
        self, company_id: int, year: FiscalYear
    ) -> Optional[FiscalYear]:
        """Exercice qui commence après ``year`` (le plus proche), s'il existe."""
        result = await self.session.execute(
            select(FiscalYear)
            .where(
                FiscalYear.company_id == company_id,
                FiscalYear.start_date > year.end_date,
            )
            .order_by(FiscalYear.start_date.asc())
        )
        return result.scalars().first()

    async def _find_generated_entry(
        self, company_id: int, source_type: str, source_id: int
    ):
        """Écriture déjà générée pour cette source (``None`` si absente)."""
        from app.modules.accounting.models.journal_entry import JournalEntry

        result = await self.session.execute(
            select(JournalEntry).where(
                JournalEntry.company_id == company_id,
                JournalEntry.source_type == source_type,
                JournalEntry.source_id == source_id,
            )
        )
        return result.scalars().first()

    async def _ensure_generated_entry(
        self,
        company_id: int,
        source_type: str,
        source_id: int,
        data,
        ledger,
    ) -> Optional[str]:
        """Crée l'écriture générée si elle n'existe pas (idempotent).

        Retourne sa référence (celle de l'écriture existante le cas échéant).
        """
        existing = await self._find_generated_entry(
            company_id, source_type, source_id
        )
        if existing is not None:
            return existing.reference
        entry = await ledger.create_entry(company_id, data, post=True)
        return entry.reference

    async def closing_preview(self, company_id: int, year_id: int) -> dict:
        """Aperçu de la clôture : soldes à solder, résultat et exercice suivant.

        Alimente l'écran de clôture : l'utilisateur voit le résultat de
        l'exercice, les comptes qui seront soldés et l'exercice de report
        (créé automatiquement s'il n'existe pas encore).
        """
        year = await self._get_fiscal_year(company_id, year_id)
        plan = await self._pnl_closing_plan(company_id, year)
        next_year = await self._next_fiscal_year(company_id, year)
        closing = await self._find_generated_entry(
            company_id, "fiscal_year_closing", year.id
        )
        opening = await self._find_generated_entry(
            company_id, "fiscal_year_opening", year.id
        )
        result = plan["result"]
        return {
            "fiscal_year": year,
            "lines": plan["lines"],
            "result": float(result),
            "result_type": (
                "profit" if result > 0 else "loss" if result < 0 else "none"
            ),
            "result_account": plan["result_account"],
            "total_debit": float(plan["total_debit"]),
            "total_credit": float(plan["total_credit"]),
            "next_year": next_year,
            "next_year_will_be_created": next_year is None,
            "closing_entry_reference": closing.reference if closing else None,
            "opening_entry_reference": opening.reference if opening else None,
            "already_closed": year.status == "closed",
        }

    async def _post_closing_entry(
        self, company_id: int, year: FiscalYear, plan: dict, ledger
    ) -> Optional[str]:
        """Écriture de clôture : soldage des charges/produits → résultat."""
        if not plan["lines"]:
            return None

        from app.modules.accounting.schemas import (
            JournalEntryCreate,
            JournalEntryLineCreate,
        )

        result = plan["result"]
        codes = await self._closing_codes(company_id)
        lines = [
            JournalEntryLineCreate(
                account_code=l["account_code"],
                label=f"Solde de clôture — {l['account_name']}",
                debit=l["debit"],
                credit=l["credit"],
            )
            for l in plan["lines"]
        ]
        if result > 0:
            lines.append(
                JournalEntryLineCreate(
                    account_code=codes[self.RESULT_PROFIT_KEY],
                    label=f"Résultat de l'exercice {year.name} (bénéfice)",
                    debit=0,
                    credit=float(result),
                )
            )
        elif result < 0:
            lines.append(
                JournalEntryLineCreate(
                    account_code=codes[self.RESULT_LOSS_KEY],
                    label=f"Résultat de l'exercice {year.name} (perte)",
                    debit=float(-result),
                    credit=0,
                )
            )

        return await self._ensure_generated_entry(
            company_id,
            "fiscal_year_closing",
            year.id,
            JournalEntryCreate(
                entry_date=year.end_date,
                journal_code=self.CLOSING_JOURNAL,
                source_type="fiscal_year_closing",
                source_id=year.id,
                description=f"Clôture de l'exercice {year.name}",
                lines=lines,
            ),
            ledger,
        )

    async def _post_retained_entry(
        self,
        company_id: int,
        year: FiscalYear,
        plan: dict,
        next_year: FiscalYear,
        ledger,
    ) -> Optional[str]:
        """Affectation du résultat au report à nouveau."""
        result = plan["result"]
        if result == 0:
            return None

        from app.modules.accounting.schemas import (
            JournalEntryCreate,
            JournalEntryLineCreate,
        )

        codes = await self._closing_codes(company_id)

        if result > 0:
            lines = [
                JournalEntryLineCreate(
                    account_code=codes[self.RESULT_PROFIT_KEY],
                    label=f"Affectation du résultat {year.name}",
                    debit=float(result),
                    credit=0,
                ),
                JournalEntryLineCreate(
                    account_code=codes[self.RETAINED_CREDIT_KEY],
                    label=f"Report à nouveau — résultat {year.name}",
                    debit=0,
                    credit=float(result),
                ),
            ]
        else:
            lines = [
                JournalEntryLineCreate(
                    account_code=codes[self.RETAINED_DEBIT_KEY],
                    label=f"Report à nouveau — perte {year.name}",
                    debit=float(-result),
                    credit=0,
                ),
                JournalEntryLineCreate(
                    account_code=codes[self.RESULT_LOSS_KEY],
                    label=f"Affectation de la perte {year.name}",
                    debit=0,
                    credit=float(-result),
                ),
            ]

        return await self._ensure_generated_entry(
            company_id,
            "fiscal_year_opening",
            year.id,
            JournalEntryCreate(
                entry_date=next_year.start_date,
                journal_code=self.CLOSING_JOURNAL,
                source_type="fiscal_year_opening",
                source_id=year.id,
                description=(
                    f"Affectation du résultat {year.name} au report à nouveau"
                ),
                lines=lines,
            ),
            ledger,
        )

    # ------------------------------------------------------------------ #
    # Taux de change
    # ------------------------------------------------------------------ #

    async def get_exchange_rate(
        self, company_id: int, base: str, quote: str
    ) -> Optional[ExchangeRate]:
        """Retourne un taux de change spécifique."""
        result = await self.session.execute(
            select(ExchangeRate)
            .where(
                ExchangeRate.company_id == company_id,
                ExchangeRate.base_currency == base,
                ExchangeRate.quote_currency == quote,
            )
        )
        return result.scalar_one_or_none()

    async def upsert_exchange_rate(
        self, data: ExchangeRateCreate, company_id: int
    ) -> ExchangeRate:
        """Insère ou met à jour un taux de change."""
        existing = await self.get_exchange_rate(
            company_id, data.base_currency, data.quote_currency
        )
        if existing:
            existing.rate = data.rate
            await self.session.commit()
            await self.session.refresh(existing)
            return existing
        rate = ExchangeRate(
            company_id=company_id,
            **data.model_dump(),
        )
        self.session.add(rate)
        await self.session.commit()
        await self.session.refresh(rate)
        return rate
    # ------------------------------------------------------------------ #
    # Vérification de contraintes
    # ------------------------------------------------------------------ #

    async def check_constraints(self, company_id: int) -> OHADACheckConstraint:
        """Vérifie les contraintes d'OHADA pour une entreprise."""
        params = await self.get_company_ohada_params(company_id)
        has_params = len(params) > 0
        has_active_param = any(p.is_active for p in params)

        open_years = [
            y for y in await self.list_fiscal_years(company_id) if y.status == "open"
        ]
        has_open_year = len(open_years) > 0
        only_one_open_year = len(open_years) <= 1

        can_open = has_active_param and has_open_year and only_one_open_year
        can_close = has_open_year

        message = ""
        if not has_params:
            message = "Aucun paramètre OHADA configuré."
        elif not has_active_param:
            message = "Aucun paramètre OHADA actif."
        elif not has_open_year:
            message = "Aucun exercice comptable ouvert."
        elif not only_one_open_year:
            message = "Plusieurs exercices comptables ouverts."

        return OHADACheckConstraint(can_open=can_open, message=message)

    # ------------------------------------------------------------------ #
    # Méthodes privées
    # ------------------------------------------------------------------ #

    async def _get_ohada_param(self, company_id: int, param_id: int) -> OHADAParameter:
        """Récupère un paramètre OHADA (vérification de l'appartenance à l'entreprise)."""
        result = await self.session.execute(
            select(OHADAParameter)
            .where(
                OHADAParameter.company_id == company_id,
                OHADAParameter.id == param_id,
            )
        )
        param = result.scalar_one_or_none()
        if param is None:
            raise ValueError(f"Paramètre OHADA {param_id} introuvable pour cette entreprise.")
        return param

    async def _get_fiscal_year(self, company_id: int, year_id: int) -> FiscalYear:
        """Récupère un exercice comptable (vérification de l'appartenance à l'entreprise)."""
        result = await self.session.execute(
            select(FiscalYear)
            .where(
                FiscalYear.company_id == company_id,
                FiscalYear.id == year_id,
            )
        )
        year = result.scalar_one_or_none()
        if year is None:
            raise ValueError(f"Exercice comptable {year_id} introuvable pour cette entreprise.")
        return year

    async def list_exchange_rates(self, company_id: int) -> list[ExchangeRate]:
        """Retourne tous les taux de change de l entreprise."""
        result = await self.session.execute(
            select(ExchangeRate).where(ExchangeRate.company_id == company_id)
        )
        return list(result.scalars().all())
