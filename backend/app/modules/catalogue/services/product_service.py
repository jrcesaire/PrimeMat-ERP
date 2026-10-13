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
from app.modules.catalogue.models.variant import (
    ProductProperty,
    ProductPropertyValue,
    ProductVariant,
    ProductVariantProperty,
)
from app.modules.catalogue.models.bac import BACSheet, BACCut
from app.modules.catalogue.schemas import (
    BACSheetCreate,
    ProductCreate,
    ProductUpdate,
    PropertyCreate,
    PropertyValueCreate,
    VariantGenerate,
    VariantUpdate,
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

        # Type de produit : stockable (quincaillerie) / on_demand (production)
        # / hybrid (les deux) / service
        stype = str(payload.get("storage_type") or "stockable").strip().lower()
        if stype not in ("stockable", "on_demand", "hybrid", "service"):
            raise ValueError(f"Type de produit invalide : {stype}")
        payload["storage_type"] = stype

        # Hérite du tenant de sa catégorie
        company_id = None
        if category_id:
            cat = await self.session.get(ProductCategory, category_id)
            if cat is not None:
                payload["company_id"] = cat.company_id
                company_id = cat.company_id
        if company_id is None:
            from app.core.tenant import get_current_company

            company_id = get_current_company() or 1

        # Code-barres unique (scan / QR)
        barcode = payload.get("barcode")
        if barcode:
            existing = (await self.session.execute(
                select(Product).where(Product.barcode == barcode)
            )).scalars().first()
            if existing is not None:
                raise ValueError(
                    f"Le code-barres « {barcode} » est déjà attribué "
                    f"au produit {existing.reference} - {existing.name}"
                )

        # Référence système séquentielle (nomenclature « product »)
        if not payload.get("reference"):
            from app.core.services.sequence_service import SequenceService

            payload["reference"] = await SequenceService(self.session).next_value(
                "product", prefix="PRD", company_id=company_id
            )

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

        # Code-barres unique (hors produit courant)
        barcode = payload.get("barcode")
        if barcode:
            existing = (await self.session.execute(
                select(Product).where(
                    Product.barcode == barcode,
                    Product.id != product_id,
                )
            )).scalars().first()
            if existing is not None:
                raise ValueError(
                    f"Le code-barres « {barcode} » est déjà attribué "
                    f"au produit {existing.reference} - {existing.name}"
                )

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

    # ------------------------------------------------------------------ #
    # Variantes de produits — propriétés, valeurs, génération
    # ------------------------------------------------------------------ #
    async def list_properties(self) -> list[ProductProperty]:
        """Propriétés de l'entreprise (avec leurs valeurs)."""
        result = await self.session.execute(
            select(ProductProperty).order_by(ProductProperty.position, ProductProperty.id)
        )
        return list(result.scalars().all())

    async def create_property(
        self, data: PropertyCreate, company_id: int | None = None
    ) -> ProductProperty:
        """Crée une propriété (nom unique par entreprise) avec valeurs initiales."""
        name = (data.name or "").strip()
        if not name:
            raise ValueError("Le nom de la propriété est obligatoire")
        existing = (await self.session.execute(
            select(ProductProperty).where(ProductProperty.name == name)
        )).scalars().first()
        if existing is not None:
            raise ValueError(f"La propriété « {name} » existe déjà")
        prop = ProductProperty(name=name, company_id=company_id)
        pos = 0
        for raw in data.values:
            value = (raw or "").strip()
            if value:
                prop.values.append(ProductPropertyValue(value=value, position=pos, company_id=company_id))
                pos += 1
        self.session.add(prop)
        await self.session.commit()
        await self.session.refresh(prop)
        return prop

    async def delete_property(self, property_id: int) -> bool:
        """Supprime une propriété (et détache les variantes qui l'utilisent)."""
        prop = await self.session.get(ProductProperty, property_id)
        if prop is None:
            return False
        links = (await self.session.execute(
            select(ProductVariantProperty).where(
                ProductVariantProperty.property_id == property_id
            )
        )).scalars().all()
        for link in links:
            await self.session.delete(link)
        await self.session.delete(prop)
        await self.session.commit()
        return True

    async def add_property_value(
        self, property_id: int, data: PropertyValueCreate
    ) -> ProductPropertyValue | None:
        """Ajoute une valeur à une propriété (idempotent)."""
        prop = await self.session.get(ProductProperty, property_id)
        if prop is None:
            return None
        value = (data.value or "").strip()
        if not value:
            raise ValueError("La valeur est obligatoire")
        for existing in prop.values:
            if existing.value.lower() == value.lower():
                return existing
        link = ProductPropertyValue(
            property_id=property_id, value=value,
            position=len(prop.values), company_id=prop.company_id,
        )
        self.session.add(link)
        await self.session.commit()
        await self.session.refresh(link)
        return link

    async def delete_property_value(self, value_id: int) -> bool:
        """Supprime une valeur (et détache les variantes qui l'utilisent)."""
        val = await self.session.get(ProductPropertyValue, value_id)
        if val is None:
            return False
        links = (await self.session.execute(
            select(ProductVariantProperty).where(
                ProductVariantProperty.value_id == value_id
            )
        )).scalars().all()
        for link in links:
            await self.session.delete(link)
        await self.session.delete(val)
        await self.session.commit()
        return True

    async def list_variants(self, product_id: int) -> list[ProductVariant]:
        """Variantes d'un produit (défaut en premier)."""
        result = await self.session.execute(
            select(ProductVariant)
            .where(ProductVariant.product_id == product_id)
            .order_by(ProductVariant.is_default.desc(), ProductVariant.id)
        )
        return list(result.scalars().all())

    async def generate_variants(
        self, product_id: int, data: VariantGenerate
    ) -> list[ProductVariant]:
        """Génère le produit cartésien des valeurs choisies (idempotent).

        Ex. Couleur {Rouge, Vert} x Finition {Mat} => 2 variantes.
        Les combinaisons déjà existantes (même suffixe) sont ignorées.
        """
        product = await self.session.get(Product, product_id)
        if product is None:
            raise ValueError("Produit introuvable")
        if not data.values:
            raise ValueError("Aucune valeur sélectionnée")

        # Propriétés dans l'ordre stable (position, id)
        prop_ids = sorted(data.values.keys())
        props = (await self.session.execute(
            select(ProductProperty).where(ProductProperty.id.in_(prop_ids))
        )).scalars().all()
        props.sort(key=lambda p: (p.position, p.id))
        prop_by_id = {p.id: p for p in props}

        existing = await self.list_variants(product_id)
        existing_suffixes = {v.name_suffix for v in existing}

        combos: list[list[ProductPropertyValue]] = [[]]
        for pid in [p.id for p in props]:
            prop = prop_by_id[pid]
            chosen_ids = data.values.get(pid) or []
            chosen = [v for v in prop.values if v.id in chosen_ids]
            if not chosen:
                raise ValueError(f"Aucune valeur valide pour « {prop.name} »")
            combos = [c + [v] for c in combos for v in chosen]

        created: list[ProductVariant] = []
        counter = len(existing)
        for combo in combos:
            suffix = " / ".join(v.value for v in combo)
            if suffix in existing_suffixes:
                continue
            counter += 1
            variant = ProductVariant(
                product_id=product_id,
                company_id=product.company_id,
                name_suffix=suffix,
                reference=f"{product.reference}-{counter}" if product.reference else None,
                selling_price=float(product.selling_price) if data.copy_prices and product.selling_price else None,
                purchase_price=float(product.purchase_price) if data.copy_prices and product.purchase_price else None,
                price_per_meter=float(product.price_per_meter) if data.copy_prices and product.price_per_meter else None,
            )
            for v in combo:
                variant.properties.append(
                    ProductVariantProperty(
                        property_id=v.property_id, value_id=v.id,
                        company_id=product.company_id,
                    )
                )
            self.session.add(variant)
            created.append(variant)
        await self.session.commit()

        # Première variante par défaut si aucune ne l'est
        variants = await self.list_variants(product_id)
        if variants and not any(v.is_default for v in variants):
            variants[0].is_default = True
            await self.session.commit()
        return created

    async def update_variant(
        self, variant_id: int, data: VariantUpdate
    ) -> ProductVariant | None:
        """Met à jour une variante (défaut exclusif)."""
        variant = await self.session.get(ProductVariant, variant_id)
        if variant is None:
            return None
        payload = data.model_dump(exclude_unset=True)
        if payload.get("is_default"):
            others = (await self.session.execute(
                select(ProductVariant).where(
                    ProductVariant.product_id == variant.product_id,
                    ProductVariant.id != variant_id,
                )
            )).scalars().all()
            for other in others:
                other.is_default = False
        for field, value in payload.items():
            setattr(variant, field, value)
        await self.session.commit()
        await self.session.refresh(variant)
        return variant

    async def delete_variant(self, variant_id: int) -> bool:
        variant = await self.session.get(ProductVariant, variant_id)
        if variant is None:
            return False
        await self.session.delete(variant)
        await self.session.commit()
        return True
