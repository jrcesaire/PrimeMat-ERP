"""Schémas Comptabilité (plan comptable, journaux, écritures)."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------ #
# Lettrage tiers (InvoiceAllocation)
# ------------------------------------------------------------------ #
class InvoiceAllocationCreate(BaseModel):
    invoice_id: int = Field(gt=0)
    payment_id: int = Field(gt=0)
    allocated_amount: float = Field(gt=0)
    allocation_date: date
    notes: str | None = Field(default=None, max_length=500)


class InvoiceAllocationRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    invoice_id: int
    payment_id: int
    allocated_amount: float
    allocation_date: date
    notes: str | None


class InvoiceAllocationSummary(BaseModel):
    invoice_id: int
    invoice_reference: str
    amount_total: float
    allocated_amount: float
    remaining_amount: float


# ------------------------------------------------------------------ #
# Comptes
# ------------------------------------------------------------------ #
class AccountRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    class_no: str
    account_type: str
    technical_name: str
    is_group: bool
    is_active: bool
    level: int


class SeedResult(BaseModel):
    """Résultat d'un seed du plan comptable."""

    created: int
    total: int
    journals_created: int


# ------------------------------------------------------------------ #
# Journaux
# ------------------------------------------------------------------ #
class JournalRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    code: str
    name: str
    journal_type: str
    is_active: bool


# ------------------------------------------------------------------ #
# Exercices comptables
# ------------------------------------------------------------------ #
class FiscalYearCreate(BaseModel):
    name: str = Field(min_length=1, max_length=50)
    start_date: date
    end_date: date


class FiscalYearRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    start_date: date
    end_date: date
    status: str


# ------------------------------------------------------------------ #
# Écritures comptables
# ------------------------------------------------------------------ #
class JournalEntryLineCreate(BaseModel):
    account_code: str = Field(min_length=1, max_length=10)
    label: str | None = None
    debit: float = Field(default=0, ge=0)
    credit: float = Field(default=0, ge=0)
    partner_id: int | None = None


class JournalEntryCreate(BaseModel):
    entry_date: date
    journal_code: str = Field(min_length=1, max_length=10)
    description: str | None = Field(default=None, max_length=500)
    source_type: str = "manual"
    source_id: int | None = None
    lines: list[JournalEntryLineCreate] = Field(min_length=2)


class JournalEntryLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    entry_id: int
    account_code: str
    label: str | None
    debit: float
    credit: float
    partner_id: int | None
    position: int


class JournalEntryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    entry_date: date
    journal_code: str
    fiscal_year_id: int | None
    source_type: str
    source_id: int | None
    description: str | None
    total_debit: float
    total_credit: float
    status: str
    lines: list[JournalEntryLineRead] = []


__all__ = [
    "AccountRead",
    "SeedResult",
    "JournalRead",
    "FiscalYearCreate",
    "FiscalYearRead",
    "JournalEntryCreate",
    "JournalEntryLineCreate",
    "JournalEntryRead",
    "JournalEntryLineRead",
    "InvoiceAllocationCreate",
    "InvoiceAllocationRead",
    "InvoiceAllocationSummary",
]