"""Service du module Catalogue — logique métier des produits et tôles BAC."""
from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalogue.models.product import (
    Product,
    ProductCategory,
    ProductUnit,
    UnitConversion,
)
from app.modules.catalogue.models.bac import BACSheet, BACCut
from app.modules.catalogue.schemas import (
    BACSheetCreate,
    ProductCreate,
    ProductUpdate,
)
from app.shared.enums import SaleMode

logger = logging.getLogger(__name__)


def compute_bac_line(cuts: list[dict[str, float]]) -> dict[str, float]:
    """
    Calcule les totaux d'une ligne de tôle BAC multi-longueurs.

    Formule pour chaque sous-ligne ::
        Montant = Quantité × Longueur × Prix unitaire

    Retourne ``total_length`` (Σ quantité×longueur) et ``total`` (Σ montants).
    """
    total_length = 0.0
    total_amount = 0.0
    for cut in cuts:
        qty = float(cut.get("quantity", 0))
        length = float(cut.get("length", 0))
        price = float(cut.get("unit_price", 0))
        total_length += qty * length
        total_amount += qty * length * price
    return {"total_length": total_length, "total_amount": total_amount}


class CatalogueService:
    """Service Catalogue."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------ #
    # Catégories — mode de vente
    # ------------------------------------------------------------------ #
    async def resolve_category_mode(
        self, category: ProductCategory
    ) -> SaleMode:
        """Mode de vente effectif d'une catégorie (remonte les ancêtres)."""
        return await category.resolve_sale_mode(self.session)

    async def build_category_tree(self) -> list[dict]:
        """Arborescence complète des catégories avec modes résolus."""
        result = await self.session.execute(select(ProductCategory))
        categories = list(result.scalars().all())
        by_id = {c.id: c for c in categories}

        # Résout les modes (avec cache pour éviter les remontées répétées)
        resolved: dict[int, SaleMode] = {}

        async def _resolve(cat: ProductCategory) -> SaleMode:
            if cat.id in resolved:
                return resolved[cat.id]
            own = SaleMode.UNIT
            try:
                own = SaleMode(cat.sale_mode or SaleMode.UNIT.value)
            except ValueError:
                own = SaleMode.UNIT
            if own != SaleMode.UNIT:
                resolved[cat.id] = own
                return own
            if cat.parent_id and cat.parent_id in by_id:
                mode = await _resolve(by_id[cat.parent_id])
            else:
                mode = SaleMode.UNIT
            resolved[cat.id] = mode
            return mode

        for cat in categories:
            await _resolve(cat)

        def _node(cat: ProductCategory) -> dict:
            mode = resolved.get(cat.id, SaleMode.UNIT)
            return {
                "id": cat.id,
                "name": cat.name,
                "code": cat.code,
                "description": cat.description,
                "parent_id": cat.parent_id,
                "sale_mode": cat.sale_mode,
                "is_active": cat.is_active,
                "company_id": cat.company_id,
                "resolved_sale_mode": mode.value,
                "sells_by_length": mode.sells_by_length,
                "children": [
                    _node(c) for c in categories if c.parent_id == cat.id
                ],
            }

        roots = [c for c in categories if c.parent_id is None]
        return [_node(c) for c in roots]

    # ------------------------------------------------------------------ #
    # Produits — dérivation du mode + validations
    # ------------------------------------------------------------------ #
    async def _derive_sale_attributes(
        self, category_id: int | None, data_dict: dict
    ) -> dict:
        """Détermine sell_by_length et valide les prix selon le mode.

        Retourne le dict modifié (sell_by_length écrasé).
        Lève ``ValueError`` si les prix sont incohérents avec le mode.
        """
        category = None
        if category_id is not None:
            category = await self.session.get(ProductCategory, category_id)
            if category is None:
                raise ValueError(f"Catégorie {category_id} introuvable")

        mode = SaleMode.UNIT
        if category is not None:
            mode = await self.resolve_category_mode(category)

        sells_length = mode.sells_by_length
        data_dict["sell_by_length"] = sells_length
        data_dict["sale_mode"] = mode.value

        ppm = data_dict.get("price_per_meter")
        sp = data_dict.get("selling_price")

        if mode == SaleMode.LENGTH:
            if not ppm:
                raise ValueError(
                    "Un produit de cette catégorie se vend au mètre linéaire : "
                    "'price_per_meter' est requis."
                )
            data_dict["selling_price"] = None
        elif mode == SaleMode.UNIT:
            if not sp:
                raise ValueError(
                    "Un produit de cette catégorie se vend à l'unité : "
                    "'selling_price' est requis."
                )
            data_dict["price_per_meter"] = None
            data_dict["sell_by_length"] = False
        else:  # DUAL
            if not ppm:
                raise ValueError(
                    "Un produit de cette catégorie se vend au mètre linéaire "
                    "(et à la pièce au prorata) : 'price_per_meter' est requis."
                )
        return data_dict

    async def create_product(self, data: ProductCreate) -> Product:
        payload = data.model_dump()
        category_id = payload.get("category_id")
        payload = await self._derive_sale_attributes(category_id, payload)

        # Référence auto-générée si non fournie
        if not payload.get("reference"):
            from uuid import uuid4

            payload["reference"] = f"PRD-{uuid4().hex[:8].upper()}"

        # Hérite du tenant de sa catégorie
        if category_id:
            cat = await self.session.get(ProductCategory, category_id)
            if cat is not None:
                payload["company_id"] = cat.company_id

        product = Product(**payload)
        self.session.add(product)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def get_product(self, product_id: int) -> Product | None:
        return await self.session.get(Product, product_id)

    async def list_products(
        self, skip: int = 0, limit: int = 100, category_id: int | None = None
    ) -> list[Product]:
        stmt = select(Product).offset(skip).limit(limit).order_by(Product.id)
        if category_id:
            stmt = stmt.where(Product.category_id == category_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_product(self, product_id: int, data: ProductUpdate) -> Product | None:
        product = await self.session.get(Product, product_id)
        if product is None:
            return None
        payload = data.model_dump(exclude_unset=True)

        # Détermine la catégorie effective (nouvelle ou existante)
        category_id = payload.get("category_id", product.category_id)
        # Fusionne avec les valeurs existantes pour valider les prix combinés
        merged = {
            "price_per_meter": payload.get(
                "price_per_meter", product.price_per_meter
            ),
            "selling_price": payload.get(
                "selling_price", product.selling_price
            ),
        }
        merged = await self._derive_sale_attributes(category_id, merged)
        payload["sell_by_length"] = merged["sell_by_length"]
        if "price_per_meter" in payload or merged["price_per_meter"] is None:
            payload.setdefault("price_per_meter", merged["price_per_meter"])
        if "selling_price" in payload or merged["selling_price"] is None:
            payload.setdefault("selling_price", merged["selling_price"])

        for field, value in payload.items():
            setattr(product, field, value)
        await self.session.commit()
        await self.session.refresh(product)
        return product

    async def delete_product(self, product_id: int) -> bool:
        product = await self.session.get(Product, product_id)
        if product is None:
            return False
        await self.session.delete(product)
        await self.session.commit()
        return True

    # ------------------------------------------------------------------ #
    # Tôles BAC
    # ------------------------------------------------------------------ #
    async def create_bac_sheet(self, data: BACSheetCreate) -> BACSheet:
        sheet_data = data.model_dump()
        cuts_data = sheet_data.pop("cuts", [])
        sheet = BACSheet(**sheet_data)
        for cut_data in cuts_data:
            sheet.cuts.append(BACCut(**cut_data))
        self.session.add(sheet)
        await self.session.commit()
        await self.session.refresh(sheet)
        return sheet

    async def get_bac_sheet(self, sheet_id: int) -> BACSheet | None:
        return await self.session.get(BACSheet, sheet_id)

    async def add_bac_cut(self, sheet_id: int, cut_data: dict[str, Any]) -> BACCut | None:
        sheet = await self.session.get(BACSheet, sheet_id)
        if sheet is None:
            return None
        cut = BACCut(**cut_data, sheet_id=sheet_id)
        self.session.add(cut)
        await self.session.commit()
        await self.session.refresh(cut)
        return cut

    async def delete_bac_cut(self, cut_id: int) -> bool:
        cut = await self.session.get(BACCut, cut_id)
        if cut is None:
            return False
        await self.session.delete(cut)
        await self.session.commit()
        return True