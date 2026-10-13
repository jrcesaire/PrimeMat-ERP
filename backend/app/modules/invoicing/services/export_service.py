"""Export des factures clients.

Format « une ligne par article » (même trame que les devis/commandes) :
l'en‑tête de la facture — montant HT / TVA / total / reste à payer — est
répété sur chaque ligne, à ne pas additionner lors d'un agrégat.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.invoicing.models.invoice import Invoice

INVOICE_HEADERS = [
    "reference",
    "client",
    "date",
    "echeance",
    "statut",
    "produit",
    "variante",
    "quantite",
    "unite",
    "prix_unitaire",
    "remise",
    "sous_total",
    "montant_ht",
    "tva",
    "montant_document",
    "montant_paye",
    "devise",
    "description",
]


class InvoiceExportService:
    """Export des factures vers un tableau (en‑têtes + lignes)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def invoices(
        self, include_rows: bool = True, include_pos: bool = False
    ) -> tuple[list[str], list[list[Any]]]:
        from app.modules.sales.models.order import SalesOrder

        stmt = select(Invoice).options(selectinload(Invoice.partner)).order_by(Invoice.id.desc())
        if not include_pos:
            stmt = stmt.outerjoin(SalesOrder, SalesOrder.id == Invoice.order_id).where(
                (Invoice.order_id.is_(None)) | (SalesOrder.fulfillment_mode != "pos")
            )
        result = await self.session.execute(stmt)
        invoices = list(result.scalars().all())
        if not include_rows:
            return INVOICE_HEADERS, []
        return INVOICE_HEADERS, self._rows(invoices)

    @staticmethod
    def _rows(invoices: list[Invoice]) -> list[list[Any]]:
        rows: list[list[Any]] = []
        for invoice in invoices:
            base = [
                invoice.reference,
                invoice.partner.name if invoice.partner else None,
                invoice.invoice_date,
                invoice.due_date,
                invoice.status,
            ]
            untaxed = float(invoice.amount_untaxed or 0)
            tax = float(invoice.tax_amount or 0)
            total = float(invoice.amount_total or 0)
            paid = float(invoice.paid_amount or 0)
            currency = invoice.currency_code
            lines = sorted(invoice.lines, key=lambda line: (line.position or 0, line.id))
            if not lines:
                rows.append(base + [None] * 7 + [untaxed, tax, total, paid, currency, None])
                continue
            for line in lines:
                product = line.product
                rows.append(
                    base
                    + [
                        product.reference if product else None,
                        line.variant_name,
                        float(line.quantity or 0),
                        line.unit,
                        float(line.unit_price or 0),
                        float(line.discount_percent or 0),
                        float(line.subtotal or 0),
                        untaxed,
                        tax,
                        total,
                        paid,
                        currency,
                        line.description or (product.name if product else None),
                    ]
                )
        return rows
