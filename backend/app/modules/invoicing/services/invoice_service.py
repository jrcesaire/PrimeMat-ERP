"""Service Facturation — création de factures depuis les commandes."""
from __future__ import annotations

import logging
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.services.sequence_service import SequenceService
from app.modules.invoicing.models.invoice import (
    Invoice,
    InvoiceLine,
    InvoiceLineCut,
)
from app.modules.sales.models.order import SalesOrder, SalesOrderLine
from app.shared.enums import InvoiceStatus

logger = logging.getLogger(__name__)


class InvoiceService:
    """Service des factures."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sequences = SequenceService(session)

    async def get_invoice(self, invoice_id: int) -> Invoice | None:
        return await self.session.get(Invoice, invoice_id)

    async def list_invoices(self, skip: int = 0, limit: int = 100) -> list[Invoice]:
        result = await self.session.execute(
            select(Invoice)
            .options(
                selectinload(Invoice.lines).selectinload(InvoiceLine.cuts),
            )
            .order_by(Invoice.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def create_from_order(self, order_id: int, due_days: int = 0) -> Invoice:
        """Génère une facture depuis une commande (lignes + coupes préservées)."""
        from app.modules.sales.models.order import SalesOrder

        result = await self.session.execute(
            select(SalesOrder)
            .options(
                selectinload(SalesOrder.lines).selectinload(SalesOrderLine.cuts),
            )
            .where(SalesOrder.id == order_id)
        )
        order = result.scalar_one_or_none()
        if order is None:
            raise ValueError(f"Commande {order_id} introuvable")

        reference = await self.sequences.next_value("invoice", "INV")

        invoice = Invoice(
            reference=reference,
            order_id=order.id,
            partner_id=order.partner_id,
            status=InvoiceStatus.POSTED.value,
            invoice_date=date.today(),
            due_date=(date.today() + timedelta(days=due_days)) if due_days else None,
            currency_code=order.currency_code,
            amount_untaxed=float(order.amount_untaxed or 0),
            tax_amount=float(order.tax_amount or 0),
            amount_total=float(order.amount_total or 0),
            notes=order.notes,
            payment_communication=f"INV/{reference}",
            company_id=order.company_id,
        )

        for oline in order.lines:
            line = InvoiceLine(
                product_id=oline.product_id,
                description=oline.description,
                quantity=float(oline.quantity_ordered or 0),
                unit=oline.unit,
                sell_by_length=oline.sell_by_length,
                unit_price=float(oline.unit_price or 0),
                discount_percent=float(oline.discount_percent or 0),
                total_length=float(oline.total_length or 0),
                subtotal=float(oline.subtotal or 0),
                position=oline.position or 0,
                company_id=order.company_id,
            )
            if oline.cuts:
                for cut in oline.cuts:
                    line.cuts.append(
                        InvoiceLineCut(
                            quantity=float(cut.quantity),
                            length=float(cut.length),
                            unit_price=float(cut.unit_price) if cut.unit_price else None,
                        )
                    )
            invoice.lines.append(line)

        # Recalcule l'amount_total depuis les lignes (source de vérité)
        invoice.amount_total = sum(float(l.subtotal or 0) for l in invoice.lines)
        invoice.amount_untaxed = invoice.amount_total

        self.session.add(invoice)
        await self.session.commit()

        # Recharge avec les relations (lazy-load interdit hors session sync)
        result = await self.session.execute(
            select(Invoice)
            .options(
                selectinload(Invoice.lines).selectinload(InvoiceLine.cuts),
            )
            .where(Invoice.id == invoice.id)
        )
        loaded = result.scalar_one()

        # Comptabilisation automatique (idempotente) — ne bloque pas le flux
        # métier si la comptabilité échoue (module inactif, compte absent…).
        try:
            from app.modules.accounting.services.posting_service import PostingService

            await PostingService(self.session).post_invoice(loaded)
            await self.session.commit()
        except Exception:  # pragma: no cover — défensif
            logger.exception(
                "Comptabilisation automatique impossible pour la facture %s",
                loaded.reference,
            )
            await self.session.rollback()

        return loaded