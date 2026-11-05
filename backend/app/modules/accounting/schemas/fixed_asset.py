"""Schémas Pydantic — immobilisations et amortissements (Phase 2 PRD)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


# ------------------------------------------------------------------ #
# Immobilisations
# ------------------------------------------------------------------ #
class FixedAssetCreate(BaseModel):
    """Création d'une immobilisation amortissable."""

    code: str = Field(min_length=1, max_length=30)
    name: str = Field(min_length=1, max_length=200)
    category: str = Field(default="equipment", max_length=20)
    asset_account: str = Field(
        min_length=1, max_length=10, description="Compte d'immobilisation (ex. 245)"
    )
    depreciation_account: str = Field(
        default="",
        max_length=10,
        description="Compte d'amortissement cumulé (ex. 284). Vide = dérivé du compte d'immobilisation.",
    )
    expense_account: str = Field(
        default="681",
        max_length=10,
        description="Compte de dotation (681 exploitation, 686 financier)",
    )
    journal_code: str = Field(default="OD", max_length=10)
    acquisition_date: date
    in_service_date: Optional[date] = Field(
        default=None, description="Défaut : date d'acquisition"
    )
    acquisition_cost: float = Field(ge=0)
    residual_value: float = Field(default=0, ge=0)
    useful_life_years: int = Field(ge=1, le=100)
    method: str = Field(default="linear", pattern="^(linear|declining)$")
    periodicity: str = Field(default="annual", pattern="^(annual|monthly)$")
    notes: Optional[str] = Field(default=None, max_length=1000)


class FixedAssetUpdate(BaseModel):
    """Mise à jour partielle (le plan est recalculé si les paramètres changent)."""

    name: Optional[str] = Field(default=None, min_length=1, max_length=200)
    category: Optional[str] = Field(default=None, max_length=20)
    asset_account: Optional[str] = Field(default=None, min_length=1, max_length=10)
    depreciation_account: Optional[str] = Field(default=None, max_length=10)
    expense_account: Optional[str] = Field(default=None, max_length=10)
    journal_code: Optional[str] = Field(default=None, max_length=10)
    acquisition_date: Optional[date] = None
    in_service_date: Optional[date] = None
    acquisition_cost: Optional[float] = Field(default=None, ge=0)
    residual_value: Optional[float] = Field(default=None, ge=0)
    useful_life_years: Optional[int] = Field(default=None, ge=1, le=100)
    method: Optional[str] = Field(default=None, pattern="^(linear|declining)$")
    periodicity: Optional[str] = Field(default=None, pattern="^(annual|monthly)$")
    status: Optional[str] = Field(default=None, pattern="^(draft|active|disposed)$")
    disposal_date: Optional[date] = None
    notes: Optional[str] = Field(default=None, max_length=1000)


class DepreciationRead(BaseModel):
    """Échéance du plan d'amortissement."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    asset_id: int
    period_index: int
    period_date: date
    opening_value: float
    amount: float
    accumulated: float
    net_value: float
    #: ``planned`` | ``posted``
    status: str
    journal_entry_id: Optional[int] = None
    posted_at: Optional[datetime] = None


class FixedAssetRead(BaseModel):
    """Immobilisation avec son plan d'amortissement."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    code: str
    name: str
    category: str
    asset_account: str
    depreciation_account: str
    expense_account: str
    journal_code: str
    acquisition_date: date
    in_service_date: date
    acquisition_cost: float
    residual_value: float
    useful_life_years: int
    method: str
    periodicity: str
    status: str
    disposal_date: Optional[date] = None
    notes: Optional[str] = None
    depreciations: list[DepreciationRead] = []


class FixedAssetSummary(BaseModel):
    """Synthèse comptable d'une immobilisation (bandeau de l'écran)."""

    asset_id: int
    code: str
    name: str
    acquisition_cost: float
    residual_value: float
    depreciable_base: float
    accumulated: float
    net_value: float
    posted_count: int
    periods_count: int
    #: Dotation restant à comptabiliser.
    remaining_to_post: float
    #: Dotation de la prochaine échéance non comptabilisée.
    next_amount: Optional[float] = None
    next_period_date: Optional[date] = None


class DepreciationRunResult(BaseModel):
    """Résultat de la comptabilisation des dotations d'une immobilisation."""

    asset_id: int
    posted: int
    skipped: int
    total_amount: float
    references: list[str] = []
    message: str = ""


class DepreciationRunRequest(BaseModel):
    """Paramètres de comptabilisation des dotations échues."""

    as_of: Optional[date] = Field(
        default=None,
        description="Comptabilise les dotations échues à cette date (défaut : aujourd'hui)",
    )


__all__ = [
    "FixedAssetCreate",
    "FixedAssetUpdate",
    "DepreciationRead",
    "FixedAssetRead",
    "FixedAssetSummary",
    "DepreciationRunResult",
    "DepreciationRunRequest",
]
