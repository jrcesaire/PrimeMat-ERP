"""Schémas Pydantic — déclarations de TVA (Phase 2 PRD comptable)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class VATPeriodRequest(BaseModel):
    """Période déclarée (bornes incluses)."""

    period_start: date
    period_end: date
    label: Optional[str] = Field(
        default=None, max_length=60, description="Défaut : « du JJ/MM au JJ/MM »"
    )


class VATReturnCreate(VATPeriodRequest):
    """Création d'une déclaration de TVA."""

    counterpart_account: str = Field(
        default="441",
        max_length=10,
        description="Compte de l'État servant de contrepartie (TVA due / crédit)",
    )
    payment_account: str = Field(
        default="521", max_length=10, description="Compte débité au règlement"
    )
    journal_code: str = Field(default="OD", max_length=10)
    notes: Optional[str] = Field(default=None, max_length=1000)


class VATPayRequest(BaseModel):
    """Règlement de la TVA due."""

    payment_date: Optional[date] = None
    amount: Optional[float] = Field(
        default=None, ge=0, description="Défaut : montant total de la TVA due"
    )


class VATLineRead(BaseModel):
    """TVA d'un compte du plan sur la période."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    account_code: str
    account_name: str
    #: ``collected`` (TVA facturée) | ``deductible`` (TVA récupérable)
    kind: str
    amount: float
    entry_count: int


class VATReturnRead(BaseModel):
    """Déclaration de TVA avec son détail par compte."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    reference: str
    label: str
    period_start: date
    period_end: date
    #: ``draft`` | ``submitted`` | ``paid``
    status: str
    collected_amount: float
    deductible_amount: float
    net_due: float
    credit_carry: float
    counterpart_account: str
    payment_account: str
    journal_code: str
    journal_entry_id: Optional[int] = None
    payment_entry_id: Optional[int] = None
    submitted_at: Optional[datetime] = None
    paid_at: Optional[datetime] = None
    notes: Optional[str] = None
    lines: list[VATLineRead] = []


class VATPreview(BaseModel):
    """Aperçu non enregistré : montants calculés et détail par compte."""

    period_start: date
    period_end: date
    label: str
    collected_amount: float
    deductible_amount: float
    net_due: float
    credit_carry: float
    lines: list[VATLineRead] = []


__all__ = [
    "VATPeriodRequest",
    "VATReturnCreate",
    "VATPayRequest",
    "VATLineRead",
    "VATReturnRead",
    "VATPreview",
]
