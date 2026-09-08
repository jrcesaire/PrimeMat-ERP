"""API Facturation — invoices + impression PDF."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.invoicing.schemas import InvoiceFromOrder, InvoiceRead
# noqa: F401  (import enregistre les modèles)
from app.modules.invoicing.services.invoice_service import InvoiceService

router = APIRouter()


@router.get("/invoices", response_model=list[InvoiceRead])
async def list_invoices(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    _: User = Depends(require_permission("invoice", "view")),
):
    service = InvoiceService(session)
    return await service.list_invoices(skip=skip, limit=limit)


@router.get("/invoices/{invoice_id}", response_model=InvoiceRead)
async def get_invoice(
    invoice_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("invoice", "view")),
):
    service = InvoiceService(session)
    invoice = await service.get_invoice(invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    return invoice


@router.post(
    "/invoices/from-order",
    response_model=InvoiceRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_invoice_from_order(
    body: InvoiceFromOrder,
    session: SessionDep,
    _: User = Depends(require_permission("invoice", "create")),
):
    service = InvoiceService(session)
    try:
        return await service.create_from_order(body.order_id, due_days=body.due_days)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/invoices/{invoice_id}/print")
async def print_invoice(
    invoice_id: int,
    _: User = Depends(require_permission("invoice", "view")),
):
    """Génère le PDF de la facture (format A4)."""
    import io

    from fastapi.responses import StreamingResponse

    from app.core.documents.context import ContextBuilder
    from app.core.documents.engine import DocumentEngine

    try:
        context = await ContextBuilder().load_invoice(invoice_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    engine = DocumentEngine()
    path = engine.render_to_pdf("invoice.html", context)
    with open(path, "rb") as f:
        data = f.read()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=invoice.pdf"},
    )