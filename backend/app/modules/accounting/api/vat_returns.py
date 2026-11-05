"""
API Comptabilité — TVA déclarative (Phase 2 PRD).

Calcul de la TVA collectée / déductible d'une période, cycle de vie de la
déclaration (``draft`` → ``submitted`` → ``paid``), écriture de liquidation
et règlement de la TVA due.

Routes préfixées par ``/api/v1/accounting``, isolées par tenant.
"""
from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi import status as http_status

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_company_id
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.accounting.schemas.vat import (
    VATPayRequest,
    VATPreview,
    VATReturnCreate,
    VATReturnRead,
)
from app.modules.accounting.services.vat_service import VATService

router = APIRouter()


def _http_error(exc: ValueError) -> HTTPException:
    """Mappe une erreur métier vers HTTP (404 si introuvable, 400 sinon)."""
    code = (
        http_status.HTTP_404_NOT_FOUND
        if "introuvable" in str(exc)
        else http_status.HTTP_400_BAD_REQUEST
    )
    return HTTPException(status_code=code, detail=str(exc))


# ------------------------------------------------------------------ #
# Calcul
# ------------------------------------------------------------------ #
# NOTE : cette route est déclarée AVANT ``/vat-returns/{return_id}`` pour que
# « preview » ne soit pas interprété comme un identifiant.
@router.get("/vat-returns/preview", response_model=VATPreview)
async def preview_vat_return(
    period_start: date,
    period_end: date,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "view")),
):
    """Aperçu non enregistré : TVA collectée / déductible de la période.

    Les comptes de TVA sont identifiés par leur nom technique du plan OHADA
    (``tax_collected``, ``tax_deductible``). Les écritures générées par les
    déclarations elles-mêmes sont exclues du calcul.
    """
    try:
        return await VATService(session).preview(
            company_id, period_start, period_end
        )
    except ValueError as exc:
        raise _http_error(exc)


# ------------------------------------------------------------------ #
# Déclarations
# ------------------------------------------------------------------ #
@router.get("/vat-returns", response_model=list[VATReturnRead])
async def list_vat_returns(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    status: str | None = None,
    _: User = Depends(require_permission("account", "view")),
):
    """Historique des déclarations (filtre optionnel par statut)."""
    return await VATService(session).list_returns(company_id, status=status)


@router.post(
    "/vat-returns",
    response_model=VATReturnRead,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_vat_return(
    body: VATReturnCreate,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("journal_entry", "create")),
):
    """Crée une déclaration en brouillon, montants calculés sur la période."""
    try:
        return await VATService(session).create_return(company_id, body)
    except ValueError as exc:
        raise _http_error(exc)


@router.get("/vat-returns/{return_id}", response_model=VATReturnRead)
async def get_vat_return(
    return_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "view")),
):
    """Détail d'une déclaration, avec son détail par compte."""
    try:
        return await VATService(session).get_return(company_id, return_id)
    except ValueError as exc:
        raise _http_error(exc)


@router.post("/vat-returns/{return_id}/recompute", response_model=VATReturnRead)
async def recompute_vat_return(
    return_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("journal_entry", "create")),
):
    """Recalcule une déclaration en brouillon."""
    try:
        return await VATService(session).recompute(company_id, return_id)
    except ValueError as exc:
        raise _http_error(exc)


@router.post("/vat-returns/{return_id}/submit", response_model=VATReturnRead)
async def submit_vat_return(
    return_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("journal_entry", "create")),
):
    """Soumet la déclaration : génère l'écriture de liquidation de la TVA.

    Solde les comptes de TVA de la période et constate la position nette sur
    le compte de l'État (crédit si TVA à payer, débit si crédit reportable).
    """
    try:
        return await VATService(session).submit(company_id, return_id)
    except ValueError as exc:
        raise _http_error(exc)


@router.post("/vat-returns/{return_id}/pay", response_model=VATReturnRead)
async def pay_vat_return(
    return_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    body: VATPayRequest | None = None,
    _: User = Depends(require_permission("journal_entry", "create")),
):
    """Règle la TVA due (``D 441 / C 521``)."""
    try:
        return await VATService(session).pay(
            company_id, return_id, body or VATPayRequest()
        )
    except ValueError as exc:
        raise _http_error(exc)


@router.delete(
    "/vat-returns/{return_id}", status_code=http_status.HTTP_204_NO_CONTENT
)
async def delete_vat_return(
    return_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("journal_entry", "create")),
):
    """Supprime une déclaration en brouillon."""
    try:
        await VATService(session).delete_return(company_id, return_id)
    except ValueError as exc:
        raise _http_error(exc)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


__all__ = ["router"]
