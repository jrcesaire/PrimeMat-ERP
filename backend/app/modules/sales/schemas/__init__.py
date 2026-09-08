"""Schémas du module Ventes (devis, commandes, lignes BAC)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class CutBase(BaseModel):
    """Sous-ligne de coupe BAC (quantité × longueur)."""

    quantity: float = 1
    length: float
    unit_price: float | None = None


class CutRead(CutBase):
    model_config = ConfigDict(from_attributes=True)
    id: int


class QuoteLineCreate(BaseModel):
    product_id: int | None = None
    description: str | None = None
    quantity: float = 1
    unit: str | None = None
    sell_by_length: bool = False
    unit_price: float = 0
    discount_percent: float = 0
    cuts: list[CutBase] = Field(default_factory=list)


class QuoteLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quote_id: int
    product_id: int | None = None
    description: str | None = None
    quantity: float
    unit: str | None = None
    sell_by_length: bool
    unit_price: float
    discount_percent: float
    total_length: float
    subtotal: float
    cuts: list[CutRead] = Field(default_factory=list)


class QuoteCreate(BaseModel):
    partner_id: int
    site_id: int | None = None
    quote_date: date | None = None
    valid_until: date | None = None
    currency_code: str = "XOF"
    notes: str | None = None
    terms: str | None = None
    # Remise globale (montant) et TVA (%)
    discount_amount: float = 0
    tax_percent: float = 0
    # Infos commerciales (stockées dans metadata_json)
    payment_term: str | None = None
    customer_reference: str | None = None
    lines: list[QuoteLineCreate] = Field(default_factory=list)


class QuoteUpdate(BaseModel):
    """Mise à jour d'un devis — brouillon uniquement (lignes remplaçables)."""

    partner_id: int | None = None
    site_id: int | None = None
    quote_date: date | None = None
    valid_until: date | None = None
    currency_code: str | None = None
    notes: str | None = None
    terms: str | None = None
    discount_amount: float | None = None
    tax_percent: float | None = None
    payment_term: str | None = None
    customer_reference: str | None = None
    status: str | None = None
    lines: list[QuoteLineCreate] | None = None


class QuoteRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    partner_id: int
    site_id: int | None = None
    status: str
    quote_date: date
    valid_until: date | None = None
    currency_code: str
    amount_untaxed: float
    discount_amount: float
    tax_amount: float
    amount_total: float
    expected_margin: float | None = None
    notes: str | None = None
    terms: str | None = None
    metadata_json: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    lines: list[QuoteLineRead] = Field(default_factory=list)


class OrderLineCreate(BaseModel):
    product_id: int | None = None
    description: str | None = None
    quantity_ordered: float = 1
    unit: str | None = None
    sell_by_length: bool = False
    unit_price: float = 0
    purchase_price: float | None = None
    discount_percent: float = 0
    cuts: list[CutBase] = Field(default_factory=list)


class OrderLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    product_id: int | None = None
    description: str | None = None
    quantity_ordered: float
    quantity_reserved: float
    quantity_available: float
    quantity_to_purchase: float
    quantity_purchased: float
    quantity_delivered: float
    sell_by_length: bool
    unit_price: float
    total_length: float
    subtotal: float
    remaining_to_supply: float
    cuts: list[CutRead] = Field(default_factory=list)


class SalesOrderCreate(BaseModel):
    partner_id: int
    site_id: int | None = None
    quote_id: int | None = None
    fulfillment_mode: str = "stock"
    delivery_date_planned: date | None = None
    currency_code: str = "XOF"
    notes: str | None = None
    lines: list[OrderLineCreate] = Field(default_factory=list)


class SalesOrderUpdate(BaseModel):
    """Mise à jour d'une commande — brouillon uniquement (lignes remplaçables)."""

    partner_id: int | None = None
    site_id: int | None = None
    delivery_date_planned: date | None = None
    currency_code: str | None = None
    notes: str | None = None
    status: str | None = None
    lines: list[OrderLineCreate] | None = None


class SalesOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    partner_id: int
    site_id: int | None = None
    quote_id: int | None = None
    fulfillment_mode: str
    status: str
    order_date: date
    currency_code: str
    amount_untaxed: float
    tax_amount: float
    shipping_amount: float
    amount_total: float
    paid_amount: float
    created_at: datetime
    lines: list[OrderLineRead] = Field(default_factory=list)


class PosSaleCreate(BaseModel):
    """Vente comptoir simple — panier → sortie stock → facture → paiement."""

    partner_id: int
    site_id: int | None = None
    currency_code: str = "XOF"
    warehouse_id: int | None = None
    method: str = "cash"       # cash | mobile_money | ...
    amount: float = 0          # montant encaissé (pour la vente comptoir)
    notes: str | None = None
    lines: list[OrderLineCreate] = Field(default_factory=list)

    def to_sales_order_create(self) -> SalesOrderCreate:
        return SalesOrderCreate(
            partner_id=self.partner_id,
            site_id=self.site_id,
            fulfillment_mode="pos",
            currency_code=self.currency_code,
            notes=self.notes,
            lines=self.lines,
        )