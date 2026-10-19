"""
API Finance — tresorerie et rapprochement bancaire (Phase 2 PRD).

Comptes de tresorerie (banque / caisse / mobile money), releves bancaires,
lignes a rapprocher et rapport de rapprochement.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_company_id
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.finance.schemas.treasury import (
    BankStatementCreate,
    BankStatementLineCreate,
    BankStatementLineRead,
    BankStatementRead,
    ReconciliationReport,
    ReconcilePayload,
    ReconcileResult,
    TreasuryAccountCreate,
    TreasuryAccountRead,
    TreasuryAccountUpdate,
)
from app.modules.finance.services.treasury_service import TreasuryService

router = APIRouter()


def _http_error(exc: ValueError) -> HTTPException:
    """Mappe les erreurs metier vers HTTP (404 si introuvable, 400 sinon)."""
    code = (
        status.HTTP_404_NOT_FOUND
        if "introuvable" in str(exc)
        else status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=code, detail=str(exc))


# ------------------------------------------------------------------ #
# Comptes de tresorerie
# ------------------------------------------------------------------ #
@router.get("/treasury/accounts", response_model=list[TreasuryAccountRead])
async def list_treasury_accounts(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    active_only: bool = True,
    _: User = Depends(require_permission("treasury", "view")),
):
    """Comptes de tresorerie de l'entreprise."""
    service = TreasuryService(session)
    return await service.list_accounts(company_id, active_only=active_only)


@router.post(
    "/treasury/accounts",
    response_model=TreasuryAccountRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_treasury_account(
    body: TreasuryAccountCreate,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("treasury", "create")),
):
    """Cree un compte de tresorerie (code unique par entreprise)."""
    try:
        return await TreasuryService(session).create_account(company_id, body)
    except ValueError as exc:
        raise _http_error(exc)


@router.put("/treasury/accounts/{account_id}", response_model=TreasuryAccountRead)
async def update_treasury_account(
    account_id: int,
    body: TreasuryAccountUpdate,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("treasury", "edit")),
):
    """Met a jour un compte de tresorerie."""
    try:
        return await TreasuryService(session).update_account(company_id, account_id, body)
    except ValueError as exc:
        raise _http_error(exc)


@router.delete("/treasury/accounts/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_treasury_account(
    account_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("treasury", "delete")),
):
    """Supprime un compte de tresorerie (et ses releves, cascade)."""
    try:
        await TreasuryService(session).delete_account(company_id, account_id)
    except ValueError as exc:
        raise _http_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ #
# Releves bancaires
# ------------------------------------------------------------------ #
@router.get(
    "/treasury/accounts/{account_id}/statements",
    response_model=list[BankStatementRead],
)
async def list_statements(
    account_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("treasury", "view")),
):
    """Releves d'un compte de tresorerie."""
    try:
        return await TreasuryService(session).list_statements(company_id, account_id)
    except ValueError as exc:
        raise _http_error(exc)


@router.post(
    "/treasury/accounts/{account_id}/statements",
    response_model=BankStatementRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_statement(
    account_id: int,
    body: BankStatementCreate,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("treasury", "create")),
):
    """Cree un releve bancaire (soldes d'ouverture / cloture)."""
    try:
        return await TreasuryService(session).create_statement(company_id, account_id, body)
    except ValueError as exc:
        raise _http_error(exc)


@router.get("/treasury/statements/{statement_id}", response_model=BankStatementRead)
async def get_statement(
    statement_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("treasury", "view")),
):
    """Detail d'un releve avec ses lignes."""
    try:
        return await TreasuryService(session).get_statement(company_id, statement_id)
    except ValueError as exc:
        raise _http_error(exc)


@router.post(
    "/treasury/statements/{statement_id}/lines",
    response_model=BankStatementLineRead,
    status_code=status.HTTP_201_CREATED,
)
async def add_statement_line(
    statement_id: int,
    body: BankStatementLineCreate,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("treasury", "create")),
):
    """Ajoute une ligne au releve (montant signe : + encaissement)."""
    try:
        return await TreasuryService(session).add_line(company_id, statement_id, body)
    except ValueError as exc:
        raise _http_error(exc)


@router.delete("/treasury/lines/{line_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_statement_line(
    line_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("treasury", "delete")),
):
    """Supprime une ligne non rapprochee d'un releve ouvert."""
    try:
        await TreasuryService(session).delete_line(company_id, line_id)
    except ValueError as exc:
        raise _http_error(exc)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/treasury/statements/{statement_id}/close", response_model=BankStatementRead
)
async def close_statement(
    statement_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("treasury", "edit")),
):
    """Cloture un releve (verrouille ses lignes)."""
    try:
        return await TreasuryService(session).close_statement(company_id, statement_id)
    except ValueError as exc:
        raise _http_error(exc)


# ------------------------------------------------------------------ #
# Rapprochement
# ------------------------------------------------------------------ #
@router.post(
    "/treasury/statements/{statement_id}/auto-reconcile",
    response_model=ReconcileResult,
)
async def auto_reconcile(
    statement_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("treasury", "edit")),
):
    """Rapprochement automatique : montant identique + date +|- 5 jours."""
    try:
        return await TreasuryService(session).auto_reconcile(company_id, statement_id)
    except ValueError as exc:
        raise _http_error(exc)


@router.post(
    "/treasury/lines/{line_id}/reconcile", response_model=BankStatementLineRead
)
async def reconcile_line(
    line_id: int,
    body: ReconcilePayload,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    user: User = Depends(require_permission("treasury", "edit")),
):
    """Rapproche manuellement une ligne de releve et une ecriture."""
    try:
        return await TreasuryService(session).reconcile(
            company_id, line_id, body.entry_line_id, user_id=user.id
        )
    except ValueError as exc:
        raise _http_error(exc)


@router.post(
    "/treasury/lines/{line_id}/unreconcile", response_model=BankStatementLineRead
)
async def unreconcile_line(
    line_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("treasury", "edit")),
):
    """Retire le rapprochement d'une ligne (releve ouvert uniquement)."""
    try:
        return await TreasuryService(session).unreconcile(company_id, line_id)
    except ValueError as exc:
        raise _http_error(exc)


@router.get(
    "/treasury/accounts/{account_id}/reconciliation",
    response_model=ReconciliationReport,
)
async def reconciliation_report(
    account_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("treasury", "view")),
):
    """Rapport : solde comptable, solde releve, montant rapproche, lignes en attente."""
    try:
        return await TreasuryService(session).reconciliation_report(company_id, account_id)
    except ValueError as exc:
        raise _http_error(exc)


__all__ = ["router"]
