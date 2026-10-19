"""
Schémas Pydantic pour les CreditNote (avoirs / notes de crédit).
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CreditNoteCreate(BaseModel):
    """Données pour créer un avoir."""

    original_invoice_id: int | None = Field(default=None, gt=0)
    partner_id: int | None = Field(default=None, gt=0)
    type: str = Field(min_length=1, max_length=20)  # 'customer' | 'supplier'
    amount_untaxed: float = Field(default=0, ge=0)
    tax_amount: float = Field(default=0, ge=0)
    amount_total: float = Field(default=0, ge=0)
    currency_code: str = Field(default="XOF", min_length=3, max_length=3)
    credit_date: date | None = None
    reason: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)
    company_id: int | None = None


class CreditNoteUpdate(BaseModel):
    """Données pour mettre à jour un avoir (brouillon uniquement)."""

    partner_id: int | None = Field(default=None, gt=0)
    type: str | None = Field(default=None, min_length=1, max_length=20)
    amount_untaxed: float | None = Field(default=None, ge=0)
    tax_amount: float | None = Field(default=None, ge=0)
    amount_total: float | None = Field(default=None, ge=0)
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    credit_date: date | None = None
    reason: str | None = Field(default=None, max_length=1000)
    notes: str | None = Field(default=None, max_length=2000)


class CreditNoteRead(BaseModel):
    """Représentation en lecture d'un avoir."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    original_invoice_id: int | None
    partner_id: int | None
    type: str
    amount_untaxed: float
    tax_amount: float
    amount_total: float
    currency_code: str
    status: str
    credit_date: date
    reason: str | None
    notes: str | None
    journal_entry_id: int | None
    company_id: int


class CreditNoteIssue(BaseModel):
    """Demande d'émission d'un avoir (passe de draft → issued, avec comptabilisation)."""

    credit_date: date | None = None
    notes: str | None = Field(default=None, max_length=2000)


class CreditNoteApply(BaseModel):
    """Demande d'imputation d'un avoir sur une facture (passe issued → applied)."""

    invoice_id: int = Field(gt=0)
    amount_to_apply: float | None = Field(default=None, ge=0)


class CreditNoteSummary(BaseModel):
    """Résumé d'un avoir pour les listes."""

    id: int
    reference: str
    type: str
    amount_total: float
    currency_code: str
    status: str
    credit_date: date
    partner_id: int | None
    amount_due: float


__all__ = [
    "CreditNoteCreate",
    "CreditNoteUpdate",
    "CreditNoteRead",
    "CreditNoteIssue",
    "CreditNoteSummary",
]