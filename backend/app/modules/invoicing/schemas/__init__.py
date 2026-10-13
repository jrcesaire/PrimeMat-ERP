"""Schémas Facturation (Invoice)."""
from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict


class InvoiceCutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quantity: float
    length: float
    unit_price: float | None = None


class InvoiceLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None
    variant_id: int | None = None
    variant_name: str | None = None
    description: str | None
    quantity: float
    unit: str | None
    sell_by_length: bool
    unit_price: float
    discount_percent: float
    total_length: float
    subtotal: float
    cuts: list[InvoiceCutRead] = []


class InvoiceRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    order_id: int | None
    partner_id: int
    status: str
    invoice_date: date
    due_date: date | None
    currency_code: str
    amount_untaxed: float
    tax_amount: float
    amount_total: float
    paid_amount: float
    amount_due: float
    payment_communication: str | None
    notes: str | None
    lines: list[InvoiceLineRead] = []


class InvoiceFromOrder(BaseModel):
    """Body : créer une facture depuis une commande.

    - ``mode="full"`` : facturation totale (ou du solde restant si des
      acomptes existent déjà).
    - ``mode="down_payment_percent"`` : acompte = ``value`` % du total.
    - ``mode="down_payment_fixed"`` : acompte = ``value`` (montant fixe).
    - ``post=False`` : la facture est créée en brouillon (comportement
      Odoo) ; ``post=True`` la comptabilise immédiatement.
    """

    order_id: int
    due_days: int = 0
    mode: Literal["full", "down_payment_percent", "down_payment_fixed"] = "full"
    value: float | None = None
    post: bool = False
