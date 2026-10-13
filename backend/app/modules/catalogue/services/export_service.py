"""Export en masse des produits (Excel / CSV).

Miroir de ``CatalogueImportService`` : mêmes colonnes, mêmes libellés
(``oui``/``non`` pour ``vente_au_metre``, ISO pour les dates de prix…),
donc le fichier exporté se réimporte sans retouche.
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalogue.models.product import Product, ProductUnit

PRODUCT_HEADERS = [
    "reference",
    "nom",
    "categorie",
    "marque",
    "description",
    "prix_achat",
    "prix_vente",
    "prix_ml",
    "unite",
    "longueur_std",
    "vente_au_metre",
    "code_barre",
    "mode_vente",
    "type",
]


class CatalogueExportService:
    """Export des produits vers un tableau (en‑têtes + lignes)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def products(self, include_rows: bool = True) -> tuple[list[str], list[list[Any]]]:
        if not include_rows:
            return PRODUCT_HEADERS, []

        result = await self.session.execute(
            select(Product)
            .options(selectinload(Product.category))
            .order_by(Product.id)
        )
        products = list(result.scalars().all())

        units = await self.session.execute(select(ProductUnit))
        unit_names = {u.id: u.name for u in units.scalars().all()}

        return PRODUCT_HEADERS, [self._row(p, unit_names) for p in products]

    @staticmethod
    def _row(product: Product, unit_names: dict[int, str]) -> list[Any]:
        category = product.category
        return [
            product.reference,
            product.name,
            category.name if category else None,
            product.brand,
            product.description,
            float(product.purchase_price) if product.purchase_price is not None else None,
            float(product.selling_price) if product.selling_price is not None else None,
            float(product.price_per_meter) if product.price_per_meter is not None else None,
            unit_names.get(product.sale_unit_id),
            float(product.unit_length) if product.unit_length is not None else None,
            "oui" if product.sell_by_length else "non",
            product.barcode,
            product.sale_mode,
            product.storage_type,
        ]
