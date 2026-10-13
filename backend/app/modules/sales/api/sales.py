"""
Endpoints API du module Ventes — devis et commandes.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, UploadFile, status

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.sales.schemas import (
    PosSaleCreate,
    QuoteCreate,
    QuoteInvoiceCreate,
    QuoteInvoiceRead,
    QuoteRead,
    QuoteUpdate,
    SalesOrderCreate,
    SalesOrderRead,
    SalesOrderUpdate,
)
from app.modules.sales.services.export_service import SalesExportService
from app.modules.sales.services.import_service import SalesImportService
from app.modules.sales.services.order_service import OrderService
from app.modules.sales.services.pos_service import PosService
from app.modules.sales.services.quote_service import QuoteService
from app.shared.file_export import export_response
from app.shared.file_import import read_rows_from_bytes

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


# Déclaré AVANT /quotes/{quote_id} : sinon « export » serait capturé comme
# identifiant et renverrait 422.
@router.get("/quotes/export")
async def export_quotes(
    session: SessionDep,
    format: str = "xlsx",
    template: bool = False,
    _: User = Depends(require_permission("quote", "view")),
):
    """Export Excel / CSV des devis — une ligne par article.

    ``format`` : ``xlsx`` (défaut) ou ``csv`` ; ``template=1`` : en‑têtes seuls.
    """
    headers, rows = await SalesExportService(session).quotes(
        include_rows=not template
    )
    return export_response(format, "Devis", headers, rows)


@router.post("/quotes", response_model=QuoteRead, status_code=status.HTTP_201_CREATED)
async def create_quote(
    body: QuoteCreate,
    session: SessionDep,
    current_user: User = Depends(require_permission("quote", "create")),
):
    service = QuoteService(session)
    try:
        return await service.create_quote(body, current_user)
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
    current_user: User = Depends(require_permission("quote", "edit")),
):
    """Met à jour un devis brouillon (client, notes et lignes remplaçables)."""
    service = QuoteService(session)
    try:
        return await service.update_quote(quote_id, body, current_user)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.delete("/quotes/{quote_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_quote(
    quote_id: int,
    session: SessionDep,
    user: User = Depends(require_permission("quote", "delete")),
):
    """Supprime un devis brouillon (lignes et coupes incluses)."""
    service = QuoteService(session)
    try:
        await service.delete_quote(quote_id, user_id=user.id)
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


@router.post("/quotes/{quote_id}/invoice", response_model=QuoteInvoiceRead)
async def create_quote_invoice(
    quote_id: int,
    body: QuoteInvoiceCreate,
    session: SessionDep,
    _: User = Depends(require_permission("invoice", "create")),
):
    """Parcours de vente — « Créer facture » depuis un devis confirmé.

    Enchaîne les étapes sans changer de module :

    1. confirmation du devis si nécessaire (commande créée ou réutilisée) ;
    2. facturation de la commande liée (totale, acompte % ou acompte fixe).

    **Idempotent** : si la commande est déjà entièrement facturée, la facture
    existante est renvoyée avec ``created=False`` — le bouton « Créer facture »
    fait alors office de « Voir la facture ».
    """
    from sqlalchemy import select as _select

    from app.modules.invoicing.models.invoice import Invoice
    from app.modules.invoicing.services.invoice_service import InvoiceService

    quote_service = QuoteService(session)
    try:
        order = await quote_service.confirm_quote(quote_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))

    invoice_service = InvoiceService(session)
    created = True
    try:
        invoice = await invoice_service.create_from_order(
            order.id,
            due_days=body.due_days,
            mode=body.mode,
            value=body.value,
            post=body.post,
        )
    except ValueError as exc:
        # Commande déjà facturée : on renvoie la facture existante au lieu
        # d'échouer — le parcours reste ainsi re-jouable.
        if "entièrement facturée" not in str(exc):
            raise HTTPException(status_code=400, detail=str(exc))
        result = await session.execute(
            _select(Invoice)
            .where(Invoice.order_id == order.id)
            .order_by(Invoice.id.desc())
            .limit(1)
        )
        invoice = result.scalar_one_or_none()
        if invoice is None:
            raise HTTPException(status_code=400, detail=str(exc))
        created = False

    quote = await quote_service.get_quote(quote_id)
    return QuoteInvoiceRead(
        quote_id=quote_id,
        quote_reference=getattr(quote, "reference", "") or "",
        order_id=order.id,
        order_reference=order.reference,
        invoice_id=invoice.id,
        invoice_reference=invoice.reference,
        invoice_status=invoice.status,
        created=created,
    )


# ------------------------------------------------------------------ #
# Commandes
# ------------------------------------------------------------------ #
@router.get("/orders", response_model=list[SalesOrderRead])
async def list_orders(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    partner_id: int | None = None,
    include_pos: bool = False,
    _: User = Depends(require_permission("order", "view")),
):
    """Liste les commandes (ventes comptoir exclues par défaut)."""
    service = OrderService(session)
    return await service.list_orders(
        skip=skip, limit=limit, partner_id=partner_id, include_pos=include_pos
    )


# Déclaré AVANT /orders/{order_id} : sinon « export » serait capturé comme
# identifiant et renverrait 422.
@router.get("/orders/export")
async def export_orders(
    session: SessionDep,
    format: str = "xlsx",
    template: bool = False,
    include_pos: bool = False,
    _: User = Depends(require_permission("order", "view")),
):
    """Export Excel / CSV des commandes — une ligne par article.

    Colonnes compatibles avec ``POST /sales/orders/import`` : le fichier
    exporté se réimporte tel quel (``statut`` et ``montant_document`` sont
    ignorés par l'import).

    ``format`` : ``xlsx`` (défaut) ou ``csv`` ; ``template=1`` : en‑têtes seuls.
    """
    headers, rows = await SalesExportService(session).orders(
        include_rows=not template, include_pos=include_pos
    )
    return export_response(format, "Commandes", headers, rows)


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
    from app.core.documents.naming import content_disposition
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
            context = await builder.load_pos(order_id)
            path = await engine.arender_pos_ticket(order_id)
        except ValueError:
            raise HTTPException(status_code=404, detail="Vente introuvable")
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
        context = await builder.load_invoice(invoice.id)
        path = await engine.arender_invoice(invoice.id)

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


@router.post("/orders/{order_id}/close", response_model=SalesOrderRead)
async def close_order(
    order_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("order", "edit")),
):
    """Clôture la vente (facture soldée + bons de livraison terminés)."""
    service = OrderService(session)
    try:
        return await service.close_order(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


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
    from app.core.documents.naming import content_disposition

    try:
        context = await ContextBuilder().load_quote(quote_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Devis introuvable")
    engine = DocumentEngine()
    path = await engine.arender_quote(quote_id)
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
# Import en masse de commandes (Excel / CSV)
# ------------------------------------------------------------------ #
@router.post("/orders/import")
async def import_orders(
    file: UploadFile,
    session: SessionDep,
    user: User = Depends(require_permission("order", "create")),
):
    """Import de commandes depuis un fichier .xlsx ou .csv (une ligne = un article).

    Colonnes attendues (première ligne d'en-têtes) ::
        client | produit | quantite | prix_unitaire | remise | date
        | reference_commande (facultative : regroupe les lignes)

    Les commandes sont créées en brouillon ; clients et produits inconnus
    sont créés à la volée, le prix unitaire absent reprend le prix catalogue.
    """
    content = await file.read()
    rows = read_rows_from_bytes(file.filename or "import.csv", content)
    service = SalesImportService(session, company_id=user.company_id)
    return await service.import_orders(rows)


# ------------------------------------------------------------------ #
# Point de vente (comptoir)
# ------------------------------------------------------------------ #
@router.get("/pos/sales")
async def list_pos_sales(
    session: SessionDep,
    skip: int = 0,
    limit: int = 15,
    include_archived: bool = False,
    _: User = Depends(require_permission("order", "view")),
):
    """Historique des ventes comptoir — plus récent d'abord, paginé."""
    service = PosService(session)
    return await service.list_pos_sales(
        skip=skip, limit=limit, include_archived=include_archived
    )


@router.get("/pos/sales/{order_id}")
async def get_pos_sale(
    order_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("order", "view")),
):
    """Détail d'une vente comptoir (consultation seule, sans effet de bord)."""
    service = PosService(session)
    try:
        return await service.get_pos_sale(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/pos/sales/{order_id}/archive")
async def archive_pos_sale(
    order_id: int,
    session: SessionDep,
    _: User = Depends(require_permission("order", "edit")),
):
    """Archive une vente comptoir (masquage d'historique — comptabilité conservée)."""
    service = PosService(session)
    try:
        return await service.archive_pos_sale(order_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.post("/pos/sales")
async def create_pos_sale(
    body: PosSaleCreate,
    session: SessionDep,
    user: User = Depends(require_permission("order", "create")),
):
    """Vente comptoir simple → commande + stock + facture + paiement.

    Sans ``partner_id``, le service rattache la vente au partenaire walk-in
    « Client de passage » (encaissement sans client imposé).
    """
    service = PosService(session)
    try:
        return await service.create_pos_sale(body, company_id=user.company_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/pos/sales/{order_id}/ticket-html")
async def print_pos_ticket_html(
    order_id: int,
    _: User = Depends(require_permission("order", "view")),
):
    """Ticket de caisse en HTML (impression directe sur imprimante POS 80 mm).

    Le frontend ouvre ce HTML dans une fenêtre d'impression système :
    aucun PDF n'est généré ni téléchargé pour les tickets.
    """
    from fastapi.responses import HTMLResponse

    from app.core.documents.context import ContextBuilder
    from app.core.documents.engine import DocumentEngine

    try:
        context = await ContextBuilder().load_pos(order_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Vente introuvable")
    html = DocumentEngine().render_to_html("pos_ticket.html", context)
    return HTMLResponse(html)


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
    from app.core.documents.naming import content_disposition

    try:
        context = await ContextBuilder().load_pos(order_id)
    except ValueError:
        raise HTTPException(status_code=404, detail="Vente introuvable")
    engine = DocumentEngine()
    path = await engine.arender_pos_ticket(order_id)
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