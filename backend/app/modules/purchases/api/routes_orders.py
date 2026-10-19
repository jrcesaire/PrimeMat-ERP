"""
API Routes Bon de Commande (BC) — achats.

    GET    /purchases/orders
    POST   /purchases/orders
    GET    /purchases/orders/{order_id}
    PUT    /purchases/orders/{order_id}
    GET    /purchases/orders/{order_id}/lines
    POST   /purchases/orders/{order_id}/submit
    POST   /purchases/orders/{order_id}/confirm
    POST   /purchases/orders/{order_id}/cancel
    POST   /purchases/orders/{request_id}/convert-from-request
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.models.user import User
from app.core.dependencies.permissions import require_permission
from app.modules.purchases.schemas import (
    PurchaseOrderCreate,
    PurchaseOrderLineRead,
    PurchaseOrderRead,
    PurchaseOrderUpdate,
)
from app.modules.purchases.services.order_service import OrderService

router = APIRouter()

require_view = require_permission("purchase_order", "view")
require_edit = require_permission("purchase_order", "edit")
require_confirm = require_permission("purchase_order", "confirm")
require_cancel = require_permission("purchase_order", "cancel")


# ------------------------------------------------------------------ #
# Liste / consultation
# ------------------------------------------------------------------ #
@router.get("/orders", response_model=list[PurchaseOrderRead])
async def list_orders(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    status: str | None = None,
    supplier_id: int | None = None,
    _: None = Depends(require_view),
):
    service = OrderService(session)
    return await service.list_orders(
        skip=skip, limit=limit, status=status, supplier_id=supplier_id
    )


@router.get("/orders/{order_id}", response_model=PurchaseOrderRead)
async def get_order(
    order_id: int,
    session: SessionDep,
    _: None = Depends(require_view),
):
    service = OrderService(session)
    order = await service.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Bon de commande introuvable.")
    return order


@router.get("/orders/{order_id}/lines", response_model=list[PurchaseOrderLineRead])
async def list_order_lines(
    order_id: int,
    session: SessionDep,
    _: None = Depends(require_view),
):
    service = OrderService(session)
    order = await service.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Bon de commande introuvable.")
    return order.lines


# ------------------------------------------------------------------ #
# Écriture
# ------------------------------------------------------------------ #
@router.post(
    "/orders", response_model=PurchaseOrderRead, status_code=status.HTTP_201_CREATED
)
async def create_order(
    body: PurchaseOrderCreate,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
    _: None = Depends(require_edit),
):
    service = OrderService(session)
    return await service.create_order(body, current_user.company_id)


@router.put("/orders/{order_id}", response_model=PurchaseOrderRead)
async def update_order(
    order_id: int,
    body: PurchaseOrderUpdate,
    session: SessionDep,
    _: None = Depends(require_edit),
):
    service = OrderService(session)
    try:
        order = await service.update_order(order_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if order is None:
        raise HTTPException(status_code=404, detail="Bon de commande introuvable.")
    return order


# ------------------------------------------------------------------ #
# Workflow
# ------------------------------------------------------------------ #
@router.post("/orders/{order_id}/submit", response_model=PurchaseOrderRead)
async def submit_order(
    order_id: int,
    session: SessionDep,
    _: None = Depends(require_edit),
):
    service = OrderService(session)
    try:
        order = await service.submit(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if order is None:
        raise HTTPException(status_code=404, detail="Bon de commande introuvable.")
    return order


@router.post("/orders/{order_id}/confirm", response_model=PurchaseOrderRead)
async def confirm_order(
    order_id: int,
    session: SessionDep,
    _: None = Depends(require_confirm),
):
    service = OrderService(session)
    try:
        order = await service.confirm(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if order is None:
        raise HTTPException(status_code=404, detail="Bon de commande introuvable.")
    return order


@router.post("/orders/{order_id}/cancel", response_model=PurchaseOrderRead)
async def cancel_order(
    order_id: int,
    session: SessionDep,
    _: None = Depends(require_cancel),
):
    service = OrderService(session)
    try:
        order = await service.cancel(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if order is None:
        raise HTTPException(status_code=404, detail="Bon de commande introuvable.")
    return order


@router.get(
    "/orders/{order_id}/pdf",
    response_class=StreamingResponse,
)
async def download_order_pdf(
    order_id: int,
    session: SessionDep,
    _: None = Depends(require_view),
):
    """PDF du bon de commande fournisseur — téléchargement direct (WeasyPrint)."""
    import io

    from fastapi.responses import StreamingResponse

    from app.core.documents.context import ContextBuilder
    from app.core.documents.engine import DocumentEngine
    from app.core.documents.naming import content_disposition

    try:
        context = await ContextBuilder().build_purchase_order_context(order_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Bon de commande introuvable."
        )
    engine = DocumentEngine()
    path = await engine.arender_purchase_order(order_id)
    with open(path, "rb") as f:
        data = f.read()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={
            "Content-Disposition": content_disposition(
                context.get("doc_filename") or "document.pdf"
            )
        },
    )


@router.post(
    "/orders/{request_id}/convert-from-request",
    response_model=PurchaseOrderRead,
    status_code=status.HTTP_201_CREATED,
)
async def convert_from_request(
    request_id: int,
    session: SessionDep,
    current_user: User = Depends(get_current_active_user),
):
    service = OrderService(session)
    try:
        return await service.convert_from_request(request_id, current_user.company_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

