"""
API États financiers — balance, compte de résultat, bilan, grand livre, journal.

Endpoints :
- ``GET /financial/balance``         balance générale (soldes par compte)
- ``GET /financial/trial-balance``   balance de vérification (soldes non nuls)
- ``GET /financial/income-statement`` compte de résultat (produits - charges)
- ``GET /financial/balance-sheet``   bilan actif/passif
- ``GET /financial/ledger/{code}``   grand livre d'un compte
- ``GET /financial/journal``         journal général (écritures d'une période)
"""

from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_company_id
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.accounting.services.financial_service import FinancialService
from app.modules.accounting.services.journal_service import LedgerService

router = APIRouter()


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #
async def _parse_date(value: str | None) -> date | None:
    if not value:
        return None
    try:
        return date.fromisoformat(value)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Date invalide : {value}")


# ------------------------------------------------------------------ #
# Balance générale
# ------------------------------------------------------------------ #
@router.get("/financial/balance")
async def balance_report(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    date_from: str | None = Query(default=None, description="Début (YYYY-MM-DD)"),
    date_to: str | None = Query(default=None, description="Fin (YYYY-MM-DD)"),
    _: User = Depends(require_permission("account", "view")),
):
    """Balance générale : soldes débit/crédit par compte."""
    service = FinancialService(session)
    return await service.balance_report(
        company_id,
        date_from=await _parse_date(date_from),
        date_to=await _parse_date(date_to),
    )


# ------------------------------------------------------------------ #
# Balance de vérification
# ------------------------------------------------------------------ #
@router.get("/financial/trial-balance")
async def trial_balance(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "view")),
):
    """Balance de vérification : soldes résiduels non nuls."""
    service = FinancialService(session)
    service = FinancialService(session)
    return await service.trial_balance(company_id)


# ------------------------------------------------------------------ #
# Compte de résultat
# ------------------------------------------------------------------ #
@router.get("/financial/income-statement")
async def income_statement(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    date_from: str | None = Query(default=None, description="Début (YYYY-MM-DD)"),
    date_to: str | None = Query(default=None, description="Fin (YYYY-MM-DD)"),
    _: User = Depends(require_permission("account", "view")),
):
    """Compte de résultat SYSCOHADA (produits - charges)."""
    service = FinancialService(session)
    return await service.income_statement(
        company_id,
        date_from=await _parse_date(date_from),
        date_to=await _parse_date(date_to),
    )


# ------------------------------------------------------------------ #
# Bilan
# ------------------------------------------------------------------ #
@router.get("/financial/balance-sheet")
async def balance_sheet(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    as_of: str | None = Query(default=None, description="Situation au (YYYY-MM-DD)"),
    _: User = Depends(require_permission("account", "view")),
):
    """Bilan SYSCOHADA (actif / passif par grandes masses)."""
    service = FinancialService(session)
    return await service.balance_sheet(
        company_id, as_of=await _parse_date(as_of)
    )


# ------------------------------------------------------------------ #
# Grand livre d'un compte
# ------------------------------------------------------------------ #
@router.get("/financial/ledger/{account_code}")
async def account_ledger(
    account_code: str,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    date_from: str | None = Query(default=None, description="Début (YYYY-MM-DD)"),
    date_to: str | None = Query(default=None, description="Fin (YYYY-MM-DD)"),
    _: User = Depends(require_permission("account", "view")),
):
    """Grand livre d'un compte : mouvements chronologiques + cumul."""
    service = FinancialService(session)
    return await service.general_ledger(
        company_id,
        account_code,
        date_from=await _parse_date(date_from),
        date_to=await _parse_date(date_to),
    )


# ------------------------------------------------------------------ #
# Journal général
# ------------------------------------------------------------------ #
@router.get("/financial/journal")
async def journal_report(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    journal_code: str | None = Query(default=None, description="Code journal (VTE, ACH…)"),
    date_from: str | None = Query(default=None, description="Début (YYYY-MM-DD)"),
    date_to: str | None = Query(default=None, description="Fin (YYYY-MM-DD)"),
    _: User = Depends(require_permission("account", "view")),
):
    """Journal général : écritures publiées d'une période (ou par journal)."""
    service = FinancialService(session)
    return await service.journal_report(
        company_id,
        journal_code=journal_code,
        date_from=await _parse_date(date_from),
        date_to=await _parse_date(date_to),
    )

    return await service.trial_balance(company_id)