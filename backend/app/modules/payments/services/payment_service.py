"""Service Paiements — encaissements/décaissements et suivi facture."""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.services.sequence_service import SequenceService
from app.modules.payments.models.payment import Payment
from app.modules.payments.schemas import PaymentCreate
from app.shared.enums import InvoiceStatus, PaymentMethod, PaymentStatus

logger = logging.getLogger(__name__)


class PaymentService:
    """Service des paiements."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sequences = SequenceService(session)

    async def list_payments(self, skip: int = 0, limit: int = 100) -> list[Payment]:
        result = await self.session.execute(
            select(Payment).order_by(Payment.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_payment(self, payment_id: int) -> Payment | None:
        return await self.session.get(Payment, payment_id)

    async def create_payment(self, data: PaymentCreate) -> Payment:
        method = data.method or PaymentMethod.CASH.value
        direction = data.direction or "in"
        is_receipt = direction == "in"
        prefix = "REC" if is_receipt else "PAY"

        reference = await self.sequences.next_value("payment", prefix)

        from app.modules.crm.models.partner import Partner

        partner = await self.session.get(Partner, data.partner_id)
        if partner is None:
            raise ValueError(f"Client {data.partner_id} introuvable")
        company_id = partner.company_id

        payment = Payment(
            reference=reference,
            payment_type="receipt" if is_receipt else "payment",
            direction=direction,
            partner_id=data.partner_id,
            invoice_id=data.invoice_id,
            method=method,
            amount=float(data.amount),
            payment_date=data.payment_date or date.today(),
            status=PaymentStatus.PAID.value,
            notes=data.notes,
            company_id=company_id,
        )
        self.session.add(payment)

        # Met à jour le montant payé de la facture + son statut
        if data.invoice_id:
            from app.modules.invoicing.models.invoice import Invoice

            invoice = await self.session.get(Invoice, data.invoice_id)
            if invoice:
                invoice.paid_amount = float(invoice.paid_amount or 0) + float(data.amount)
                if float(invoice.amount_due) <= 0:
                    invoice.status = InvoiceStatus.PAID.value
                else:
                    invoice.status = InvoiceStatus.PARTIALLY_PAID.value
                if invoice.company_id:
                    payment.company_id = invoice.company_id

        await self.session.commit()
        await self.session.refresh(payment)

        # Comptabilisation automatique (idempotente) — défensive
        try:
            from app.modules.accounting.services.posting_service import PostingService

            await PostingService(self.session).post_payment(payment)
            await self.session.commit()
            await self.session.refresh(payment)
        except Exception:  # pragma: no cover — défensif
            logger.exception(
                "Comptabilisation automatique impossible pour le paiement %s",
                payment.reference,
            )
            await self.session.rollback()

        return payment