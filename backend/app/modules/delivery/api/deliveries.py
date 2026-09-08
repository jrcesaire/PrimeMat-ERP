"""API Livraison + bon de livraison imprimable."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.delivery.schemas import DeliveryFromOrder, DeliveryRead
from app.modules.delivery.services.delivery_service import DeliveryService

router = APIRouter()


@router.get("/notes", response_model=list[DeliveryRead])
async def list_deliveries(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    _: User = Depends(require_permission("delivery", "view")),
):
    service = DeliveryService(session)
    return await service.list_deliveries(skip=skip, limit=limit)


@router.get("/notes/{delivery_id}", response_model=DeliveryRead)
async def get_delivery(
    delivery_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("delivery", "view")),
):
    service = DeliveryService(session)
    delivery = await service.get_delivery(delivery_id)
    if delivery is None:
        raise HTTPException(status_code=404, detail="Bon de livraison introuvable")
    return delivery


@router.post(
    "/notes/from-order",
    response_model=DeliveryRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_delivery_from_order(
    body: DeliveryFromOrder,
    session: SessionDep,
    _: User = Depends(require_permission("delivery", "create")),
):
    service = DeliveryService(session)
    try:
        return await service.create_from_order(
            body.order_id, expected_date=body.expected_date, notes=body.notes
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/notes/{delivery_id}/status", response_model=DeliveryRead)
async def update_delivery_status(
    delivery_id: int,
    session: SessionDep,
    status_update: dict,
    _: User = Depends(require_permission("delivery", "edit")),
):
    service = DeliveryService(session)
    delivery = await service.update_status(delivery_id, status_update.get("status", ""))
    if delivery is None:
        raise HTTPException(status_code=404, detail="Bon de livraison introuvable")
    return delivery


@router.get("/notes/{delivery_id}/print")
async def print_delivery(
    delivery_id: int,
    _: User = Depends(require_permission("delivery", "view")),
):
    """Bon de livraison — format A4 (compatible matricielle)."""
    import io

    from fastapi.responses import StreamingResponse

    from app.core.documents.context import ContextBuilder
    from app.core.documents.engine import DocumentEngine

    try:
        context = await ContextBuilder().load_delivery(delivery_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Bon de livraison introuvable")
    engine = DocumentEngine()
    path = engine.render_to_pdf("delivery.html", context)
    with open(path, "rb") as f:
        data = f.read()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=delivery.pdf"},
    )