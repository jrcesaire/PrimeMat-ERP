"""Export des bons de livraison.

Format « une ligne par article ». Le BL ne porte pas de montants : les
quantités sont livrées (``quantite``) et commandées (``quantite_commandee``),
la référence de commande étant reprise pour le rapprochement.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.delivery.models.delivery import DeliveryNote

DELIVERY_HEADERS = [
    "reference",
    "client",
    "commande",
    "date",
    "statut",
    "produit",
    "variante",
    "quantite",
    "quantite_commandee",
    "unite",
    "description",
]


class DeliveryExportService:
    """Export des bons de livraison vers un tableau (en‑têtes + lignes)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def deliveries(self, include_rows: bool = True) -> tuple[list[str], list[list[Any]]]:
        stmt = (
            select(DeliveryNote)
            .options(
                selectinload(DeliveryNote.partner),
                selectinload(DeliveryNote.order),
            )
            .order_by(DeliveryNote.id.desc())
        )
        result = await self.session.execute(stmt)
        deliveries = list(result.scalars().all())
        if not include_rows:
            return DELIVERY_HEADERS, []
        return DELIVERY_HEADERS, self._rows(deliveries)

    @staticmethod
    def _rows(deliveries: list[DeliveryNote]) -> list[list[Any]]:
        rows: list[list[Any]] = []
        for delivery in deliveries:
            base = [
                delivery.reference,
                delivery.partner.name if delivery.partner else None,
                delivery.order.reference if delivery.order else None,
                delivery.delivery_date or delivery.expected_date,
                delivery.status,
            ]
            # DeliveryLine ne porte pas de « position » : tri par ordre de création
            lines = sorted(delivery.lines, key=lambda line: line.id)
            if not lines:
                rows.append(base + [None] * 6)
                continue
            for line in lines:
                product = line.product
                rows.append(
                    base
                    + [
                        product.reference if product else None,
                        line.variant_name,
                        float(line.quantity or 0),
                        float(line.quantity_ordered or 0),
                        line.unit,
                        line.description or (product.name if product else None),
                    ]
                )
        return rows
