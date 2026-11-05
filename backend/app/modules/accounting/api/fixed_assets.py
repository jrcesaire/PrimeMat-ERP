"""
API Comptabilité — immobilisations et amortissements (Phase 2 PRD).

CRUD des immobilisations, plan d'amortissement (linéaire ou dégressif
SYSCOHADA) et comptabilisation des dotations ``D 681 / C 28x``.

Routes préfixées par ``/api/v1/accounting``, isolées par tenant.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response
from fastapi import status as http_status

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_company_id
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.accounting.schemas.fixed_asset import (
    DepreciationRunRequest,
    DepreciationRunResult,
    FixedAssetCreate,
    FixedAssetRead,
    FixedAssetSummary,
    FixedAssetUpdate,
)
from app.modules.accounting.services.depreciation_service import (
    DepreciationService,
)

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
# Immobilisations
# ------------------------------------------------------------------ #
@router.get("/fixed-assets", response_model=list[FixedAssetRead])
async def list_fixed_assets(
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    status: str | None = None,
    _: User = Depends(require_permission("account", "view")),
):
    """Immobilisations de l'entreprise (filtre optionnel par statut)."""
    return await DepreciationService(session).list_assets(company_id, status=status)


@router.post(
    "/fixed-assets",
    response_model=FixedAssetRead,
    status_code=http_status.HTTP_201_CREATED,
)
async def create_fixed_asset(
    body: FixedAssetCreate,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "create")),
):
    """Crée une immobilisation et son plan d'amortissement.

    Le compte d'amortissement cumulé est déduit du compte d'immobilisation
    (``245`` → ``284``) s'il n'est pas fourni.
    """
    try:
        return await DepreciationService(session).create_asset(company_id, body)
    except ValueError as exc:
        raise _http_error(exc)


@router.get("/fixed-assets/{asset_id}", response_model=FixedAssetRead)
async def get_fixed_asset(
    asset_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "view")),
):
    """Détail d'une immobilisation, avec son plan d'amortissement."""
    try:
        return await DepreciationService(session).get_asset(company_id, asset_id)
    except ValueError as exc:
        raise _http_error(exc)


@router.get("/fixed-assets/{asset_id}/summary", response_model=FixedAssetSummary)
async def get_fixed_asset_summary(
    asset_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "view")),
):
    """Synthèse comptable : cumul des dotations, VNC, reste à comptabiliser."""
    service = DepreciationService(session)
    try:
        asset = await service.get_asset(company_id, asset_id)
    except ValueError as exc:
        raise _http_error(exc)
    return await service.summary(asset)


@router.put("/fixed-assets/{asset_id}", response_model=FixedAssetRead)
async def update_fixed_asset(
    asset_id: int,
    body: FixedAssetUpdate,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "edit")),
):
    """Met à jour une immobilisation (plan recalculé si les paramètres changent)."""
    try:
        return await DepreciationService(session).update_asset(
            company_id, asset_id, body
        )
    except ValueError as exc:
        raise _http_error(exc)


@router.delete(
    "/fixed-assets/{asset_id}", status_code=http_status.HTTP_204_NO_CONTENT
)
async def delete_fixed_asset(
    asset_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    _: User = Depends(require_permission("account", "edit")),
):
    """Supprime une immobilisation (refus si des dotations sont comptabilisées)."""
    try:
        await DepreciationService(session).delete_asset(company_id, asset_id)
    except ValueError as exc:
        raise _http_error(exc)
    return Response(status_code=http_status.HTTP_204_NO_CONTENT)


# ------------------------------------------------------------------ #
# Comptabilisation des dotations
# ------------------------------------------------------------------ #
@router.post(
    "/fixed-assets/{asset_id}/generate-depreciation",
    response_model=DepreciationRunResult,
)
async def generate_depreciation(
    asset_id: int,
    session: SessionDep,
    company_id: int = Depends(get_current_company_id),
    body: DepreciationRunRequest | None = None,
    _: User = Depends(require_permission("journal_entry", "create")),
):
    """Comptabilise les dotations échues (``D 681 / C 28x``), idempotent.

    ``as_of`` limite la comptabilisation aux échéances arrivées à terme à
    cette date (par défaut : aujourd'hui). Les dotations tombant dans un
    exercice clôturé sont ignorées et signalées dans le message.
    """
    service = DepreciationService(session)
    try:
        asset = await service.get_asset(company_id, asset_id)
        result = await service.post_due(asset, as_of=body.as_of if body else None)
    except ValueError as exc:
        raise _http_error(exc)
    return result


__all__ = ["router"]