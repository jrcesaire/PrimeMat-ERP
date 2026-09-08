"""Schémas Paiements."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class PaymentCreate(BaseModel):
    partner_id: int
    invoice_id: int | None = None
    method: str = "cash"
    amount: float
    payment_date: date | None = None
    direction: str = "in"
    notes: str | None = None


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    payment_type: str
    direction: str
    partner_id: int | None
    invoice_id: int | None
    method: str
    amount: float
    payment_date: date
    status: str
