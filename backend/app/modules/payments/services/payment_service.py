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

    # Tolérance d'arrondi (unités monétaires) acceptée au-delà du reste dû —
    # absorbe les erreurs de flottants sur les montants à décimales.
    OVERPAYMENT_TOLERANCE = 1.0

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sequences = SequenceService(session)

    async def list_payments(
        self, skip: int = 0, limit: int = 100, invoice_id: int | None = None
    ) -> list[Payment]:
        """Paiements (plus récents d'abord), filtrables par facture."""
        stmt = select(Payment)
        if invoice_id is not None:
            stmt = stmt.where(Payment.invoice_id == invoice_id)
        result = await self.session.execute(
            stmt.order_by(Payment.id.desc()).offset(skip).limit(limit)
        )
        return list(result.scalars().all())

    async def get_payment(self, payment_id: int) -> Payment | None:
        return await self.session.get(Payment, payment_id)

    async def create_payment(self, data: PaymentCreate) -> Payment:
        method = data.method or PaymentMethod.CASH.value
        direction = data.direction or "in"
        is_receipt = direction == "in"
        prefix = "REC" if is_receipt else "PAY"

        # Contrôles serveur (S-7) — montant positif et pas de sur-paiement
        amount = float(data.amount)
        if amount <= 0:
            raise ValueError("Le montant du paiement doit être strictement positif")

        reference = await self.sequences.next_value("payment", prefix)

        from app.modules.crm.models.partner import Partner

        partner = await self.session.get(Partner, data.partner_id)
        if partner is None:
            raise ValueError(f"Client {data.partner_id} introuvable")
        company_id = partner.company_id

        # Journal comptable explicite (facultatif) — validé avant toute écriture
        journal_code = (data.journal_code or "").strip() or None
        if journal_code:
            from app.modules.accounting.models.journal import Journal

            known = await self.session.execute(
                select(Journal).where(
                    Journal.company_id == company_id,
                    Journal.code == journal_code,
                )
            )
            if known.scalar_one_or_none() is None:
                raise ValueError(f"Journal comptable inconnu : {journal_code}")

        # Contrôle de cohérence avec la facture liée (avant toute écriture)
        if data.invoice_id and is_receipt:
            from app.modules.invoicing.models.invoice import Invoice

            invoice = await self.session.get(Invoice, data.invoice_id)
            if invoice is not None:
                if invoice.status == InvoiceStatus.CANCELLED.value:
                    raise ValueError(
                        "Impossible d'encaisser une facture annulée"
                    )
                if invoice.status == InvoiceStatus.DRAFT.value:
                    raise ValueError(
                        "Impossible d'encaisser une facture en brouillon — "
                        "confirmez-la d'abord"
                    )
                due = float(invoice.amount_total or 0) - float(
                    invoice.paid_amount or 0
                )
                if amount > due + self.OVERPAYMENT_TOLERANCE:
                    raise ValueError(
                        f"Sur-paiement refusé : reste dû = {due:.2f}, "
                        f"paiement demandé = {amount:.2f}"
                    )

        payment = Payment(
            reference=reference,
            payment_type="receipt" if is_receipt else "payment",
            direction=direction,
            partner_id=data.partner_id,
            invoice_id=data.invoice_id,
            method=method,
            journal_code=journal_code,
            amount=float(data.amount),
            change_amount=max(0.0, float(data.change_amount or 0)),
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

    # ------------------------------------------------------------------ #
    # Reprise du document — retour en brouillon / suppression
    # ------------------------------------------------------------------ #
    async def _assert_posting_reversible(self, payment: Payment) -> None:
        """Refuse la révocation si l'écriture appartient à un exercice clôturé.

        Supprimer l'écriture d'un exercice clôturé fausserait les soldes
        OHADA : le refus est bloquant (400) et laisse le paiement intact.
        """
        from app.modules.accounting.services.posting_service import PostingService

        if payment.company_id is None:
            return
        entry = await PostingService(self.session).find_by_source(
            payment.company_id, "payment", payment.id
        )
        if entry is None:
            return

        from app.modules.accounting.models.fiscal_year import FiscalYear

        if entry.fiscal_year_id:
            fy = await self.session.get(FiscalYear, entry.fiscal_year_id)
            closed = fy is not None and fy.status == "closed"
        else:
            covering = await self.session.execute(
                select(FiscalYear).where(
                    FiscalYear.start_date <= entry.entry_date,
                    FiscalYear.end_date >= entry.entry_date,
                )
            )
            closed = any(f.status == "closed" for f in covering.scalars().all())
        if closed:
            raise ValueError(
                "Impossible : l'écriture comptable de ce paiement appartient "
                "à un exercice clôturé."
            )

    async def _drop_posting(self, payment: Payment) -> None:
        """Supprime l'écriture comptable du paiement (après vérification)."""
        from app.modules.accounting.services.posting_service import PostingService

        if payment.company_id is None:
            return
        entry = await PostingService(self.session).find_by_source(
            payment.company_id, "payment", payment.id
        )
        if entry is None:
            return
        reference = entry.reference
        await self.session.delete(entry)  # lignes en cascade
        logger.info(
            "Écriture %s supprimée — paiement %s remis en brouillon",
            reference,
            payment.reference,
        )

    async def back_to_draft(
        self, payment_id: int, user_id: int | None = None
    ) -> Payment:
        """Remet un paiement au brouillon — étape préalable à sa suppression.

        Révoque les effets du paiement dans l'ordre :
        1. retrait de l'écriture comptable (refusé si exercice clôturé) ;
        2. recalcul de ``invoice.paid_amount`` et du statut de la facture
           liée (symétrique de ``create_payment``) ;
        3. statut ``draft`` — seule condition de suppression autorisée.
        """
        result = await self.session.execute(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            raise ValueError(f"Paiement {payment_id} introuvable")
        if payment.status == PaymentStatus.DRAFT.value:
            raise ValueError("Ce paiement est déjà en brouillon.")

        # 1. Vérification puis retrait de l'écriture (gardiens AVANT mutation)
        await self._assert_posting_reversible(payment)
        await self._drop_posting(payment)

        # 2. Recalcul de la facture liée
        if payment.invoice_id:
            from app.modules.invoicing.models.invoice import Invoice

            invoice = await self.session.get(Invoice, payment.invoice_id)
            if invoice is not None:
                new_paid = max(
                    float(invoice.paid_amount or 0) - float(payment.amount or 0),
                    0.0,
                )
                invoice.paid_amount = new_paid
                if invoice.status not in (
                    InvoiceStatus.DRAFT.value,
                    InvoiceStatus.CANCELLED.value,
                ):
                    invoice.status = (
                        InvoiceStatus.POSTED.value
                        if new_paid <= 0
                        else InvoiceStatus.PARTIALLY_PAID.value
                    )

        # 3. Statut
        old_status = payment.status
        payment.status = PaymentStatus.DRAFT.value

        from app.core.services.audit_service import AuditService

        await AuditService(self.session).log(
            "payment.back_to_draft",
            "payment",
            payment.id,
            company_id=payment.company_id,
            user_id=user_id,
            old_values={"status": old_status},
            new_values={"status": PaymentStatus.DRAFT.value},
        )
        await self.session.commit()
        await self.session.refresh(payment)
        logger.info("Paiement %s remis en brouillon", payment.reference)
        return payment

    async def confirm(self, payment_id: int, user_id: int | None = None) -> Payment:
        """Re-confirme un paiement en brouillon — symétrique de ``back_to_draft``.

        1. re-jeu des contrôles métier (facture liée : existence, statut,
           sur-paiement — la facture a pu changer depuis la révocation) ;
        2. statut ``paid`` + recrédit de ``invoice.paid_amount`` ;
        3. recréation de l'écriture comptable (``post_payment`` idempotent) ;
        4. trace d'audit.
        """
        result = await self.session.execute(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            raise ValueError(f"Paiement {payment_id} introuvable")
        if payment.status != PaymentStatus.DRAFT.value:
            raise ValueError("Ce paiement n'est pas en brouillon — rien à confirmer.")

        amount = float(payment.amount or 0)
        if amount <= 0:
            raise ValueError("Le montant du paiement doit être strictement positif")

        # 1. Contrôles sur la facture liée (uniquement pour un encaissement)
        is_receipt = payment.direction == "in"
        invoice = None
        if payment.invoice_id and is_receipt:
            from app.modules.invoicing.models.invoice import Invoice

            invoice = await self.session.get(Invoice, payment.invoice_id)
            if invoice is None:
                raise ValueError(
                    "Facture liée introuvable — elle a été supprimée. "
                    "Supprimez ce paiement pour lever l'incohérence."
                )
            if invoice.status == InvoiceStatus.CANCELLED.value:
                raise ValueError("Impossible d'encaisser une facture annulée")
            if invoice.status == InvoiceStatus.DRAFT.value:
                raise ValueError(
                    "Impossible d'encaisser une facture en brouillon — "
                    "confirmez-la d'abord"
                )
            due = float(invoice.amount_total or 0) - float(invoice.paid_amount or 0)
            if amount > due + self.OVERPAYMENT_TOLERANCE:
                raise ValueError(
                    f"Sur-paiement refusé : reste dû = {due:.2f}, "
                    f"paiement demandé = {amount:.2f}"
                )
        elif payment.invoice_id:
            from app.modules.invoicing.models.invoice import Invoice

            invoice = await self.session.get(Invoice, payment.invoice_id)

        # 2. Statut + effet sur la facture (symétrique de back_to_draft)
        old_status = payment.status
        payment.status = PaymentStatus.PAID.value
        if invoice is not None:
            invoice.paid_amount = float(invoice.paid_amount or 0) + amount
            if float(invoice.amount_due) <= 0:
                invoice.status = InvoiceStatus.PAID.value
            else:
                invoice.status = InvoiceStatus.PARTIALLY_PAID.value
            if invoice.company_id:
                payment.company_id = invoice.company_id

        from app.core.services.audit_service import AuditService

        await AuditService(self.session).log(
            "payment.confirm",
            "payment",
            payment.id,
            company_id=payment.company_id,
            user_id=user_id,
            old_values={"status": old_status},
            new_values={"status": PaymentStatus.PAID.value},
        )
        await self.session.commit()
        await self.session.refresh(payment)

        # 3. Comptabilisation (idempotente) — défensive, même garde que create
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

        logger.info("Paiement %s re-confirmé", payment.reference)
        return payment

    async def delete_payment(
        self, payment_id: int, user_id: int | None = None
    ) -> None:
        """Supprime un paiement — brouillon uniquement.

        Garde-fous (cascade) : statut ``draft`` obligatoire (donc remise au
        brouillon préalable) et plus aucune écriture comptable rattachée.
        """
        result = await self.session.execute(
            select(Payment).where(Payment.id == payment_id).with_for_update()
        )
        payment = result.scalar_one_or_none()
        if payment is None:
            raise ValueError(f"Paiement {payment_id} introuvable")
        if payment.status != PaymentStatus.DRAFT.value:
            raise ValueError(
                "Seul un paiement au statut « brouillon » peut être supprimé "
                "— remettez-le d'abord au brouillon "
                f"(statut actuel : {payment.status})."
            )

        # Défense en profondeur : l'écriture a été retirée à la remise au brouillon
        from app.modules.accounting.services.posting_service import PostingService

        if payment.company_id is not None:
            entry = await PostingService(self.session).find_by_source(
                payment.company_id, "payment", payment.id
            )
            if entry is not None:
                raise ValueError(
                    "Impossible : une écriture comptable est encore rattachée "
                    "à ce paiement."
                )

        from app.core.services.audit_service import AuditService

        await AuditService(self.session).log(
            "payment.deleted",
            "payment",
            payment.id,
            company_id=payment.company_id,
            user_id=user_id,
            old_values={
                "reference": payment.reference,
                "status": payment.status,
                "amount": float(payment.amount or 0),
                "payment_date": str(payment.payment_date),
                "invoice_id": payment.invoice_id,
                "partner_id": payment.partner_id,
            },
        )
        await self.session.delete(payment)
        await self.session.commit()
        logger.info("Paiement %s supprimé", payment.reference)