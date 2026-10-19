"""
Schémas du module Achats — fournisseurs, demandes d'achat, bons de
commande, réceptions et factures fournisseur.
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------ #
# Fournisseurs
# ------------------------------------------------------------------ #
class SupplierCategoryLink(BaseModel):
    """Rattachement fournisseur -> catégorie de produits."""

    category_id: int


class SupplierBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    code: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    tax_number: str | None = None
    registration_number: str | None = None
    payment_terms_days: int | None = None
    is_active: bool = True


class SupplierCreate(SupplierBase):
    rating: float | None = Field(default=None, ge=1, le=5)
    delivery_days: int | None = None
    category_ids: list[int] = Field(default_factory=list)


class SupplierUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    tax_number: str | None = None
    registration_number: str | None = None
    payment_terms_days: int | None = None
    is_active: bool | None = None
    rating: float | None = Field(default=None, ge=1, le=5)
    delivery_days: int | None = None
    category_ids: list[int] | None = None


class SupplierRead(SupplierBase):
    id: int
    company_id: int
    role: str
    rating: float | None = None
    delivery_days: int | None = None
    category_ids: list[int] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SupplierSuggest(BaseModel):
    """Suggestion de fournisseurs pour une catégorie (saisie BC)."""

    id: int
    name: str
    rating: float | None = None
    delivery_days: int | None = None
    last_price: float | None = None  # dernier prix connu pour le produit


class PriceHistoryEntry(BaseModel):
    """Dernier prix d'achat connu pour un produit."""

    supplier_id: int | None = None
    supplier_name: str | None = None
    unit_price: float
    order_date: date | None = None
    source: str  # "po" (bon de commande) ou "catalogue" (prix produit)


# ------------------------------------------------------------------ #
# Demande d'Achat (DA)
# ------------------------------------------------------------------ #
class PurchaseRequestLineCreate(BaseModel):
    product_id: int | None = None
    description: str | None = None
    quantity: float = Field(default=1, gt=0)
    unit: str | None = None
    estimated_unit_price: float = Field(default=0, ge=0)


class PurchaseRequestLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    request_id: int
    product_id: int | None = None
    description: str | None = None
    quantity: float
    unit: str | None = None
    estimated_unit_price: float
    subtotal: float


class PurchaseRequestCreate(BaseModel):
    supplier_id: int | None = None
    priority: Literal["low", "normal", "high", "urgent"] = "normal"
    request_date: date | None = None
    needed_by: date | None = None
    notes: str | None = None
    lines: list[PurchaseRequestLineCreate] = Field(default_factory=list)


class PurchaseRequestUpdate(BaseModel):
    supplier_id: int | None = None
    priority: Literal["low", "normal", "high", "urgent"] | None = None
    needed_by: date | None = None
    notes: str | None = None
    lines: list[PurchaseRequestLineCreate] | None = None


class PurchaseRequestRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    number: str
    requester_id: int | None = None
    validator_id: int | None = None
    supplier_id: int | None = None
    status: str
    priority: str
    request_date: date
    needed_by: date | None = None
    submitted_at: datetime | None = None
    validated_at: datetime | None = None
    rejection_reason: str | None = None
    estimated_total: float
    notes: str | None = None
    lines: list[PurchaseRequestLineRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime




# ------------------------------------------------------------------ #
# Bon de Commande (BC)
# ------------------------------------------------------------------ #
class PurchaseOrderLineCreate(BaseModel):
    product_id: int | None = None
    description: str | None = None
    quantity: float = Field(default=1, gt=0)
    unit: str | None = None
    unit_price: float = Field(default=0, ge=0)
    tax_rate: float = Field(default=0, ge=0)
    discount_percent: float = Field(default=0, ge=0)


class PurchaseOrderLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    order_id: int
    product_id: int | None = None
    description: str | None = None
    quantity: float
    quantity_received: float
    unit: str | None = None
    unit_price: float
    tax_rate: float
    discount_percent: float
    subtotal: float
    tax_amount: float
    total: float
    quantity_remaining: float


class PurchaseOrderCreate(BaseModel):
    supplier_id: int
    origin_request_id: int | None = None
    order_date: date | None = None
    expected_date: date | None = None
    currency_code: str = "XOF"
    payment_terms_days: int | None = None
    tax_percent: float = Field(default=0, ge=0)  # TVA appliquée aux lignes sans tax_rate
    notes: str | None = None
    lines: list[PurchaseOrderLineCreate] = Field(default_factory=list)


class PurchaseOrderUpdate(BaseModel):
    supplier_id: int | None = None
    order_date: date | None = None
    expected_date: date | None = None
    currency_code: str | None = None
    payment_terms_days: int | None = None
    notes: str | None = None
    lines: list[PurchaseOrderLineCreate] | None = None


class PurchaseOrderRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    number: str
    supplier_id: int
    origin_request_id: int | None = None
    status: str
    order_date: date
    expected_date: date | None = None
    currency_code: str
    amount_untaxed: float
    tax_amount: float
    amount_total: float
    payment_terms_days: int | None = None
    notes: str | None = None
    confirmed_at: datetime | None = None
    cancelled_at: datetime | None = None
    lines: list[PurchaseOrderLineRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime




# ------------------------------------------------------------------ #
# Bon de Réception (BR)
# ------------------------------------------------------------------ #
class PurchaseReceptionLineCreate(BaseModel):
    order_line_id: int | None = None
    product_id: int | None = None
    description: str | None = None
    quantity: float = Field(default=1, gt=0)
    unit_cost: float | None = Field(default=None, ge=0)


class PurchaseReceptionLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reception_id: int
    order_line_id: int | None = None
    product_id: int | None = None
    description: str | None = None
    quantity: float
    unit_cost: float | None = None


class PurchaseReceptionCreate(BaseModel):
    """Création d'un BR depuis un BC — lignes pré-remplies côté client."""

    order_id: int
    warehouse_id: int
    reception_date: date | None = None
    notes: str | None = None
    lines: list[PurchaseReceptionLineCreate] = Field(default_factory=list)


class PurchaseReceptionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    number: str
    order_id: int
    warehouse_id: int
    status: str
    reception_date: date
    validated_at: datetime | None = None
    received_by: int | None = None
    notes: str | None = None
    lines: list[PurchaseReceptionLineRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


# ------------------------------------------------------------------ #
# Facture fournisseur
# ------------------------------------------------------------------ #
class SupplierInvoiceLineCreate(BaseModel):
    order_line_id: int | None = None
    product_id: int | None = None
    description: str | None = None
    quantity: float = Field(default=1, gt=0)
    unit_price: float = Field(default=0, ge=0)
    tax_rate: float = Field(default=0, ge=0)


class SupplierInvoiceLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    invoice_id: int
    order_line_id: int | None = None
    product_id: int | None = None
    description: str | None = None
    quantity: float
    unit_price: float
    tax_rate: float
    subtotal: float
    tax_amount: float


class SupplierInvoiceCreate(BaseModel):
    supplier_id: int
    supplier_invoice_number: str | None = None
    order_id: int | None = None
    reception_id: int | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    currency_code: str = "XOF"
    notes: str | None = None
    lines: list[SupplierInvoiceLineCreate] = Field(default_factory=list)


class SupplierInvoiceUpdate(BaseModel):
    supplier_invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    notes: str | None = None
    lines: list[SupplierInvoiceLineCreate] | None = None


class SupplierInvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    reference: str
    supplier_invoice_number: str | None = None
    supplier_id: int
    order_id: int | None = None
    reception_id: int | None = None
    status: str
    invoice_date: date
    due_date: date | None = None
    currency_code: str
    amount_untaxed: float
    tax_amount: float
    amount_total: float
    paid_amount: float
    amount_due: float
    matching_status: str | None = None
    matching_details: dict[str, Any] | None = None
    posted_at: datetime | None = None
    notes: str | None = None
    # Alerte régime fiscal (TEE/RME = TVA non applicable) — informatif, jamais bloquant.
    tva_regime_warning: str | None = None
    lines: list[SupplierInvoiceLineRead] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime


class SupplierInvoicePay(BaseModel):
    """Encaissement d'une facture fournisseur (décaissement réel)."""

    amount: float = Field(gt=0)
    payment_date: date | None = None
    method: Literal["cash", "bank_transfer", "check", "mobile_money"] = "cash"


class MatchingLineDetail(BaseModel):
    """Détail du rapprochement 3 voies pour une ligne."""

    product_id: int | None = None
    description: str | None = None
    ordered_qty: float = 0
    received_qty: float = 0
    invoiced_qty: float = 0
    po_unit_price: float | None = None
    invoice_unit_price: float | None = None
    issues: list[str] = Field(default_factory=list)


class MatchingResult(BaseModel):
    """Résultat du rapprochement BC / BR / facture."""

    status: Literal["match_ok", "qty_diff", "price_diff", "no_reference"]
    lines: list[MatchingLineDetail] = Field(default_factory=list)
    ordered_total: float | None = None
    invoiced_total: float | None = None

