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

    # ------------------------------------------------------------------ #
    # Helpers — reste à facturer
    # ------------------------------------------------------------------ #
    async def get_order_invoiced_total(self, order_id: int) -> float:
        """Total déjà facturé pour une commande (hors avoirs/annulées)."""
        result = await self.session.execute(
            select(Invoice.status, Invoice.amount_total).where(
                Invoice.order_id == order_id
            )
        )
        excluded = {
            InvoiceStatus.CANCELLED.value,
            InvoiceStatus.CREDIT.value,
        }
        return float(
            sum(amount for status, amount in result.all()
                if status not in excluded)
        )

    async def get_invoice(self, invoice_id: int) -> Invoice | None:
        return await self.session.get(Invoice, invoice_id)

    async def list_invoices(
        self, skip: int = 0, limit: int = 100, include_pos: bool = False
    ) -> list[Invoice]:
        """Factures, plus récentes d'abord.

        Les factures issues des ventes comptoir (commande
        ``fulfillment_mode="pos"``) sont exclues par défaut : elles vivent
        uniquement dans l'historique du Point de Vente.
        """
        stmt = (
            select(Invoice)
            .options(
                selectinload(Invoice.lines).selectinload(InvoiceLine.cuts),
            )
            .order_by(Invoice.id.desc())
            .offset(skip)
            .limit(limit)
        )
        if not include_pos:
            stmt = (
                stmt.outerjoin(SalesOrder, SalesOrder.id == Invoice.order_id).where(
                    (Invoice.order_id.is_(None))
                    | (SalesOrder.fulfillment_mode != "pos")
                )
            )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create_from_order(
        self,
        order_id: int,
        due_days: int = 0,
        mode: str = "full",
        value: float | None = None,
        post: bool = False,
    ) -> Invoice:
        """Génère une facture depuis une commande.

        - ``mode="full"`` : toutes les lignes (coupes préservées) ; si des
          acomptes existent déjà, facture de **solde** du reste à facturer.
        - ``mode="down_payment_percent"`` : acompte de ``value`` % du total.
        - ``mode="down_payment_fixed"`` : acompte de ``value`` (montant fixe).
        - ``post=False`` → brouillon (défaut, façon Odoo) ; ``post=True`` →
          comptabilisée immédiatement.

        Lève ``ValueError`` si la commande est introuvable, entièrement
        facturée, ou si le montant d'acompte est invalide.
        """
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

        order_total = float(order.amount_total or 0)
        invoiced = await self.get_order_invoiced_total(order.id)
        remaining = round(max(order_total - invoiced, 0.0), 2)
        if remaining <= 0.005:
            raise ValueError("Cette commande est déjà entièrement facturée")

        order_ref = getattr(order, "reference", None) or f"#{order.id}"
        # Ratio TVA proportionnel (0 si commande sans taxe)
        untaxed = float(order.amount_untaxed or 0)
        tax_ratio = float(order.tax_amount or 0) / untaxed if untaxed > 0 else 0.0

        reference = await self.sequences.next_value("invoice", "INV")

        invoice = Invoice(
            reference=reference,
            order_id=order.id,
            salesperson_id=getattr(order, "salesperson_id", None),
            partner_id=order.partner_id,
            status=InvoiceStatus.POSTED.value if post else InvoiceStatus.DRAFT.value,
            invoice_date=date.today(),
            due_date=(date.today() + timedelta(days=due_days)) if due_days else None,
            currency_code=order.currency_code,
            notes=order.notes,
            payment_communication=f"INV/{reference}",
            company_id=order.company_id,
        )

        if mode == "down_payment_percent":
            if value is None or value <= 0 or value > 100:
                raise ValueError("Pourcentage d'acompte invalide (attendu 0–100)")
            amount = round(min(order_total * value / 100, remaining), 2)
            if amount <= 0:
                raise ValueError("Le montant de l'acompte serait nul")
            invoice.lines.append(
                InvoiceLine(
                    description=f"Acompte {value:g} % — {order_ref}",
                    quantity=1,
                    unit="forfait",
                    unit_price=amount,
                    subtotal=amount,
                    company_id=order.company_id,
                )
            )
        elif mode == "down_payment_fixed":
            if value is None or value <= 0:
                raise ValueError("Montant d'acompte invalide")
            if value > remaining + 0.005:
                raise ValueError(
                    f"Le montant de l'acompte ({value:,.2f}) dépasse le reste "
                    f"à facturer ({remaining:,.2f})"
                )
            amount = round(value, 2)
            invoice.lines.append(
                InvoiceLine(
                    description=f"Acompte fixe — {order_ref}",
                    quantity=1,
                    unit="forfait",
                    unit_price=amount,
                    subtotal=amount,
                    company_id=order.company_id,
                )
            )
        elif invoiced > 0.005:
            # mode="full" avec acomptes existants → facture de solde
            invoice.lines.append(
                InvoiceLine(
                    description=f"Solde — {order_ref}",
                    quantity=1,
                    unit="forfait",
                    unit_price=remaining,
                    subtotal=remaining,
                    company_id=order.company_id,
                )
            )

        else:
            for oline in order.lines:
                line = InvoiceLine(
                    product_id=oline.product_id,
                    variant_id=oline.variant_id,
                    variant_name=oline.variant_name,
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
                                unit_price=(
                                    float(cut.unit_price) if cut.unit_price else None
                                ),
                            )
                        )
                invoice.lines.append(line)

        # Totaux — lignes HT + TVA proportionnelle (source de vérité : lignes)
        invoice.amount_untaxed = round(
            sum(float(l.subtotal or 0) for l in invoice.lines), 4
        )
        invoice.tax_amount = round(invoice.amount_untaxed * tax_ratio, 4)
        invoice.amount_total = round(invoice.amount_untaxed + invoice.tax_amount, 4)

        self.session.add(invoice)
        await self.session.commit()

        # Recharge avec les relations (lazy-load interdit hors session sync)
        loaded = await self._reload_invoice(invoice.id)

        if post:
            await self._post(loaded)

        return loaded

    async def post_invoice(self, invoice_id: int) -> Invoice:
        """Confirme une facture brouillon → POSTED (+ comptabilisation)."""
        invoice = await self.get_invoice(invoice_id)
        if invoice is None:
            raise ValueError(f"Facture {invoice_id} introuvable")
        if invoice.status != InvoiceStatus.DRAFT.value:
            raise ValueError(
                "Seule une facture en brouillon peut être confirmée "
                f"(statut actuel : {invoice.status})"
            )
        invoice.status = InvoiceStatus.POSTED.value
        await self.session.commit()
        loaded = await self._reload_invoice(invoice_id)
        await self._post(loaded)
        return loaded

    async def _reload_invoice(self, invoice_id: int) -> Invoice:
        result = await self.session.execute(
            select(Invoice)
            .options(
                selectinload(Invoice.lines).selectinload(InvoiceLine.cuts),
            )
            .where(Invoice.id == invoice_id)
        )
        return result.scalar_one()

    async def _post(self, invoice: Invoice) -> None:
        """Comptabilisation automatique (idempotente) — ne bloque pas le flux
        métier si la comptabilité échoue (module inactif, compte absent…)."""
        try:
            from app.modules.accounting.services.posting_service import PostingService

            await PostingService(self.session).post_invoice(invoice)
            await self.session.commit()
        except Exception:  # pragma: no cover — défensif
            logger.exception(
                "Comptabilisation automatique impossible pour la facture %s",
                invoice.reference,
            )
            await self.session.rollback()

    # ------------------------------------------------------------------ #
    # Reprise du document — retour en brouillon / annulation
    # ------------------------------------------------------------------ #
    async def _drop_posting(self, invoice: Invoice) -> bool:
        """Supprime l'écriture comptable générée pour cette facture.

        ``post_invoice`` comptabilise en une passe (écriture créée d'emblée au
        statut ``posted``).  La remise en brouillon / l'annulation étant une
        reprise du document avant tout paiement, l'écriture est retirée pour
        qu'une confirmation ultérieure comptabilise à nouveau sans doublon
        (``PostingService`` est idempotent par ``source_type``/``source_id``).

        Échec non bloquant : le module comptable peut être inactif.
        """
        try:
            from app.modules.accounting.services.posting_service import PostingService

            entry = await PostingService(self.session).find_by_source(
                invoice.company_id, "invoice", invoice.id
            )
            if entry is None:
                return False
            reference = entry.reference
            await self.session.delete(entry)  # lignes en cascade
            await self.session.commit()
            logger.info(
                "Écriture %s supprimée — facture %s reprise en amont",
                reference,
                invoice.reference,
            )
            return True
        except Exception:  # pragma: no cover — défensif
            logger.exception(
                "Écriture comptable non supprimée pour la facture %s",
                invoice.reference,
            )
            await self.session.rollback()
            return False

    async def _assert_not_paid(self, invoice: Invoice) -> None:
        """Refuse la reprise d'une facture déjà encaissée (même partiellement)."""
        if float(invoice.paid_amount or 0) > 0:
            raise ValueError(
                "Impossible : un paiement est déjà enregistré sur cette facture."
            )
        from app.modules.payments.models.payment import Payment

        result = await self.session.execute(
            select(Payment.id).where(Payment.invoice_id == invoice.id).limit(1)
        )
        if result.scalar_one_or_none() is not None:
            raise ValueError(
                "Impossible : des paiements sont rattachés à cette facture."
            )

    async def reset_to_draft(self, invoice_id: int) -> Invoice:
        """Remet une facture confirmée en brouillon (aucun paiement requis).

        Débloque le parcours de vente : une facture confirmée par erreur peut
        être corrigée puis re-confirmée.  Refusé dès qu'un encaissement existe.
        """
        invoice = await self.get_invoice(invoice_id)
        if invoice is None:
            raise ValueError(f"Facture {invoice_id} introuvable")
        if invoice.status == InvoiceStatus.DRAFT.value:
            raise ValueError("Cette facture est déjà en brouillon.")
        if invoice.status not in (
            InvoiceStatus.POSTED.value,
            InvoiceStatus.CANCELLED.value,
        ):
            raise ValueError(
                "Seule une facture confirmée ou annulée peut être remise en "
                f"brouillon (statut actuel : {invoice.status})."
            )
        await self._assert_not_paid(invoice)
        await self._drop_posting(invoice)
        invoice.status = InvoiceStatus.DRAFT.value
        await self.session.commit()
        logger.info("Facture %s remise en brouillon", invoice.reference)
        return await self._reload_invoice(invoice_id)

    async def cancel(self, invoice_id: int) -> Invoice:
        """Annule une facture non payée (brouillon ou confirmée).

        Libère la commande : une facture annulée ne compte plus dans le total
        déjà facturé (``get_order_invoiced_total``), un devis bloqué par une
        facture peut donc être repris.
        """
        invoice = await self.get_invoice(invoice_id)
        if invoice is None:
            raise ValueError(f"Facture {invoice_id} introuvable")
        if invoice.status == InvoiceStatus.CANCELLED.value:
            raise ValueError("Cette facture est déjà annulée.")
        if invoice.status not in (
            InvoiceStatus.DRAFT.value,
            InvoiceStatus.POSTED.value,
        ):
            raise ValueError(
                "Une facture ne peut être annulée qu'en brouillon ou confirmée "
                f"(statut actuel : {invoice.status})."
            )
        await self._assert_not_paid(invoice)
        await self._drop_posting(invoice)
        invoice.status = InvoiceStatus.CANCELLED.value
        # Détachement de la commande : la facture annulée ne doit plus
        # bloquer la remise en brouillon / la suppression de la commande
        # ni de son devis (sinon FK sales_orders.id → IntegrityError 500),
        # et la commande redevient intégralement facturable.
        invoice.order_id = None
        await self.session.commit()
        logger.info("Facture %s annulée", invoice.reference)
        return await self._reload_invoice(invoice_id)

    async def delete_invoice(
        self, invoice_id: int, user_id: int | None = None
    ) -> None:
        """Supprime une facture — brouillon uniquement (cascade).

        Garde-fous : statut ``draft`` (donc remise en brouillon préalable)
        et aucun paiement rattaché (``_assert_not_paid``).
        """
        result = await self.session.execute(
            select(Invoice).where(Invoice.id == invoice_id).with_for_update()
        )
        invoice = result.scalar_one_or_none()
        if invoice is None:
            raise ValueError(f"Facture {invoice_id} introuvable")
        if invoice.status != InvoiceStatus.DRAFT.value:
            raise ValueError(
                "Seule une facture en brouillon peut être supprimée — "
                "remettez-la d'abord en brouillon "
                f"(statut actuel : {invoice.status})."
            )
        await self._assert_not_paid(invoice)

        # Défense : une facture brouillon ne doit plus avoir d'écriture,
        # mais si subsiste, elle doit pouvoir être retirée (sinon refus).
        from app.modules.accounting.services.posting_service import PostingService

        if invoice.company_id is not None:
            entry = await PostingService(self.session).find_by_source(
                invoice.company_id, "invoice", invoice.id
            )
            if entry is not None and not await self._drop_posting(invoice):
                raise ValueError(
                    "Impossible : l'écriture comptable de cette facture "
                    "n'a pas pu être retirée."
                )

        from app.core.services.audit_service import AuditService

        await AuditService(self.session).log(
            "invoice.deleted",
            "invoice",
            invoice.id,
            company_id=invoice.company_id,
            user_id=user_id,
            old_values={
                "reference": invoice.reference,
                "status": invoice.status,
                "order_id": invoice.order_id,
                "partner_id": invoice.partner_id,
                "amount_total": float(invoice.amount_total or 0),
            },
        )
        await self.session.delete(invoice)  # cascade lines + cuts
        await self.session.commit()
        logger.info("Facture %s supprimée", invoice.reference)

