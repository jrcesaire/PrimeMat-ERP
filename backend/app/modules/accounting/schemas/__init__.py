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
# Avoirs / notes de crédit
# ------------------------------------------------------------------ #
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
    """Demande d'imputation d'un avoir sur une facture (passe issued → applied).

    Le montant imputé est par défaut le montant total de l'avoir, plafonné
    par le solde restant de la facture.
    """

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
# Régime fiscal (TEE / RME / RSI / RNI)
# ------------------------------------------------------------------ #
class TaxRegimeRead(BaseModel):
    """Régime fiscal actuel de l'entreprise + suggestion de changement."""

    company_id: int
    tax_regime: str | None
    suggested_tax_regime: str | None
    ca_threshold: int | None
    ca_exceeds_threshold: bool
    tva_blocked: bool


class TaxRegimeUpdate(BaseModel):
    """Mise à jour du régime fiscal (choix manuel, jamais automatique)."""

    tax_regime: str


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
    "CreditNoteCreate",
    "CreditNoteUpdate",
    "CreditNoteRead",
    "CreditNoteApply",
    "CreditNoteIssue",
    "CreditNoteSummary",
    "TaxRegimeRead",
    "TaxRegimeUpdate",
]