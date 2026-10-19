"""Schemas Pydantic — tresorerie et rapprochement bancaire."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------ #
# Comptes de tresorerie
# ------------------------------------------------------------------ #
class TreasuryAccountCreate(BaseModel):
    """Creation d'un compte de tresorerie."""
    code: str = Field(min_length=1, max_length=20)
    name: str = Field(min_length=1, max_length=120)
    account_code: str = Field(min_length=1, max_length=10, description="Compte du plan (511, 512, 531...)")
    bank_name: Optional[str] = Field(default=None, max_length=120)
    account_number: Optional[str] = Field(default=None, max_length=64)
    currency: str = Field(default="XOF", min_length=3, max_length=3)
    is_active: bool = True


class TreasuryAccountUpdate(BaseModel):
    """Mise a jour partielle d'un compte de tresorerie."""
    code: Optional[str] = Field(default=None, min_length=1, max_length=20)
    name: Optional[str] = Field(default=None, min_length=1, max_length=120)
    account_code: Optional[str] = Field(default=None, min_length=1, max_length=10)
    bank_name: Optional[str] = Field(default=None, max_length=120)
    account_number: Optional[str] = Field(default=None, max_length=64)
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    is_active: Optional[bool] = None


class TreasuryAccountRead(BaseModel):
    """Lecture d'un compte de tresorerie."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    code: str
    name: str
    account_code: str
    bank_name: Optional[str] = None
    account_number: Optional[str] = None
    currency: str
    is_active: bool


# ------------------------------------------------------------------ #
# Releves bancaires
# ------------------------------------------------------------------ #
class BankStatementCreate(BaseModel):
    """Creation d'un releve bancaire."""
    label: str = Field(min_length=1, max_length=120)
    statement_date: date
    opening_balance: float = Field(default=0, ge=0)
    closing_balance: float = Field(default=0, ge=0)


class BankStatementLineRead(BaseModel):
    """Lecture d'une ligne de releve."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    statement_id: int
    line_date: date
    label: str
    amount: float
    entry_line_id: Optional[int] = None
    reconciled_at: Optional[datetime] = None


class BankStatementRead(BaseModel):
    """Lecture d'un releve (avec lignes)."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    account_id: int
    label: str
    statement_date: date
    opening_balance: float
    closing_balance: float
    status: str
    lines: list[BankStatementLineRead] = []


class BankStatementLineCreate(BaseModel):
    """Saisie d'une ligne de releve."""
    line_date: date
    label: str = Field(min_length=1, max_length=255)
    amount: float = Field(description="Positif = encaissement, negatif = decaissement")


# ------------------------------------------------------------------ #
# Rapprochement
# ------------------------------------------------------------------ #
class ReconcilePayload(BaseModel):
    """Rapprochement manuel : relie une ligne de releve a une ecriture."""
    entry_line_id: int = Field(description="Ligne du journal sur le compte de tresorerie")


class ReconcileResult(BaseModel):
    """Resultat d'un rapprochement (manuel ou automatique)."""
    matched: int
    unmatched: int
    message: str = ""


class UnreconciledEntryLine(BaseModel):
    """Ligne d'ecriture de tresorerie non rapprochee."""
    entry_line_id: int
    entry_id: int
    reference: str
    entry_date: date
    label: Optional[str] = None
    amount: float


class ReconciliationReport(BaseModel):
    """Etat de rapprochement d'un compte de tresorerie."""
    account_id: int
    account_code: str
    #: Solde du compte comptable (ecritures publiees).
    accounting_balance: float
    #: Solde cumule des releves saisis (cloture du dernier releve + lignes en cours).
    statement_balance: float
    #: Montant deja rapproche (cumule des lignes de releve rattachees).
    reconciled_amount: float
    #: Lignes de releve non rapprochees.
    unreconciled_lines: list[BankStatementLineRead] = []
    #: Lignes d'ecriture non rapprochees sur le compte.
    unreconciled_entry_lines: list[UnreconciledEntryLine] = []


__all__ = [
    "TreasuryAccountCreate",
    "TreasuryAccountUpdate",
    "TreasuryAccountRead",
    "BankStatementCreate",
    "BankStatementRead",
    "BankStatementLineCreate",
    "BankStatementLineRead",
    "ReconcilePayload",
    "ReconcileResult",
    "ReconciliationReport",
    "UnreconciledEntryLine",
]
