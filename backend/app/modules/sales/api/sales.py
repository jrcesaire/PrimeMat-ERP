"""
Endpoints API du module Ventes — devis et commandes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.sales.schemas import (
    PosSaleCreate,
    QuoteCreate,
    QuoteRead,
    QuoteUpdate,
    SalesOrderCreate,
    SalesOrderRead,
    SalesOrderUpdate,
)
from app.modules.sales.services.order_service import OrderService
from app.modules.sales.services.pos_service import PosService
from app.modules.sales.services.quote_service import QuoteService

router = APIRouter()


# ------------------------------------------------------------------ #
# Devis
# ------------------------------------------------------------------ #
@router.get("/quotes", response_model=list[QuoteRead])
async def list_quotes(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    partner_id: int | None = None,
    _: User = Depends(require_permission("quote", "view")),
):
    service = QuoteService(session)
    return await service.list_quotes(skip=skip, limit=limit, partner_id=partner_id)


@router.post("/quotes", response_model=QuoteRead, status_code=status.HTTP_201_CREATED)
async def create_quote(
    body: QuoteCreate,
    session: SessionDep,
    _: User = Depends(require_permission("quote", "create")),
):
    service = QuoteService(session)
    try:
        return await service.create_quote(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/quotes/{quote_id}", response_model=QuoteRead)
async def get_quote(
    quote_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("quote", "view")),
):
    service = QuoteService(session)
    quote = await service.get_quote(quote_id)
    if quote is None:
        raise HTTPException(status_code=404, detail="Devis introuvable")
    return quote


@router.put("/quotes/{quote_id}", response_model=QuoteRead)
async def update_quote(
    quote_id: int,
    body: QuoteUpdate,
    session: SessionDep,
    _: User = Depends(require_permission("quote", "edit")),
):
    """Met à jour un devis brouillon (client, notes et lignes remplaçables)."""
    service = QuoteService(session)
    try:
        return await service.update_quote(quote_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/quotes/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quote(
    quote_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("quote", "delete")),
):
    """Supprime un devis brouillon (lignes et coupes incluses)."""
    service = QuoteService(session)
    try:
        await service.delete_quote(quote_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.post("/quotes/{quote_id}/confirm", response_model=SalesOrderRead)
async def confirm_quote(
    quote_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("quote", "confirm")),
):
    """Confirme un devis → génère la commande (coupes BAC préservées)."""
    service = QuoteService(session)
    try:
        return await service.confirm_quote(quote_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/quotes/{quote_id}/back-to-draft", response_model=QuoteRead)
async def quote_back_to_draft(
    quote_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("quote", "edit")),
):
    """Remet un devis confirmé au brouillon (annule la commande générée)."""
    service = QuoteService(session)
    try:
        return await service.back_to_draft(quote_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ------------------------------------------------------------------ #
# Commandes
# ------------------------------------------------------------------ #
@router.get("/orders", response_model=list[SalesOrderRead])
async def list_orders(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    partner_id: int | None = None,
    _: User = Depends(require_permission("order", "view")),
):
    service = OrderService(session)
    return await service.list_orders(skip=skip, limit=limit, partner_id=partner_id)


@router.post("/orders", response_model=SalesOrderRead, status_code=status.HTTP_201_CREATED)
async def create_order(
    body: SalesOrderCreate,
    session: SessionDep,
    _: User = Depends(require_permission("order", "create")),
):
    service = OrderService(session)
    return await service.create_order(body)


@router.get("/orders/{order_id}", response_model=SalesOrderRead)
async def get_order(
    order_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("order", "view")),
):
    service = OrderService(session)
    order = await service.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Commande introuvable")
    return order


@router.put("/orders/{order_id}", response_model=SalesOrderRead)
async def update_order(
    order_id: int,
    body: SalesOrderUpdate,
    session: SessionDep,
    _: User = Depends(require_permission("order", "edit")),
):
    """Met à jour une commande brouillon (client, notes et lignes remplaçables)."""
    service = OrderService(session)
    try:
        return await service.update_order(order_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/orders/{order_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_order(
    order_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("order", "delete")),
):
    """Supprime une commande brouillon (lignes et coupes incluses)."""
    service = OrderService(session)
    try:
        await service.delete_order(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/orders/{order_id}/print")
async def print_order(
    order_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("order", "view")),
):
    """PDF d'une commande.

    - vente comptoir (``pos``)  → ticket de caisse 80 mm
    - autre commande            → facture (auto-générée si absente)
    """
    import io

    from fastapi.responses import StreamingResponse
    from sqlalchemy import select as _select

    from app.core.documents.context import ContextBuilder
    from app.core.documents.engine import DocumentEngine
    from app.modules.invoicing.models.invoice import Invoice
    from app.modules.invoicing.services.invoice_service import InvoiceService
    from app.modules.sales.services.order_service import OrderService

    engine = DocumentEngine()
    builder = ContextBuilder()

    service = OrderService(session)
    order = await service.get_order(order_id)
    if order is None:
        raise HTTPException(status_code=404, detail="Commande introuvable")

    if order.fulfillment_mode == "pos":
        try:
            path = engine.render_to_pdf(
                "pos_ticket.html", await builder.load_pos(order_id)
            )
        except ValueError:
            raise HTTPException(status_code=404, detail="Vente introuvable")
        filename = "ticket.pdf"
    else:
        # Facture liée existante ? Sinon génération automatique.
        result = await session.execute(
            _select(Invoice).where(Invoice.order_id == order_id).limit(1)
        )
        invoice = result.scalar_one_or_none()
        if invoice is None:
            try:
                invoice = await InvoiceService(session).create_from_order(order_id)
            except ValueError as exc:
                raise HTTPException(status_code=400, detail=str(exc))
        path = engine.render_to_pdf("invoice.html", await builder.load_invoice(invoice.id))
        filename = "invoice.pdf"

    with open(path, "rb") as f:
        data = f.read()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename={filename}"},
    )


@router.post("/orders/{order_id}/confirm")
async def confirm_order(
    order_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("order", "confirm")),
):
    """Confirme une commande : réserve le stock et crée les besoins d'achat."""
    service = OrderService(session)
    try:
        return await service.confirm_order(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/orders/{order_id}/back-to-draft", response_model=SalesOrderRead)
async def order_back_to_draft(
    order_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("order", "edit")),
):
    """Remet une commande confirmée au brouillon (libère les réservations).

    Refusé si une facture ou un bon de livraison est déjà lié.
    """
    service = OrderService(session)
    try:
        return await service.back_to_draft(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
@router.get("/quotes/{quote_id}/print")
async def print_quote(
    quote_id: int,
    _: User = Depends(require_permission("quote", "view")),
):
    """PDF du devis — format A4, coupes BAC préservées."""
    import io

    from fastapi.responses import StreamingResponse

    from app.core.documents.context import ContextBuilder
    from app.core.documents.engine import DocumentEngine

    try:
        context = await ContextBuilder().load_quote(quote_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Devis introuvable")
    engine = DocumentEngine()
    path = engine.render_to_pdf("quote.html", context)
    with open(path, "rb") as f:
        data = f.read()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=quote.pdf"},
    )


@router.get("/quotes/{quote_id}/preview-html")
async def preview_quote_html(
    quote_id: int,
    _: User = Depends(require_permission("quote", "view")),
):
    """Aperçu HTML du devis (pour le rendu navigateur)."""
    from fastapi.responses import HTMLResponse

    from app.core.documents.context import ContextBuilder
    from app.core.documents.engine import DocumentEngine

    try:
        context = await ContextBuilder().load_quote(quote_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Devis introuvable")
    engine = DocumentEngine()
    return HTMLResponse(engine.render_to_html("quote.html", context))


# ------------------------------------------------------------------ #
# Point de vente (comptoir)
# ------------------------------------------------------------------ #
@router.post("/pos/sales")
async def create_pos_sale(
    body: PosSaleCreate,
    session: SessionDep,
    _: User = Depends(require_permission("order", "create")),
):
    """Vente comptoir simple → commande + stock + facture + paiement."""
    service = PosService(session)
    try:
        return await service.create_pos_sale(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/pos/sales/{order_id}/ticket")
async def print_pos_ticket(
    order_id: int,
    _: User = Depends(require_permission("order", "view")),
):
    """Ticket de caisse (80 mm) avec QR code en bas."""
    import io

    from fastapi.responses import StreamingResponse

    from app.core.documents.context import ContextBuilder
    from app.core.documents.engine import DocumentEngine

    try:
        context = await ContextBuilder().load_pos(order_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Vente introuvable")
    engine = DocumentEngine()
    path = engine.render_to_pdf("pos_ticket.html", context)
    with open(path, "rb") as f:
        data = f.read()
    return StreamingResponse(
        io.BytesIO(data),
        media_type="application/pdf",
        headers={"Content-Disposition": "inline; filename=ticket.pdf"},
    )