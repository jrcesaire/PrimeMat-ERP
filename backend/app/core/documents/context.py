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

logger = logging.getLogger(__name__)


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
            "lines": invoice.lines,
            "currency": getattr(invoice.company, "currency_code", "XOF"),
            "document_type": "invoice",
            "cgv": cgv,
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
                    selectinload(Quote.lines).selectinload(QuoteLine.cuts),
                )
                .where(Quote.id == quote_id)
            )
            quote = result.scalar_one_or_none()

        if quote is None:
            raise ValueError(f"Devis {quote_id} introuvable")

        cgv = await ContextBuilder._load_cgv(session)
        return {
            "quote": quote,
            "company": quote.company,
            "partner": quote.partner,
            "lines": quote.lines,
            "currency": getattr(quote.company, "currency_code", "XOF"),
            "document_type": "quote",
            "cgv": cgv,
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
            "currency": getattr(company, "currency_code", "XOF") if company else "XOF",
            "document_type": "delivery",
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
            "currency": getattr(order.company, "currency_code", "XOF"),
            "document_type": "purchase_order",
        }
# ------------------------------------------------------------------ #
    # Builders async (utilisables directement dans les endpoints FastAPI)
    # ------------------------------------------------------------------ #
    async def load_invoice(self, invoice_id: int) -> dict[str, Any]:
        """Charge le contexte d'une facture (async, pour endpoints)."""
        from app.core.database import AsyncSessionLocal
        from app.modules.invoicing.models.invoice import Invoice, InvoiceLine
        from app.modules.invoicing.models.invoice import InvoiceLine
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Invoice)
                .options(
                    selectinload(Invoice.company),
                    selectinload(Invoice.partner),
                    selectinload(Invoice.lines).selectinload(InvoiceLine.cuts),
                )
                .where(Invoice.id == invoice_id)
            )
            invoice = result.scalar_one_or_none()
            partner = invoice.partner if invoice else None
            company = invoice.company if invoice else None

        if invoice is None:
            raise ValueError(f"Facture {invoice_id} introuvable")
        return {
            "doc": invoice, "invoice": invoice, "company": company,
            "partner": partner, "lines": invoice.lines,
            "currency": getattr(company, "currency_code", "XOF") if company else "XOF",
            "document_type": "invoice",
        }

    async def load_delivery(self, delivery_id: int) -> dict[str, Any]:
        """Charge le contexte d'un bon de livraison (async)."""
        from app.core.database import AsyncSessionLocal
        from app.modules.delivery.models.delivery import DeliveryLine
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
            "currency": getattr(company, "currency_code", "XOF") if company else "XOF",
            "document_type": "delivery",
        }

    async def load_quote(self, quote_id: int) -> dict[str, Any]:
        """Charge le contexte d'un devis (async)."""
        from app.core.database import AsyncSessionLocal
        from app.modules.sales.models.quote import Quote, QuoteLine
        from app.modules.sales.models.quote import QuoteLine
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload

        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(Quote)
                .options(
                    selectinload(Quote.company),
                    selectinload(Quote.partner),
                    selectinload(Quote.lines).selectinload(QuoteLine.cuts),
                )
                .where(Quote.id == quote_id)
            )
            quote = result.scalar_one_or_none()
            partner = quote.partner if quote else None
            company = quote.company if quote else None

        if quote is None:
            raise ValueError(f"Devis {quote_id} introuvable")
        return {
            "doc": quote, "quote": quote, "company": company,
            "partner": partner, "lines": quote.lines,
            "currency": getattr(company, "currency_code", "XOF") if company else "XOF",
            "document_type": "quote",
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
            "currency": getattr(invoice, "currency_code", "XOF") if invoice else "XOF",
            "document_type": "receipt",
            "total": float(payment.amount),
            "acompte": float(invoice.paid_amount - payment.amount) if invoice else 0.0,
            "solde": float(invoice.amount_due) if invoice else 0.0,
        }

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

        if order is None:
            raise ValueError(f"Vente comptoir {order_id} introuvable")
        pos_url = ""
        qr_data_uri = ""
        try:
            from app.core.services.setting_service import SettingService

            setting_service = SettingService(session)
            pos_url = await setting_service.get("pos_ticket_url", "") or ""
        except Exception:
            pos_url = ""

        # Génère le QR code (URL du site) → data URI PNG pour insertion dans le PDF
        if pos_url.strip():
            try:
                import base64
                import io as _io

                import qrcode

                img = qrcode.make(pos_url.strip())
                buf = _io.BytesIO()
                img.save(buf, format="PNG")
                b64 = base64.b64encode(buf.getvalue()).decode("ascii")
                qr_data_uri = f"data:image/png;base64,{b64}"
            except Exception:  # noqa: BLE001
                qr_data_uri = ""

        return {
            "doc": order, "order": order, "company": company,
            "partner": partner, "lines": order.lines,
            "currency": getattr(company, "currency_code", "XOF") if company else "XOF",
            "document_type": "pos_ticket",
            "total": float(order.amount_total or 0),
            "pos_url": pos_url,
            "qr_data_uri": qr_data_uri,
        }

