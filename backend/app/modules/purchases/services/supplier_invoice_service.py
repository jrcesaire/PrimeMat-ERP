"""
Service Facture fournisseur — saisie, rapprochement 3 voies, comptabilité.

Rapprochement (BC × BR × facture) :
- ``match_ok``      : quantités et prix cohérents ;
- ``qty_diff``      : quantité facturée ≠ commandée / reçue ;
- ``price_diff``    : prix unitaire facturé ≠ prix BC ;
- ``no_reference``  : facture saisie sans BC liée.

Comptabilisation (module Accounting) :
- à ``posted`` : D 601 (achats marchandises) + D 4452 (TVA déductible)
  / C 401 (fournisseurs) — journal ACH.
"""
from __future__ import annotations

import logging
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.services.sequence_service import SequenceService
from app.core.services.setting_service import SettingService
from app.modules.crm.models.partner import Partner
from app.modules.purchases.models import (
    PurchaseOrder,
    PurchaseOrderLine,
    SupplierInvoice,
    SupplierInvoiceLine,
)
from app.modules.purchases.schemas import (
    MatchingLineDetail,
    MatchingResult,
    PosPurchaseCreate,
    SupplierInvoiceCreate,
    SupplierInvoiceLineCreate,
    SupplierInvoiceUpdate,
)
from app.shared.enums import SupplierInvoiceStatus

logger = logging.getLogger(__name__)

#: Pas de conversion monétaire (centime).
CENTS = Decimal("0.01")


def _cents(value: float | str | None) -> Decimal:
    """Convertit un montant en ``Decimal`` arrondi au centime."""
    return Decimal(str(value or 0)).quantize(CENTS, rounding=ROUND_HALF_UP)


def _recompute_totals(invoice: SupplierInvoice) -> None:
    """Recalcule les totaux de la facture depuis ses lignes."""
    untaxed = sum(line.subtotal for line in invoice.lines)
    tax = sum(line.tax_amount for line in invoice.lines)
    invoice.amount_untaxed = untaxed
    invoice.tax_amount = tax
    invoice.amount_total = untaxed + tax


class SupplierInvoiceService:
    """Gestion des factures fournisseur."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sequences = SequenceService(session)

    # ------------------------------------------------------------------ #
    # Alerte régime fiscal (TEE/RME → TVA non applicable)
    # ------------------------------------------------------------------ #
    async def tva_regime_warning(
        self, company_id: int | None, tax_amount: float | None
    ) -> str | None:
        """Alerte si le régime fiscal interdit la TVA (TEE / RME) alors qu'une
        TVA est présente sur la facture.

        Règle Phase 2 : ALERTE UNIQUEMENT — ne bloque ni la saisie ni la
        comptabilisation, ne bascule jamais de régime automatiquement.
        """
        try:
            amount = float(tax_amount or 0)
        except (TypeError, ValueError):
            return None
        if amount <= 0 or company_id is None:
            return None

        from app.core.models.company import Company
        from app.modules.accounting.services.fiscal_regime import TaxRegimeService

        company = await self.session.get(Company, company_id)
        if company is None:
            return None
        regime = getattr(company, "tax_regime", None)
        if not TaxRegimeService.is_tva_blocked(regime):
            return None
        regime_label = regime.value if hasattr(regime, "value") else regime
        return (
            f"Régime fiscal {regime_label} : la TVA n'est pas applicable "
            f"(montant TVA saisi : {amount:.2f} FCFA). Vérifiez le régime "
            "dans Paramètres > Régime fiscal."
        )

    async def attach_tva_warning(self, invoice: SupplierInvoice) -> None:
        """Pose l'attribut non persisté `tva_regime_warning` sur la facture
        (repris par le schéma SupplierInvoiceRead)."""
        invoice.tva_regime_warning = await self.tva_regime_warning(
            invoice.company_id, invoice.tax_amount
        )

    # ------------------------------------------------------------------ #
    # Lecture
    # ------------------------------------------------------------------ #
    async def list_invoices(
        self,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
        supplier_id: int | None = None,
    ) -> list[SupplierInvoice]:
        stmt = select(SupplierInvoice).options(
            selectinload(SupplierInvoice.lines),
            selectinload(SupplierInvoice.supplier),
        )
        if status:
            stmt = stmt.where(SupplierInvoice.status == status)
        if supplier_id:
            stmt = stmt.where(SupplierInvoice.supplier_id == supplier_id)
        stmt = stmt.order_by(SupplierInvoice.id.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        invoices = list(result.scalars().all())
        for inv in invoices:
            await self.attach_tva_warning(inv)
        return invoices

    async def get_invoice(self, invoice_id: int) -> SupplierInvoice | None:
        stmt = (
            select(SupplierInvoice)
            .options(
                selectinload(SupplierInvoice.lines),
                selectinload(SupplierInvoice.supplier),
                selectinload(SupplierInvoice.order).selectinload(
                    PurchaseOrder.lines
                ),
            )
            .where(SupplierInvoice.id == invoice_id)
        )
        result = await self.session.execute(stmt)
        invoice = result.scalars().first()
        if invoice is not None:
            await self.attach_tva_warning(invoice)
        return invoice


    # ------------------------------------------------------------------ #
    # Écriture
    # ------------------------------------------------------------------ #
    async def create_invoice(
        self, data: SupplierInvoiceCreate, company_id: int
    ) -> SupplierInvoice:
        if not data.lines:
            raise ValueError("La facture fournisseur doit comporter au moins une ligne.")

        reference = await self.sequences.next_value("supplier_invoice", "FAF")

        # Échéance : date facture + conditions de paiement du fournisseur
        due_date = data.due_date
        if due_date is None and data.invoice_date is not None:
            supplier = await self.session.get(Partner, data.supplier_id)
            terms = getattr(supplier, "payment_terms_days", None) if supplier else None
            if terms:
                due_date = data.invoice_date + timedelta(days=terms)

        invoice = SupplierInvoice(
            reference=reference,
            supplier_invoice_number=data.supplier_invoice_number,
            supplier_id=data.supplier_id,
            order_id=data.order_id,
            reception_id=data.reception_id,
            status=SupplierInvoiceStatus.DRAFT.value,
            invoice_date=data.invoice_date or date.today(),
            due_date=due_date,
            currency_code=data.currency_code,
            notes=data.notes,
            company_id=company_id,
        )
        self.session.add(invoice)

        for line_data in data.lines:
            invoice.lines.append(
                SupplierInvoiceLine(
                    order_line_id=line_data.order_line_id,
                    product_id=line_data.product_id,
                    description=line_data.description,
                    quantity=line_data.quantity,
                    unit_price=line_data.unit_price,
                    tax_rate=line_data.tax_rate,
                    company_id=company_id,
                )
            )

        _recompute_totals(invoice)
        # Rapprochement automatique si BC liée
        if data.order_id is not None:
            matching = await self._compute_matching(invoice)
            invoice.matching_status = matching.status
            invoice.matching_details = matching.model_dump()

        await self.session.commit()
        await self.session.refresh(invoice)
        logger.info("Facture fournisseur %s créée", reference)
        # Alerte régime fiscal TEE/RME — informative, jamais bloquante
        await self.attach_tva_warning(invoice)
        if invoice.tva_regime_warning:
            logger.warning(
                "Facture fournisseur %s : %s", reference, invoice.tva_regime_warning
            )
        return invoice

    async def update_invoice(
        self, invoice_id: int, data: SupplierInvoiceUpdate
    ) -> SupplierInvoice | None:
        invoice = await self.get_invoice(invoice_id)
        if invoice is None:
            return None
        if invoice.status != SupplierInvoiceStatus.DRAFT.value:
            raise ValueError("Seule une facture brouillon peut être modifiée.")

        for field in ("supplier_invoice_number", "invoice_date", "due_date", "notes"):
            value = getattr(data, field, None)
            if value is not None:
                setattr(invoice, field, value)

        if data.lines is not None:
            if not data.lines:
                raise ValueError("La facture fournisseur doit comporter au moins une ligne.")
            invoice.lines.clear()
            await self.session.flush()
            for line_data in data.lines:
                invoice.lines.append(
                    SupplierInvoiceLine(
                        order_line_id=line_data.order_line_id,
                        product_id=line_data.product_id,
                        description=line_data.description,
                        quantity=line_data.quantity,
                        unit_price=line_data.unit_price,
                        tax_rate=line_data.tax_rate,
                        company_id=invoice.company_id,
                    )
                )

        _recompute_totals(invoice)
        if invoice.order_id is not None:
            matching = await self._compute_matching(invoice)
            invoice.matching_status = matching.status
            invoice.matching_details = matching.model_dump()

        await self.session.commit()
        await self.session.refresh(invoice)
        await self.attach_tva_warning(invoice)
        return invoice



    # ------------------------------------------------------------------ #
    # Workflow — comptabilisation / paiement
    # ------------------------------------------------------------------ #
    async def post(self, invoice_id: int) -> SupplierInvoice | None:
        """Enregistre la facture et génère l'écriture comptable ACH."""
        invoice = await self.get_invoice(invoice_id)
        if invoice is None:
            return None
        if invoice.status != SupplierInvoiceStatus.DRAFT.value:
            raise ValueError("Seule une facture brouillon peut être enregistrée.")

        invoice.status = SupplierInvoiceStatus.POSTED.value
        invoice.posted_at = datetime.utcnow()
        await self.session.commit()

        # Écriture comptable (idempotente — gérée par PostingService)
        try:
            from app.modules.accounting.services.posting_service import PostingService

            await PostingService(self.session).post_supplier_invoice(invoice)
            await self.session.commit()
        except Exception:
            logger.exception(
                "Écriture comptable non générée pour la facture %s",
                invoice.reference,
            )
            await self.session.rollback()

        await self.session.refresh(invoice)
        # Alerte régime fiscal : informatif, la comptabilisation n'est JAMAIS bloquée
        await self.attach_tva_warning(invoice)
        if invoice.tva_regime_warning:
            logger.warning(
                "Comptabilisation facture %s : %s",
                invoice.reference,
                invoice.tva_regime_warning,
            )
        logger.info("Facture fournisseur %s enregistrée + comptabilisée", invoice.reference)
        return invoice

    async def pay(
        self,
        invoice_id: int,
        amount: float,
        payment_date: date | None = None,
        *,
        treasury_account: str = "511",
        journal_code: str = "BAN",
    ) -> SupplierInvoice | None:
        """Enregistre un règlement fournisseur (décaissement).

        ``treasury_account`` / ``journal_code`` permettent de choisir le compte
        décaissé : banque (``511``/``BAN``) par défaut, caisse (``531``/``CAI``)
        pour un achat comptoir saisi depuis le PoS.
        """
        invoice = await self.get_invoice(invoice_id)
        if invoice is None:
            return None
        if invoice.status not in (
            SupplierInvoiceStatus.POSTED.value,
            SupplierInvoiceStatus.PAID.value,
        ):
            raise ValueError("Seule une facture enregistrée peut être réglée.")
        if amount <= 0:
            raise ValueError("Le montant du règlement doit être positif.")
        if amount > float(invoice.amount_due) + 1e-9:
            raise ValueError(
                f"Montant supérieur au reste dû ({float(invoice.amount_due):.2f})."
            )

        invoice.paid_amount = float(invoice.paid_amount) + amount
        if float(invoice.paid_amount) >= float(invoice.amount_total) - 1e-9:
            invoice.status = SupplierInvoiceStatus.PAID.value
        await self.session.commit()

        try:
            from app.modules.accounting.services.posting_service import PostingService

            await PostingService(self.session).post_supplier_payment(
                invoice,
                amount,
                payment_date or date.today(),
                treasury_account=treasury_account,
                journal_code=journal_code,
            )
            await self.session.commit()
        except Exception:
            logger.exception(
                "Écriture de règlement non générée pour %s", invoice.reference
            )
            await self.session.rollback()

        await self.session.refresh(invoice)
        await self.attach_tva_warning(invoice)
        logger.info("Règlement %.2f enregistré sur %s", amount, invoice.reference)
        return invoice

    # ------------------------------------------------------------------ #
    # Achat de quincaillerie saisi depuis le Point de Vente (PRD US5)
    # ------------------------------------------------------------------ #
    async def create_pos_purchase(
        self, data: PosPurchaseCreate, company_id: int
    ) -> SupplierInvoice:
        """Crée, comptabilise et règle un achat comptoir saisi depuis le PoS.

        Le montant saisi est **TTC** : la base hors taxes et la TVA en sont
        déduites au centime, de sorte que ``HT + TVA == TTC`` exactement (les
        écritures comptables exigent un équilibre au centime près). La facture
        fournisseur générée suit le workflow standard (``draft → posted →
        paid``) afin d'apparaître dans le module Achats global (liste des
        factures fournisseur) et dans le grand livre
        (``D 601 + D 4452 / C 401`` puis ``D 401 / C trésorerie``).

        Une facture non réglée (``paid=False``) reste enregistrée en attente de
        règlement dans le module Achats.
        """
        total = _cents(data.amount_total)
        if total <= 0:
            raise ValueError("Le montant de l'achat doit être supérieur à zéro.")

        rate = Decimal(str(data.tax_rate or 0))
        # Montant TTC → base hors taxes ; la TVA est le complément exact du TTC,
        # ce qui absorbe l'arrondi et garantit l'équilibre de l'écriture.
        untaxed = (
            (total / (1 + rate / 100)).quantize(CENTS, rounding=ROUND_HALF_UP)
            if rate > 0
            else total
        )
        tax = total - untaxed
        purchase_date = data.purchase_date or date.today()

        # Compte de trésorerie décaissé : déduit du mode de règlement (caisse
        # 531 pour un paiement en espèces, banque 511 sinon), sauf surcharge.
        from app.modules.accounting.services.posting_service import TREASURY_ACCOUNTS

        treasury_account = data.treasury_account or TREASURY_ACCOUNTS.get(
            data.payment_method, "531"
        )
        journal_code = data.journal_code or (
            "CAI" if treasury_account == "531" else "BAN"
        )

        invoice = await self.create_invoice(
            SupplierInvoiceCreate(
                supplier_id=data.supplier_id,
                supplier_invoice_number=data.supplier_invoice_number,
                invoice_date=purchase_date,
                due_date=purchase_date,
                notes=data.notes or "Achat de quincaillerie saisi depuis le PoS",
                lines=[
                    SupplierInvoiceLineCreate(
                        description=data.label,
                        quantity=1,
                        unit_price=float(untaxed),
                        tax_rate=float(rate),
                    )
                ],
            ),
            company_id,
        )

        # Fige les totaux recalculés par la ligne : la ventilation HT / TVA est
        # celle saisie au comptoir (HT + TVA == TTC au centime).
        invoice.amount_untaxed = float(untaxed)
        invoice.tax_amount = float(tax)
        invoice.amount_total = float(total)
        await self.session.commit()
        await self.session.refresh(invoice)

        posted = await self.post(invoice.id)
        if posted is None:
            raise ValueError("Comptabilisation de l'achat impossible.")

        if not data.paid:
            return posted

        due = float(posted.amount_due)
        if due <= 0:
            return posted

        paid = await self.pay(
            posted.id,
            due,
            purchase_date,
            treasury_account=treasury_account,
            journal_code=journal_code,
        )
        logger.info(
            "Achat PoS %s enregistré et réglé (%.2f %s)",
            posted.reference,
            due,
            posted.currency_code,
        )
        return paid or posted


    async def cancel(self, invoice_id: int) -> SupplierInvoice | None:
        invoice = await self.get_invoice(invoice_id)
        if invoice is None:
            return None
        if invoice.status == SupplierInvoiceStatus.PAID.value:
            raise ValueError("Une facture payée ne peut pas être annulée.")
        invoice.status = SupplierInvoiceStatus.CANCELLED.value
        await self.session.commit()
        await self.session.refresh(invoice)
        return invoice



    # ------------------------------------------------------------------ #
    # Rapprochement 3 voies (BC × BR × facture)
    # ------------------------------------------------------------------ #
    async def matching(self, invoice_id: int) -> MatchingResult:
        """Calcule le rapprochement pour la facture demandée."""
        invoice = await self.get_invoice(invoice_id)
        if invoice is None:
            raise ValueError("Facture introuvable.")
        return await self._compute_matching(invoice)

    async def _compute_matching(self, invoice: SupplierInvoice) -> MatchingResult:
        """Compare facture × BC (quantités + prix) × BR (reçu)."""
        if invoice.order_id is None:
            return MatchingResult(status="no_reference")

        # `session.get` eager-charge `lines`/`receptions` (lazy="selectin") ;
        # `invoice.order` peut être non chargé sur une facture créée en mémoire.
        order = await self.session.get(PurchaseOrder, invoice.order_id)
        if order is None:
            return MatchingResult(status="no_reference")

        po_by_id = {l.id: l for l in order.lines}
        received_by_po_line: dict[int, float] = {}
        for reception in order.receptions:
            for rline in reception.lines:
                if rline.order_line_id is not None:
                    received_by_po_line[rline.order_line_id] = (
                        received_by_po_line.get(rline.order_line_id, 0)
                        + float(rline.quantity)
                    )

        details: list[MatchingLineDetail] = []
        has_qty_diff = False
        has_price_diff = False

        for iline in invoice.lines:
            po_line = po_by_id.get(iline.order_line_id) if iline.order_line_id else None
            detail = MatchingLineDetail(
                product_id=iline.product_id,
                description=iline.description,
                invoiced_qty=float(iline.quantity),
            )
            if po_line is not None:
                detail.ordered_qty = float(po_line.quantity)
                detail.received_qty = received_by_po_line.get(po_line.id, 0.0)
                detail.po_unit_price = float(po_line.unit_price)
                detail.invoice_unit_price = float(iline.unit_price)

                if abs(float(iline.quantity) - float(po_line.quantity)) > 1e-6:
                    detail.issues.append("qty_vs_ordered")
                    has_qty_diff = True
                if abs(float(iline.quantity) - detail.received_qty) > 1e-6:
                    detail.issues.append("qty_vs_received")
                    has_qty_diff = True
                if abs(float(iline.unit_price) - float(po_line.unit_price)) > 1e-6:
                    detail.issues.append("price_diff")
                    has_price_diff = True
            else:
                detail.issues.append("no_po_line")
            details.append(detail)

        status = "match_ok"
        if has_qty_diff:
            status = "qty_diff"
        elif has_price_diff:
            status = "price_diff"

        return MatchingResult(
            status=status,
            lines=details,
            ordered_total=float(order.amount_total),
            invoiced_total=float(invoice.amount_total),
        )

