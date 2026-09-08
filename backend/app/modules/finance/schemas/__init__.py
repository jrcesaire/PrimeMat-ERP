"""Schémas Finance (dépenses)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class ExpenseCreate(BaseModel):
    label: str
    category: str = "general"
    amount: float
    expense_date: date | None = None
    payment_method: str = "cash"
    supplier_id: int | None = None
    notes: str | None = None


class ExpenseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    label: str
    category: str
    amount: float
    expense_date: date | None
    payment_method: str
    supplier_id: int | None
    notes: str | None
