"""Import en masse des produits (Excel / CSV).

Colonnes attendues (en-têtes normalisés, tolérants aux variantes) ::
    reference, nom, categorie, marque, description, prix_achat,
    prix_vente, prix_ml, unite, longueur_std, vente_au_metre (oui/non),
    code_barre, mode_vente, type

Comportement :
- mise à jour (upsert) si ``reference`` existe déjà → ré-import idempotent
- catégorie et unité créées automatiquement si inconnues
- les lignes en erreur sont listées sans bloquer le reste du fichier
"""
from __future__ import annotations

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalogue.models.product import (
    Product,
    ProductCategory,
    ProductUnit,
)
from app.shared.enums import DocumentStatus, ProductType, SaleMode
from app.shared.file_import import clean_str, to_bool, to_float

# Alias d'en-têtes → nom logique
_FIELD_ALIASES: dict[str, str] = {
    "reference": "reference",
    "ref": "reference",
    "code": "reference",
    "sku": "reference",
    "nom": "name",
    "name": "name",
    "produit": "name",
    "designation": "name",
    "categorie": "category",
    "category": "category",
    "famille": "category",
    "marque": "brand",
    "brand": "brand",
    "description": "description",
    "prix_achat": "purchase_price",
    "prix_d_achat": "purchase_price",
    "cout_achat": "purchase_price",
    "purchase_price": "purchase_price",
    "prix_vente": "selling_price",
    "prix_de_vente": "selling_price",
    "prix_unitaire": "selling_price",
    "selling_price": "selling_price",
    "prix_ml": "price_per_meter",
    "prix_au_metre": "price_per_meter",
    "price_per_meter": "price_per_meter",
    "prix_metre": "price_per_meter",
    "unite": "unit",
    "unit": "unit",
    "unite_de_vente": "unit",
    "longueur_std": "unit_length",
    "longueur_standard": "unit_length",
    "unit_length": "unit_length",
    "vente_au_metre": "sell_by_length",
    "sell_by_length": "sell_by_length",
    "code_barre": "barcode",
    "barcode": "barcode",
    "mode_vente": "sale_mode",
    "sale_mode": "sale_mode",
    "type": "storage_type",
    "stock_type": "storage_type",
}


def _map_row(row: dict[str, Any]) -> dict[str, Any]:
    mapped: dict[str, Any] = {"__line__": row.get("__line__")}
    for key, value in row.items():
        if key.startswith("__"):
            continue
        field = _FIELD_ALIASES.get(key)
        if field and field not in mapped:
            mapped[field] = value
    return mapped


class CatalogueImportService:
    """Import des produits depuis un fichier Excel / CSV."""

    def __init__(self, session: AsyncSession, company_id: int | None = None):
        self.session = session
        self.company_id = company_id

    # -- résolution / création de catégorie ------------------------- #
    async def _resolve_category(self, raw_name: Any) -> ProductCategory | None:
        name = clean_str(raw_name, 100)
        if not name:
            return None
        stmt = select(ProductCategory).where(ProductCategory.name.ilike(name))
        if self.company_id:
            stmt = stmt.where(ProductCategory.company_id == self.company_id)
        cat = (await self.session.execute(stmt)).scalars().first()
        if cat is None:
            cat = ProductCategory(name=name, sale_mode=SaleMode.UNIT.value, is_active=True, company_id=self.company_id)
            self.session.add(cat)
            await self.session.flush()
        return cat

    # -- résolution / création d'unité ------------------------------- #
    async def _resolve_unit(self, raw: Any) -> ProductUnit | None:
        text = clean_str(raw, 50)
        if not text:
            return None
        stmt_u = select(ProductUnit).where(
            (ProductUnit.code.ilike(text)) | (ProductUnit.name.ilike(text))
        )
        if self.company_id:
            stmt_u = stmt_u.where(ProductUnit.company_id == self.company_id)
        unit = (await self.session.execute(stmt_u)).scalars().first()
        if unit is None:
            unit = ProductUnit(
                name=text, code=text[:10].lower().replace(" ", "_"), is_active=True,
                company_id=self.company_id,
            )
            self.session.add(unit)
            await self.session.flush()
        return unit

    # -- import ------------------------------------------------------- #
    async def import_products(self, rows: list[dict[str, Any]]) -> dict[str, Any]:
        created, updated, errors = 0, 0, []

        for row in rows:
            data = _map_row(row)
            line_no = data.get("__line__")
            try:
                reference = clean_str(data.get("reference"), 50)
                name = clean_str(data.get("name"), 200)
                if not name:
                    raise ValueError("Colonne « nom » obligatoire")
                if not reference:
                    raise ValueError("Colonne « reference » obligatoire")

                category = await self._resolve_category(data.get("category"))
                unit = await self._resolve_unit(data.get("unit"))

                stmt_p = select(Product).where(Product.reference == reference)
                if self.company_id:
                    stmt_p = stmt_p.where(Product.company_id == self.company_id)
                product = (await self.session.execute(stmt_p)).scalars().first()

                if product is None:
                    product = Product(
                        reference=reference, status=DocumentStatus.DRAFT.value,
                        company_id=self.company_id,
                    )
                    self.session.add(product)
                    created += 1
                else:
                    updated += 1

                product.name = name
                product.category_id = category.id if category else product.category_id
                product.sale_unit_id = unit.id if unit else product.sale_unit_id
                product.barcode = clean_str(data.get("barcode"), 50)
                product.brand = clean_str(data.get("brand"), 100)
                product.description = clean_str(data.get("description"), 1000)
                product.purchase_price = to_float(data.get("purchase_price"))
                product.selling_price = to_float(data.get("selling_price"))
                product.price_per_meter = to_float(data.get("price_per_meter"))
                product.unit_length = to_float(data.get("unit_length"))

                # Vente au mètre : colonne explicite OU prix/ml OU mode category
                sell_by_length = to_bool(data.get("sell_by_length"))
                mode_raw = clean_str(data.get("sale_mode"), 10)
                if mode_raw:
                    sell_by_length = sell_by_length or mode_raw in ("length", "dual", "metre", "ml")
                if to_float(data.get("price_per_meter")):
                    sell_by_length = True
                product.sell_by_length = sell_by_length

                if sell_by_length:
                    product.sale_mode = SaleMode.LENGTH.value
                elif mode_raw:
                    try:
                        product.sale_mode = SaleMode(mode_raw).value
                    except ValueError:
                        pass
                elif category is not None:
                    product.sale_mode = (await category.resolve_sale_mode(self.session)).value

                if data.get("storage_type"):
                    try:
                        product.storage_type = ProductType(
                            str(data.get("storage_type")).strip().lower()
                        ).value
                    except ValueError:
                        pass

                await self.session.flush()
            except Exception as exc:  # noqa: BLE001 — ligne isolée
                await self.session.rollback()
                errors.append({"line": line_no, "error": str(exc) or exc.__class__.__name__})

        if created or updated:
            await self.session.commit()
        return {
            "created": created,
            "updated": updated,
            "errors": errors,
            "total": created + updated + len(errors),
        }
