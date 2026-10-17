"""Schémas Pydantic pour le module OHADA (parametres, exercices, taux de change)."""



from __future__ import annotations

from datetime import date
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class OHADAParameterCreate(BaseModel):
    """Création d'un paramètre OHADA."""
    country_code: str = Field(min_length=2, max_length=2, description="Code ISO 3166-1 alpha-2 du pays")
    currency_code: str = Field(min_length=3, max_length=3, description="Code devise (ex: XOF)")
    rate_to_fx: Optional[float] = Field(default=600.0, ge=0, description="Taux de change VS devise de la société")
    fiscal_year_start: Optional[date] = None
    fiscal_year_end: Optional[date] = None
    tax_rate_percentage: Optional[float] = Field(default=0.0, ge=0, le=100, description="Taux TVA par défaut")
    is_active: bool = True



class OHADAParameterUpdate(BaseModel):
    """Mise à jour d'un paramètre OHADA."""
    country_code: Optional[str] = Field(default=None, min_length=2, max_length=2)
    currency_code: Optional[str] = Field(default=None, min_length=3, max_length=3)
    rate_to_fx: Optional[float] = Field(default=None, ge=0)
    fiscal_year_start: Optional[date] = None
    fiscal_year_end: Optional[date] = None
    tax_rate_percentage: Optional[float] = Field(default=None, ge=0, le=100)
    is_active: Optional[bool] = None


class OHADAParameterRead(BaseModel):
    """Lecture d'un paramètre OHADA."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    country_code: str
    currency_code: str
    rate_to_fx: Optional[float]
    fiscal_year_start: Optional[date]
    fiscal_year_end: Optional[date]
    tax_rate_percentage: Optional[float]
    is_active: bool


class FiscalYearCreate(BaseModel):
    """Création d'un exercice comptable."""
    name: str = Field(min_length=1, max_length=50)
    start_date: date
    end_date: date


class FiscalYearUpdate(BaseModel):
    """Mise à jour d'un exercice comptable."""
    name: Optional[str] = Field(default=None, min_length=1, max_length=50)
    start_date: Optional[date] = None
    end_date: Optional[date] = None


class FiscalYearRead(BaseModel):
    """Lecture d'un exercice comptable."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    name: str
    start_date: date
    end_date: date
    status: str


class ExchangeRateCreate(BaseModel):
    """Création d'un taux de change."""
    base_currency: str = Field(min_length=3, max_length=3)
    quote_currency: str = Field(min_length=3, max_length=3)
    rate: float = Field(ge=0, description="Taux de change (1 unité de base = rate unités de quote)")


class ExchangeRateRead(BaseModel):
    """Lecture d'un taux de change."""
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    base_currency: str
    quote_currency: str
    rate: float


class OHADACheckConstraint(BaseModel):
    """Vérification de contrainte OHADA."""
    model_config = ConfigDict(from_attributes=True)

    can_open: bool
    message: str
