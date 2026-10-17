
"""
Service OHADA — configuration par pays et gestion de l'exercice comptable.
"""

from __future__ import annotations

import logging
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
        """Clôture un exercice comptable s'il est ouvert."""
        year = await self._get_fiscal_year(company_id, year_id)
        if year.status != "open":
            raise ValueError(
                f"L'exercice {year_id} est déjà {'fermé' if year.status == 'closed' else 'dans un état non gérable'}"
            )
        year.status = "closed"
        await self.session.commit()
        await self.session.refresh(year)
        return year

    async def is_fiscal_year_closed(self, company_id: int, year_id: int) -> bool:
        """Vérifie si un exercice comptable est clôturé."""
        year = await self._get_fiscal_year(company_id, year_id)
        return year.status == "closed"
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
