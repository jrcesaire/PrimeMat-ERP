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


# ------------------------------------------------------------------ #
# Clôture d'exercice — aperçu (écran « Clôture d'exercice »)
# ------------------------------------------------------------------ #
class FiscalYearClosingLine(BaseModel):
    """Compte de charges/produits soldé par l'écriture de clôture."""

    account_code: str
    account_name: str
    class_no: str
    #: Solde de l'exercice sur ce compte (débit − crédit).
    balance: float
    #: Sens de la ligne de soldage (inverse du solde).
    debit: float
    credit: float


class FiscalYearClosingPreview(BaseModel):
    """Aperçu de la clôture : soldes à solder, résultat et exercice de report."""

    fiscal_year: FiscalYearRead
    #: Comptes de charges/produits qui seront soldés.
    lines: list[FiscalYearClosingLine] = []
    #: Résultat de l'exercice (positif = bénéfice, négatif = perte).
    result: float
    #: ``profit`` | ``loss`` | ``none``
    result_type: str
    #: Compte de résultat utilisé (121 bénéfice / 129 perte), ``None`` si nul.
    result_account: Optional[str] = None
    total_debit: float
    total_credit: float
    #: Exercice qui recevra le report à nouveau.
    next_year: Optional[FiscalYearRead] = None
    #: Vrai si l'exercice suivant sera créé par la clôture (année civile).
    next_year_will_be_created: bool = False
    #: Références des écritures déjà générées (clôture / affectation).
    closing_entry_reference: Optional[str] = None
    opening_entry_reference: Optional[str] = None
    already_closed: bool = False
