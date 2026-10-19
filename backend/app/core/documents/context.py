"""
Constructeurs de contexte pour les documents.

Chaque méthode récupère les données métier nécessaires et les organise
en dictionnaire exploitable par les templates Jinja2.

Ces builders sont **indépendants** des modules métier :
ils utilisent le Session de la base de données mais ne dépendent
pas de l'import du module source (lazy imports).
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.documents.naming import document_filename, document_title

logger = logging.getLogger(__name__)


def _naming(kind: str, reference: Any) -> dict[str, str]:
    """Clés de nommage d'un document : titre affiché + nom de fichier du PDF.

    Source unique de vérité partagée par les templates (``<title>``), la
    métadonnée ``/Title`` du PDF et l'en-tête ``Content-Disposition`` —
    voir :mod:`app.core.documents.naming`.
    """
    return {
        "doc_title": document_title(kind, reference),
        "doc_filename": document_filename(kind, reference),
    }


class ContextBuilder:
    """Construit les contextes de données pour les templates de documents."""

    @staticmethod
    async def _load_cgv(session: Any) -> str:
        """Charge le texte des CGV depuis les paramètres (vide si indisponible)."""
        try:
            from app.core.services.setting_service import SettingService

            svc = SettingService(session)
            return await svc.get("cgv_content", "") or ""
        except Exception:  # noqa: BLE001
            return ""

    async def build_invoice_context(self, invoice_id: int) -> dict[str, Any]:
        """Contexte pour une facture."""
        from app.core.database import AsyncSessionLocal
        from app.modules.invoicing.models.invoice import Invoice, InvoiceLine
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Invoice)
                .options(
                    selectinload(Invoice.company),
                    selectinload(Invoice.partner),
                    selectinload(Invoice.salesperson),
                    selectinload(Invoice.lines).selectinload(InvoiceLine.cuts),
                )
                .where(Invoice.id == invoice_id)
            )
            invoice = result.scalar_one_or_none()

        if invoice is None:
            raise ValueError(f"Facture {invoice_id} introuvable")

        cgv = await ContextBuilder._load_cgv(session)
        return {
            "invoice": invoice,
            "company": invoice.company,
            "partner": invoice.partner,
            "salesperson": invoice.salesperson,
            "lines": invoice.lines,
            "currency": getattr(invoice.company, "currency_code", "FCFA"),
            "document_type": "invoice",
            "cgv": cgv,
            **_naming("invoice", invoice.reference),
        }

    async def build_quote_context(self, quote_id: int) -> dict[str, Any]:
        """Contexte pour un devis."""
        from app.core.database import AsyncSessionLocal
        from app.modules.sales.models.quote import Quote, QuoteLine
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Quote)
                .options(
                    selectinload(Quote.company),
                    selectinload(Quote.partner),
                    selectinload(Quote.salesperson),
                    selectinload(Quote.lines).selectinload(QuoteLine.cuts),
                )
                .where(Quote.id == quote_id)
            )
            quote = result.scalar_one_or_none()
            # Fallback : devis orphelin → commercial = créateur du document.
            salesperson = quote.salesperson if quote else None
            if quote is not None and salesperson is None and quote.created_by:
                from app.core.models.user import User

                salesperson = await session.get(User, quote.created_by)

        if quote is None:
            raise ValueError(f"Devis {quote_id} introuvable")

        cgv = await ContextBuilder._load_cgv(session)
        return {
            "quote": quote,
            "company": quote.company,
            "partner": quote.partner,
            "salesperson": salesperson,
            "lines": quote.lines,
            "currency": getattr(quote.company, "currency_code", "FCFA"),
            "document_type": "quote",
            "cgv": cgv,
            **_naming("quote", quote.reference),
        }

    async def build_delivery_context(self, delivery_id: int) -> dict[str, Any]:
        """Contexte pour un bon de livraison (tout charge dans la session)."""
        from app.core.database import AsyncSessionLocal
        from app.modules.delivery.models.delivery import DeliveryNote, DeliveryLine
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(DeliveryNote)
                .options(
                    selectinload(DeliveryNote.company),
                    selectinload(DeliveryNote.partner),
                    selectinload(DeliveryNote.lines).selectinload(DeliveryLine.cuts),
                    selectinload(DeliveryNote.order),
                )
                .where(DeliveryNote.id == delivery_id)
            )
            delivery = result.scalar_one_or_none()
            if delivery is None:
                raise ValueError(f"Livraison {delivery_id} introuvable")

            company = delivery.company
            partner = delivery.partner
            lines = list(delivery.lines)
            # Prefetch les coupes + noms produits (evite les lazy-loads post-session)
            lines_data = []
            for line in lines:
                lines_data.append({
                    "obj": line,
                    "cuts": list(line.cuts) if hasattr(line, "cuts") else [],
                })
            order = delivery.order
            order_ref = order.reference if order else None

        return {
            "delivery": delivery,
            "company": company,
            "partner": partner,
            "lines": lines,
            "order_ref": order_ref,
            "currency": getattr(company, "currency_code", "FCFA") if company else "FCFA",
            "document_type": "delivery",
            **_naming("delivery", delivery.reference),
        }

    async def build_purchase_order_context(self, order_id: int) -> dict[str, Any]:
        """Contexte pour un bon de commande fournisseur."""
        from app.core.database import AsyncSessionLocal
        from app.modules.purchases.models.purchase_order import PurchaseOrder
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(PurchaseOrder)
                .options(
                    selectinload(PurchaseOrder.company),
                    selectinload(PurchaseOrder.supplier),
                    selectinload(PurchaseOrder.lines),
                )
                .where(PurchaseOrder.id == order_id)
            )
            order = result.scalar_one_or_none()

        if order is None:
            raise ValueError(f"Bon de commande {order_id} introuvable")

        return {
            "order": order,
            "company": order.company,
            "supplier": order.supplier,
            "lines": order.lines,
            "currency": getattr(order.company, "currency_code", "FCFA"),
            "document_type": "purchase_order",
            **_naming("purchase_order", order.number),
        }
# ------------------------------------------------------------------ #
    # Builders async (utilisables directement dans les endpoints FastAPI)
    # ------------------------------------------------------------------ #
    async def load_invoice(self, invoice_id: int) -> dict[str, Any]:
        """Charge le contexte d'une facture (async, pour endpoints)."""
        from app.core.database import AsyncSessionLocal
        from app.modules.invoicing.models.invoice import Invoice, InvoiceLine
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Invoice)
                .options(
                    selectinload(Invoice.company),
                    selectinload(Invoice.partner),
                    selectinload(Invoice.salesperson),
                    selectinload(Invoice.lines).selectinload(InvoiceLine.cuts),
                )
                .where(Invoice.id == invoice_id)
            )
            invoice = result.scalar_one_or_none()
            partner = invoice.partner if invoice else None
            company = invoice.company if invoice else None
            cgv = await ContextBuilder._load_cgv(session)

        if invoice is None:
            raise ValueError(f"Facture {invoice_id} introuvable")
        return {
            "doc": invoice, "invoice": invoice, "company": company,
            "partner": partner, "salesperson": invoice.salesperson, "lines": invoice.lines,
            "currency": getattr(company, "currency_code", "FCFA") if company else "FCFA",
            "document_type": "invoice",
            "cgv": cgv,
            **_naming("invoice", invoice.reference),
        }

    async def load_delivery(self, delivery_id: int) -> dict[str, Any]:
        """Charge le contexte d'un bon de livraison (async)."""
        from app.core.database import AsyncSessionLocal
        from app.modules.delivery.models.delivery import DeliveryLine, DeliveryNote
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(DeliveryNote)
                .options(
                    selectinload(DeliveryNote.company),
                    selectinload(DeliveryNote.partner),
                    selectinload(DeliveryNote.lines).selectinload(DeliveryLine.cuts),
                    selectinload(DeliveryNote.order),
                )
                .where(DeliveryNote.id == delivery_id)
            )
            note = result.scalar_one_or_none()
            company = note.company if note else None
            partner = note.partner if note else None

        if note is None:
            raise ValueError(f"Livraison {delivery_id} introuvable")
        return {
            "doc": note, "delivery": note, "company": company,
            "partner": partner, "lines": note.lines, "order": note.order,
            "currency": getattr(company, "currency_code", "FCFA") if company else "FCFA",
            "document_type": "delivery",
            **_naming("delivery", note.reference),
        }

    async def load_quote(self, quote_id: int) -> dict[str, Any]:
        """Charge le contexte d'un devis (async)."""
        from app.core.database import AsyncSessionLocal
        from app.modules.sales.models.quote import Quote, QuoteLine
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Quote)
                .options(
                    selectinload(Quote.company),
                    selectinload(Quote.partner),
                    selectinload(Quote.salesperson),
                    selectinload(Quote.lines).selectinload(QuoteLine.cuts),
                )
                .where(Quote.id == quote_id)
            )
            quote = result.scalar_one_or_none()
            partner = quote.partner if quote else None
            company = quote.company if quote else None
            cgv = await ContextBuilder._load_cgv(session)

        if quote is None:
            raise ValueError(f"Devis {quote_id} introuvable")
        return {
            "doc": quote, "quote": quote, "company": company,
            "partner": partner, "salesperson": quote.salesperson, "lines": quote.lines,
            "currency": getattr(company, "currency_code", "FCFA") if company else "FCFA",
            "document_type": "quote",
            "cgv": cgv,
            **_naming("quote", quote.reference),
        }

    async def load_payment(self, payment_id: int) -> dict[str, Any]:
        """Charge le contexte d'un paiement (reçu)."""
        from app.core.database import AsyncSessionLocal
        from app.modules.payments.models.payment import Payment
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Payment)
                .options(
                    selectinload(Payment.invoice),
                    selectinload(Payment.partner),
                    selectinload(Payment.company),
                )
                .where(Payment.id == payment_id)
            )
            payment = result.scalar_one_or_none()
            partner = payment.partner if payment else None
            company = payment.company if payment else None

        if payment is None:
            raise ValueError(f"Paiement {payment_id} introuvable")
        invoice = payment.invoice
        if company is None and invoice is not None:
            company = invoice.company

        return {
            "doc": payment, "payment": payment, "partner": partner,
            "invoice": invoice, "company": company,
            "currency": getattr(invoice, "currency_code", "FCFA") if invoice else "FCFA",
            "document_type": "receipt",
            **_naming("receipt", payment.reference),
            "total": float(payment.amount),
            "acompte": float(invoice.paid_amount - payment.amount) if invoice else 0.0,
            "solde": float(invoice.amount_due) if invoice else 0.0,
        }

    @staticmethod
    def _pos_qr_payload(order: Any) -> str:
        """Contenu du QR du ticket POS : numéro de commande + date et heure."""
        created = getattr(order, "created_at", None)
        if created is not None:
            stamp = created.strftime("%d/%m/%Y %H:%M")
        else:
            od = getattr(order, "order_date", None)
            stamp = od.strftime("%d/%m/%Y") if od else ""
        return f"{order.reference} | {stamp}"

    async def load_pos(self, order_id: int) -> dict[str, Any]:
        """Charge le contexte d'une vente comptoir (ticket de caisse)."""
        from app.core.database import AsyncSessionLocal
        from app.modules.sales.models.order import SalesOrder
        from app.modules.sales.models.order import SalesOrderLine
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(SalesOrder)
                .options(
                    selectinload(SalesOrder.company),
                    selectinload(SalesOrder.partner),
                    selectinload(SalesOrder.lines).selectinload(SalesOrderLine.cuts),
                )
                .where(SalesOrder.id == order_id, SalesOrder.fulfillment_mode == "pos")
            )
            order = result.scalar_one_or_none()
            partner = order.partner if order else None
            company = order.company if order else None

            # Dernier reçu de la facture — montant reçu et monnaie rendue.
            amount_paid = 0.0
            amount_received = 0.0
            change_amount = 0.0
            if order is not None:
                from app.modules.invoicing.models.invoice import Invoice
                from app.modules.payments.models.payment import Payment

                inv_res = await session.execute(
                    select(Invoice)
                    .where(Invoice.order_id == order.id)
                    .order_by(Invoice.id.desc())
                    .limit(1)
                )
                invoice = inv_res.scalars().first()
                if invoice is not None:
                    pay_res = await session.execute(
                        select(Payment)
                        .where(Payment.invoice_id == invoice.id)
                        .order_by(Payment.id.desc())
                        .limit(1)
                    )
                    payment = pay_res.scalars().first()
                    if payment is not None:
                        amount_paid = float(payment.amount or 0)
                        change_amount = float(payment.change_amount or 0)
                        amount_received = amount_paid + change_amount

        if order is None:
            raise ValueError(f"Vente comptoir {order_id} introuvable")
        pos_url = ""
        try:
            from app.core.services.setting_service import SettingService

            setting_service = SettingService(session)
            pos_url = await setting_service.get("pos_ticket_url", "") or ""
        except Exception:
            pos_url = ""

        # QR code systématique : numéro de commande + date et heure
        qr_content = self._pos_qr_payload(order)
        qr_data_uri = ""
        try:
            import base64
            import io as _io

            import qrcode

            img = qrcode.make(qr_content)
            buf = _io.BytesIO()
            img.save(buf, format="PNG")
            b64 = base64.b64encode(buf.getvalue()).decode("ascii")
            qr_data_uri = f"data:image/png;base64,{b64}"
        except Exception:  # noqa: BLE001
            qr_data_uri = ""

        return {
            "doc": order, "order": order, "company": company,
            "partner": partner, "lines": order.lines,
            "currency": getattr(company, "currency_code", "FCFA") if company else "FCFA",
            "document_type": "pos_ticket",
            **_naming("pos_ticket", order.reference),
            "total": float(order.amount_total or 0),
            "amount_paid": amount_paid,
            "amount_received": amount_received,
            "change_amount": change_amount,
            "pos_url": pos_url,
            "qr_data_uri": qr_data_uri,
        }

