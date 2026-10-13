"""Schémas du module Catalogue (produits, catégories, unités, tôles BAC)."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ProductBase(BaseModel):
    """Champs communs d'un produit."""

    model_config = ConfigDict(from_attributes=True)

    reference: str
    barcode: str | None = None
    name: str
    description: str | None = None
    category_id: int | None = None
    brand: str | None = None
    storage_type: str = "stockable"
    purchase_unit_id: int | None = None
    sale_unit_id: int | None = None
    conversion_factor: float = 1.0
    sell_by_length: bool = False
    unit_length: float | None = None
    price_per_meter: float | None = None
    purchase_price: float | None = None
    selling_price: float | None = None
    margin_percent: float | None = None
    tax_id: int | None = None
    lead_time_days: int | None = None
    reorder_point: float | None = None
    primary_supplier_id: int | None = None
    status: str = "draft"
    attributes: dict[str, Any] = Field(default_factory=dict)


class ProductCreate(ProductBase):
    """Création de produit — référence auto-générée si absente."""

    reference: str | None = None  # type: ignore[assignment]


class ProductUpdate(BaseModel):
    """Mise à jour partielle d'un produit."""

    reference: str | None = None
    barcode: str | None = None
    name: str | None = None
    description: str | None = None
    category_id: int | None = None
    brand: str | None = None
    storage_type: str | None = None
    selling_price: float | None = None
    purchase_price: float | None = None
    is_active: bool | None = None


class ProductRead(ProductBase):
    """Produit tel que retourné par l'API."""

    id: int
    company_id: int
    sale_mode: str = "unit"      # mode effectif résolu depuis la catégorie
    is_bac_sheet: bool = False   # vrai si vendu au mètre linéaire
    variants_count: int = 0
    created_at: datetime
    updated_at: datetime


class ProductCategoryCreate(BaseModel):
    name: str
    code: str | None = None
    description: str | None = None
    parent_id: int | None = None
    sale_mode: str = "unit"  # unit | length | dual


class ProductCategoryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str | None = None
    description: str | None = None
    parent_id: int | None = None
    sale_mode: str = "unit"
    is_active: bool
    company_id: int


class CategoryTreeNode(ProductCategoryRead):
    """Nœud de l'arborescence des catégories (mode effectif résolu)."""

    resolved_sale_mode: str = "unit"
    sells_by_length: bool = False
    children: list["CategoryTreeNode"] = Field(default_factory=list)


class ProductUnitCreate(BaseModel):
    name: str
    code: str
    symbol: str | None = None


class ProductUnitRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str
    symbol: str | None = None
    is_active: bool
    company_id: int


class UnitConversionCreate(BaseModel):
    from_unit_id: int
    to_unit_id: int
    factor: float


class UnitConversionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_unit_id: int
    to_unit_id: int
    factor: float


class BACCutCreate(BaseModel):
    quantity: float = 1
    length: float
    unit_price: float | None = None


class BACCutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quantity: float
    length: float
    unit_price: float | None = None
    total_length: float
    subtotal: float


class BACSheetCreate(BaseModel):
    product_id: int
    profile: str | None = None
    material: str | None = None
    thickness: float | None = None
    useful_width: float | None = None
    total_width: float | None = None
    color: str | None = None
    finish: str | None = None
    standard_length: float | None = None
    unit_measure: str = "m"
    unit_cost: float | None = None
    unit_price: float | None = None
    supplier_id: int | None = None
    cuts: list[BACCutCreate] = Field(default_factory=list)


class BACSheetRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    profile: str | None = None
    material: str | None = None
    thickness: float | None = None
    useful_width: float | None = None
    total_width: float | None = None
    color: str | None = None
    finish: str | None = None
    standard_length: float | None = None
    unit_measure: str
    unit_cost: float | None = None
    unit_price: float | None = None
    cuts: list[BACCutRead] = Field(default_factory=list)

# ------------------------------------------------------------------ #
# Variantes de produits — propriétés, valeurs, variantes
# ------------------------------------------------------------------ #
class PropertyValueRead(BaseModel):
    """Valeur d'une propriété (ex. Rouge)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    value: str
    position: int = 0


class PropertyCreate(BaseModel):
    """Création d'une propriété (ex. Couleur) avec valeurs initiales."""

    name: str
    values: list[str] = Field(default_factory=list)


class PropertyRead(BaseModel):
    """Propriété et ses valeurs possibles."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    position: int = 0
    is_active: bool = True
    values: list[PropertyValueRead] = Field(default_factory=list)


class PropertyValueCreate(BaseModel):
    """Ajout d'une valeur sur une propriété existante."""

    value: str


class VariantPropertyRead(BaseModel):
    """(Propriété, valeur) d'une variante."""

    model_config = ConfigDict(from_attributes=True)

    property_id: int
    property_name: str
    value_id: int
    value: str


class VariantRead(BaseModel):
    """Variante d'un produit."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    reference: str | None = None
    name_suffix: str
    selling_price: float | None = None
    purchase_price: float | None = None
    price_per_meter: float | None = None
    is_default: bool = False
    is_active: bool = True
    properties: list[VariantPropertyRead] = Field(default_factory=list)


class VariantGenerate(BaseModel):
    """Génération des variantes — valeurs choisies par propriété.

    ``values`` : {property_id: [value_ids]} — le produit cartésien des
    valeurs crée les variantes (idempotent : les combinaisons existantes
    sont ignorées).
    """

    values: dict[int, list[int]] = Field(default_factory=dict)
    copy_prices: bool = True


class VariantUpdate(BaseModel):
    """Mise à jour partielle d'une variante."""

    reference: str | None = None
    selling_price: float | None = None
    purchase_price: float | None = None
    price_per_meter: float | None = None
    is_active: bool | None = None
    is_default: bool | None = None


# ------------------------------------------------------------------ #
# Variantes de produits — propriétés, valeurs, variantes
# ------------------------------------------------------------------ #
class PropertyValueRead(BaseModel):
    """Valeur d'une propriété (ex. Rouge)."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    value: str
    position: int = 0


class PropertyCreate(BaseModel):
    """Création d'une propriété (ex. Couleur) avec valeurs initiales."""

    name: str
    values: list[str] = Field(default_factory=list)


class PropertyRead(BaseModel):
    """Propriété et ses valeurs possibles."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    position: int = 0
    is_active: bool = True
    values: list[PropertyValueRead] = Field(default_factory=list)


class PropertyValueCreate(BaseModel):
    """Ajout d'une valeur sur une propriété existante."""

    value: str


class VariantPropertyRead(BaseModel):
    """(Propriété, valeur) d'une variante."""

    property_id: int
    property_name: str
    value_id: int
    value: str


class VariantRead(BaseModel):
    """Variante d'un produit."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int
    reference: str | None = None
    name_suffix: str
    selling_price: float | None = None
    purchase_price: float | None = None
    price_per_meter: float | None = None
    is_default: bool = False
    is_active: bool = True
    properties: list[VariantPropertyRead] = Field(default_factory=list)


class VariantGenerate(BaseModel):
    """Génération des variantes — valeurs choisies par propriété.

    ``values`` : {property_id: [value_ids]} — le produit cartésien des
    valeurs crée les variantes (idempotent : les combinaisons existantes
    sont ignorées).
    """

    values: dict[int, list[int]] = Field(default_factory=dict)
    copy_prices: bool = True


class VariantUpdate(BaseModel):
    """Mise à jour partielle d'une variante."""

    reference: str | None = None
    selling_price: float | None = None
    purchase_price: float | None = None
    price_per_meter: float | None = None
    is_active: bool | None = None
    is_default: bool | None = None
