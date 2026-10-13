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
from app.modules.delivery.services.export_service import DeliveryExportService
from app.shared.file_export import export_response

router = APIRouter()


@router.get("/notes", response_model=list[DeliveryRead])
async def list_deliveries(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    order_id: int | None = None,
    _: User = Depends(require_permission("delivery", "view")),
):
    """Bons de livraison ; ``order_id`` filtre sur une vente."""
    service = DeliveryService(session)
    return await service.list_deliveries(skip=skip, limit=limit, order_id=order_id)


# Déclaré AVANT /notes/{delivery_id} : sinon « export » serait capturé
# comme identifiant et renverrait 422.
@router.get("/notes/export")
async def export_deliveries(
    session: SessionDep,
    format: str = "xlsx",
    template: bool = False,
    _: User = Depends(require_permission("delivery", "view")),
):
    """Export Excel / CSV des bons de livraison — une ligne par article.

    ``format`` : ``xlsx`` (défaut) ou ``csv`` ; ``template=1`` : en‑têtes seuls.
    """
    headers, rows = await DeliveryExportService(session).deliveries(
        include_rows=not template
    )
    return export_response(format, "Livraisons", headers, rows)


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
    try:
        delivery = await service.update_status(
            delivery_id, status_update.get("status", "")
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if delivery is None:
        raise HTTPException(status_code=404, detail="Bon de livraison introuvable")
    return delivery


@router.post("/notes/{delivery_id}/back-to-draft", response_model=DeliveryRead)
async def back_to_draft_delivery(
    delivery_id: int,
    session: SessionDep,
    user: User = Depends(require_permission("delivery", "edit")),
):
    """Remet un bon de livraison au brouillon (préalable à la suppression)."""
    service = DeliveryService(session)
    if await service.get_delivery(delivery_id) is None:
        raise HTTPException(status_code=404, detail="Bon de livraison introuvable")
    try:
        return await service.back_to_draft(delivery_id, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/notes/{delivery_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_delivery(
    delivery_id: int,
    session: SessionDep,
    user: User = Depends(require_permission("delivery", "delete")),
):
    """Supprime un BL — brouillon uniquement, paiements déjà supprimés."""
    service = DeliveryService(session)
    if await service.get_delivery(delivery_id) is None:
        raise HTTPException(status_code=404, detail="Bon de livraison introuvable")
    try:
        await service.delete_delivery(delivery_id, user_id=user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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
    from app.core.documents.naming import content_disposition

    try:
        context = await ContextBuilder().load_delivery(delivery_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Bon de livraison introuvable")
    engine = DocumentEngine()
    path = await engine.arender_delivery(delivery_id)
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