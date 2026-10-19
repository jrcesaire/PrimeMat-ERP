"""
API Routes Bons de Réception (BR) — achats.

    GET    /purchases/receptions
    POST   /purchases/receptions
    GET    /purchases/receptions/{reception_id}
    POST   /purchases/receptions/{reception_id}/validate
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.models.user import User
from app.core.dependencies.permissions import require_permission
from app.modules.purchases.schemas import (
    PurchaseReceptionCreate,
    PurchaseReceptionRead,
)
from app.modules.purchases.services.reception_service import ReceptionService

router = APIRouter()

require_view = require_permission("purchase_reception", "view")
require_create = require_permission("purchase_reception", "create")
require_validate = require_permission("purchase_reception", "validate")


# ------------------------------------------------------------------ #
# Liste / consultation
# ------------------------------------------------------------------ #
@router.get("/receptions", response_model=list[PurchaseReceptionRead])
async def list_receptions(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    order_id: int | None = None,
    status: str | None = None,
    _: None = Depends(require_view),
):
    service = ReceptionService(session)
    return await service.list_receptions(
        skip=skip, limit=limit, order_id=order_id, status=status
    )


@router.get("/receptions/{reception_id}", response_model=PurchaseReceptionRead)
async def get_reception(
    reception_id: int,
    session: SessionDep,
    _: None = Depends(require_view),
):
    service = ReceptionService(session)
    reception = await service.get_reception(reception_id)
    if reception is None:
        raise HTTPException(status_code=404, detail="Bon de réception introuvable.")
    return reception


# ------------------------------------------------------------------ #
# Écriture
# ------------------------------------------------------------------ #
@router.post(
    "/receptions",
    response_model=PurchaseReceptionRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_reception(
    body: PurchaseReceptionCreate,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_create),
):
    service = ReceptionService(session)
    return await service.create_reception(body, current_user.company_id, current_user.id)


# ------------------------------------------------------------------ #
# Workflow
# ------------------------------------------------------------------ #
@router.post(
    "/receptions/{reception_id}/validate",
    response_model=PurchaseReceptionRead,
)
async def validate_reception(
    reception_id: int,
    session: SessionDep,
    _: None = Depends(require_validate),
):
    service = ReceptionService(session)
    try:
        reception = await service.validate(reception_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if reception is None:
        raise HTTPException(status_code=404, detail="Bon de réception introuvable.")
    return reception

