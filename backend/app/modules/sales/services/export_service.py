"""Export des documents commerciaux (devis + commandes clients).

Format « **une ligne par article** » — l'en‑tête du document est répété
sur chaque ligne, ce qui convient au transfert comme à l'analyse (BI).

Les colonnes ``reference_commande``, ``client``, ``date``, ``produit``,
``quantite``, ``prix_unitaire``, ``remise``, ``description`` et ``devise``
sont **exactement** celles lues par ``SalesImportService`` : un export de
commandes se réimporte tel quel. ``statut``, ``variante`` et
``montant_document`` sont ignorés à la réimportation (colonnes inconnues).
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.sales.models.order import SalesOrder
from app.modules.sales.models.quote import Quote

DOCUMENT_HEADERS = [
    "reference",
    "client",
    "date",
    "statut",
    "produit",
    "variante",
    "quantite",
    "unite",
    "prix_unitaire",
    "remise",
    "sous_total",
    "montant_document",
    "devise",
    "description",
]


class SalesExportService:
    """Export des devis et des commandes vers un tableau (en‑têtes + lignes)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def quotes(self, include_rows: bool = True) -> tuple[list[str], list[list[Any]]]:
        result = await self.session.execute(
            select(Quote)
            .options(selectinload(Quote.partner))
            .order_by(Quote.id.desc())
        )
        quotes = list(result.scalars().all())
        if not include_rows:
            return DOCUMENT_HEADERS, []
        return DOCUMENT_HEADERS, self._rows(
            quotes, partner_name=lambda q: q.partner.name if q.partner else None,
            doc_date=lambda q: q.quote_date,
            quantity_of=lambda line: line.quantity,
        )

    async def orders(
        self, include_rows: bool = True, include_pos: bool = False
    ) -> tuple[list[str], list[list[Any]]]:
        stmt = (
            select(SalesOrder)
            .options(selectinload(SalesOrder.partner))
            .order_by(SalesOrder.id.desc())
        )
        if not include_pos:
            stmt = stmt.where(SalesOrder.fulfillment_mode != "pos")
        result = await self.session.execute(stmt)
        orders = list(result.scalars().all())
        if not include_rows:
            return DOCUMENT_HEADERS, []
        return DOCUMENT_HEADERS, self._rows(
            orders, partner_name=lambda o: o.partner.name if o.partner else None,
            doc_date=lambda o: o.order_date,
            # La ligne de commande porte « quantity_ordered » (pas « quantity »)
            quantity_of=lambda line: line.quantity_ordered,
        )

    # -- mise en forme -------------------------------------------------- #
    @classmethod
    def _rows(
        cls, documents, *, partner_name, doc_date, quantity_of
    ) -> list[list[Any]]:
        rows: list[list[Any]] = []
        for document in documents:
            base = [
                document.reference,
                partner_name(document),
                doc_date(document),
                document.status,
            ]
            amount = float(document.amount_total or 0)
            currency = document.currency_code
            lines = sorted(document.lines, key=lambda line: (line.position or 0, line.id))
            if not lines:
                # Document sans ligne : conserve la ligne d'en‑tête
                rows.append(base + [None] * 7 + [amount, currency, None])
                continue
            for line in lines:
                product = line.product
                rows.append(
                    base
                    + [
                        product.reference if product else None,
                        line.variant_name,
                        float(quantity_of(line) or 0),
                        line.unit,
                        float(line.unit_price or 0),
                        float(line.discount_percent or 0),
                        float(line.subtotal or 0),
                        amount,
                        currency,
                        line.description or (product.name if product else None),
                    ]
                )
        return rows
