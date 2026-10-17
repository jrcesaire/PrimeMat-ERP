"""
API Comptabilité — configuration OHADA (paramètres, exercices, taux de change).

Phase 1 du PRD (« Configuration société ») : paramètres par pays OHADA,
exercices comptables (clôture / état courant), taux de change et contraintes.

Routes préfixées par ``/api/v1/accounting``, isolées par tenant (``company_id``).
"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_company_id
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.accounting.schemas.ohada import (
    ExchangeRateCreate,
    ExchangeRateRead,
    FiscalYearRead,
    OHADACheckConstraint,
    OHADAParameterCreate,
    OHADAParameterRead,
    OHADAParameterUpdate,
)
from app.modules.accounting.services.ohada import OHADAService

router = APIRouter()


# ------------------------------------------------------------------ #
# Paramètres OHADA (configuration par pays)
# ------------------------------------------------------------------ #
@router.get("/ohada/parameters", response_model=list[OHADAParameterRead])
async def list_ohada_parameters(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "view")),
):
    """Liste des paramètres OHADA de l'entreprise."""
    return await OHADAService(session).list_ohada_params(company_id)


@router.post("/ohada/parameters", response_model=OHADAParameterRead, status_code=201)
async def create_ohada_parameter(
    body: OHADAParameterCreate,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "create")),
):
    """Crée un paramètre OHADA pour un pays donné."""
    service = OHADAService(session)
    existing = await service.get_country_default(company_id, body.country_code)
    if existing is not None:
        raise HTTPException(
            status_code=409,
            detail=f"Un paramètre OHADA existe déjà pour le pays {body.country_code}.",
        )
    return await service.create_ohada_param(body, company_id)


@router.put("/ohada/parameters", response_model=OHADAParameterRead)
async def upsert_ohada_parameter(
    body: OHADAParameterCreate,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "edit")),
):
    """Insère ou met à jour le paramètre OHADA du pays (idempotent — wizard)."""
    return await OHADAService(session).upsert_ohada_param(body, company_id)


@router.put("/ohada/parameters/{param_id}", response_model=OHADAParameterRead)
async def update_ohada_parameter(
    param_id: int,
    body: OHADAParameterUpdate,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "edit")),
):
    """Met à jour un paramètre OHADA existant (par identifiant)."""
    service = OHADAService(session)
    try:
        return await service.update_ohada_param(company_id, param_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.get("/ohada/constraints", response_model=OHADACheckConstraint)
async def check_ohada_constraints(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "view")),
):
    """Vérifie les contraintes OHADA (paramètre actif + exercice ouvert unique)."""
    return await OHADAService(session).check_constraints(company_id)


# ------------------------------------------------------------------ #
# Exercices comptables (état courant + clôture)
# ------------------------------------------------------------------ #
@router.get("/fiscal-years/current", response_model=FiscalYearRead | None)
async def get_current_fiscal_year(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "view")),
):
    """Exercice comptable ouvert le plus récent (None si aucun)."""
    return await OHADAService(session).get_fiscal_year(company_id)


@router.post("/fiscal-years/{year_id}/close", response_model=FiscalYearRead)
async def close_fiscal_year(
    year_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "edit")),
):
    """Clôture un exercice comptable ouvert."""
    service = OHADAService(session)
    try:
        return await service.close_fiscal_year(company_id, year_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ------------------------------------------------------------------ #
# Taux de change
# ------------------------------------------------------------------ #
@router.get("/exchange-rates", response_model=list[ExchangeRateRead])
async def list_exchange_rates(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "view")),
):
    """Taux de change de l'entreprise."""
    return await OHADAService(session).list_exchange_rates(company_id)


@router.get("/exchange-rates/{base}/{quote}", response_model=ExchangeRateRead)
async def get_exchange_rate(
    base: str,
    quote: str,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "view")),
):
    """Taux de change entre deux devises (404 si absent)."""
    rate = await OHADAService(session).get_exchange_rate(
        company_id, base.upper(), quote.upper()
    )
    if rate is None:
        raise HTTPException(
            status_code=404,
            detail=f"Taux de change {base}/{quote} introuvable.",
        )
    return rate


@router.put("/exchange-rates", response_model=ExchangeRateRead)
async def upsert_exchange_rate(
    body: ExchangeRateCreate,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "edit")),
):
    """Insère ou met à jour un taux de change (idempotent)."""
    return await OHADAService(session).upsert_exchange_rate(body, company_id)


__all__ = ["router"]
