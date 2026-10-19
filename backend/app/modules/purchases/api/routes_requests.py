"""
API Routes Demandes d'Achat (DA).

   GET    /purchases/requests
   GET    /purchases/requests/{request_id}
   PUT    /purchases/requests/{request_id}
   DELETE /purchases/requests/{request_id}
   POST   /purchases/requests/{request_id}/submit
   POST   /purchases/requests/{request_id}/approve
   POST   /purchases/requests/{request_id}/reject
   POST   /purchases/requests/{request_id}/delete
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.models.user import User
from app.core.dependencies.permissions import require_permission
from app.modules.purchases.models import PurchaseRequest
from app.modules.purchases.schemas import (
    PurchaseRequestCreate,
    PurchaseRequestRead,
    PurchaseRequestUpdate,
)
from app.modules.purchases.services.request_service import RequestService

router = APIRouter()
require_view = require_permission("purchase_request", "view")
require_edit = require_permission("purchase_request", "edit")
require_approve = require_permission("purchase_request", "approve")
require_delete = require_permission("purchase_request", "delete")


# ------------------------------------------------------------------ #
# Liste / consultation
# ------------------------------------------------------------------ #
@router.get("/requests", response_model=list[PurchaseRequestRead])
async def list_requests(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    requester_id: int | None = None,
    _: None = Depends(require_view),
):
    service = RequestService(session)
    return await service.list_requests(
        skip=skip, limit=limit, status=status, requester_id=requester_id
    )


@router.get("/requests/{request_id}", response_model=PurchaseRequestRead)
async def get_request(
    request_id: int,
    session: SessionDep,
    _: None = Depends(require_view),
):
    service = RequestService(session)
    request = await service.get_request(request_id)
    if request is None:
        raise HTTPException(status_code=404, detail="Demande d'achat introuvable.")
    return request


# ------------------------------------------------------------------ #
# Écriture
# ------------------------------------------------------------------ #
@router.post(
    "/requests",
    response_model=PurchaseRequestRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_request(
    body: PurchaseRequestCreate,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_edit),
):
    service = RequestService(session)
    return await service.create_request(body, current_user.company_id, current_user.id)


@router.put("/requests/{request_id}", response_model=PurchaseRequestRead)
async def update_request(
    request_id: int,
    body: PurchaseRequestUpdate,
    session: SessionDep,
    _: None = Depends(require_edit),
):
    service = RequestService(session)
    try:
        request = await service.update_request(request_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if request is None:
        raise HTTPException(status_code=404, detail="Demande d'achat introuvable.")
    return request


# ------------------------------------------------------------------ #
# Workflow (validation hiérarchique)
# ------------------------------------------------------------------ #
@router.post("/requests/{request_id}/submit", response_model=PurchaseRequestRead)
async def submit_request(
    request_id: int,
    session: SessionDep,
    _: None = Depends(require_edit),
):
    service = RequestService(session)
    try:
        request = await service.submit(request_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if request is None:
        raise HTTPException(status_code=404, detail="Demande d'achat introuvable.")
    return request


@router.post("/requests/{request_id}/approve", response_model=PurchaseRequestRead)
async def approve_request(
    request_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_approve),
):
    """Validation hiérarchique (court-circuit si le montant est en dessous du seuil)."""
    service = RequestService(session)
    try:
        request = await service.approve(request_id, current_user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if request is None:
        raise HTTPException(status_code=404, detail="Demande d'achat introuvable.")
    return request


@router.post("/requests/{request_id}/reject", response_model=PurchaseRequestRead)
async def reject_request(
    request_id: int,
    session: SessionDep,
    body: dict[str, str] | None = None,
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_approve),
):
    reason = (body or {}).get("reason") if body else None
    service = RequestService(session)
    try:
        request = await service.reject(request_id, current_user.id, reason)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if request is None:
        raise HTTPException(status_code=404, detail="Demande d'achat introuvable.")
    return request


@router.post("/requests/{request_id}/delete", status_code=status.HTTP_204_NO_CONTENT)
async def delete_request(
    request_id: int,
    session: SessionDep,
    _: None = Depends(require_delete),
):
    service = RequestService(session)
    if not await service.delete_request(request_id):
        raise HTTPException(status_code=400, detail="Impossible de supprimer cette demande.")
