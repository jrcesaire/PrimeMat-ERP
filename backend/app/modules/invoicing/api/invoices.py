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
from app.modules.invoicing.services.export_service import InvoiceExportService
from app.modules.invoicing.services.invoice_service import InvoiceService
from app.shared.file_export import export_response

router = APIRouter()


@router.get("/invoices", response_model=list[InvoiceRead])
async def list_invoices(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    order_id: int | None = None,
    include_pos: bool = False,
    _: User = Depends(require_permission("invoice", "view")),
):
    """Factures (ventes comptoir exclues par défaut)."""
    service = InvoiceService(session)
    if order_id is not None:
        invoices = await service.list_invoices(skip=skip, limit=limit, include_pos=include_pos)
        return [i for i in invoices if i.order_id == order_id]
    return await service.list_invoices(skip=skip, limit=limit, include_pos=include_pos)


# Déclaré AVANT /invoices/{invoice_id} : sinon « export » serait capturé
# comme identifiant et renverrait 422.
@router.get("/invoices/export")
async def export_invoices(
    session: SessionDep,
    format: str = "xlsx",
    template: bool = False,
    include_pos: bool = False,
    _: User = Depends(require_permission("invoice", "view")),
):
    """Export Excel / CSV des factures — une ligne par article.

    ``format`` : ``xlsx`` (défaut) ou ``csv`` ; ``template=1`` : en‑têtes seuls.
    """
    headers, rows = await InvoiceExportService(session).invoices(
        include_rows=not template, include_pos=include_pos
    )
    return export_response(format, "Factures", headers, rows)


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
    """Crée une facture depuis une commande (totale, solde ou acompte)."""
    service = InvoiceService(session)
    try:
        return await service.create_from_order(
            body.order_id,
            due_days=body.due_days,
            mode=body.mode,
            value=body.value,
            post=body.post,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/invoices/{invoice_id}/post", response_model=InvoiceRead)
async def post_invoice(
    invoice_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("invoice", "edit")),
):
    """Confirme une facture brouillon (→ comptabilisée)."""
    service = InvoiceService(session)
    try:
        return await service.post_invoice(invoice_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/invoices/{invoice_id}/reset-to-draft", response_model=InvoiceRead)
async def reset_invoice_to_draft(
    invoice_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("invoice", "edit")),
):
    """Remet une facture confirmée en brouillon (refusé si un paiement existe)."""
    service = InvoiceService(session)
    try:
        return await service.reset_to_draft(invoice_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/invoices/{invoice_id}/cancel", response_model=InvoiceRead)
async def cancel_invoice(
    invoice_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("invoice", "cancel")),
):
    """Annule une facture non payée et libère la commande pour re-facturation."""
    service = InvoiceService(session)
    try:
        return await service.cancel(invoice_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/invoices/{invoice_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_invoice(
    invoice_id: int,
    session: SessionDep,
    user: User = Depends(require_permission("invoice", "delete")),
):
    """Supprime une facture — brouillon uniquement, aucun paiement rattaché."""
    service = InvoiceService(session)
    if await service.get_invoice(invoice_id) is None:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    try:
        await service.delete_invoice(invoice_id, user_id=user.id)
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
    from app.core.documents.naming import content_disposition

    try:
        context = await ContextBuilder().load_invoice(invoice_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Facture introuvable")
    engine = DocumentEngine()
    path = await engine.arender_invoice(invoice_id)
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