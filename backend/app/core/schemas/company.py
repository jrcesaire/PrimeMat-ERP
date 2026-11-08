"""Schémas pour les entreprises et agences."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from app.shared.enums import ChartOfAccounts


# ------------------------------------------------------------------ #
# Company
# ------------------------------------------------------------------ #
class CompanyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: str = Field(..., min_length=2, max_length=20)
    domain: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: dict[str, Any] = Field(default_factory=dict)
    currency_code: str = Field(default="XOF", min_length=3, max_length=3)
    tax_country: str | None = None
    # Identité visuelle / documents — data URL limitée (~600 Ko encodés)
    logo: str | None = Field(default=None, max_length=800_000)
    establishment: str | None = Field(default=None, max_length=120)
    slogan: str | None = Field(default=None, max_length=255)
    # Informations fiscales et légales
    ncc: str | None = Field(default=None, max_length=100)
    rccm: str | None = Field(default=None, max_length=100)
    share_capital: str | None = Field(default=None, max_length=100)
    # Renseignements d'entité (assistant de configuration fiscale)
    greffe: str | None = Field(default=None, max_length=120)
    importer_code: str | None = Field(default=None, max_length=60)
    social_security_code: str | None = Field(default=None, max_length=60)
    activity_code: str | None = Field(default=None, max_length=60)
    closing_date: str | None = Field(default=None, max_length=32)
    fiscal_year_months: int = Field(default=12, ge=1, le=24)
    chart_of_accounts: ChartOfAccounts = Field(
        default=ChartOfAccounts.SYSCOHADA,
        description="Référentiel du plan comptable (assistant de configuration).",
    )
    is_active: bool = True


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(BaseModel):
    """Mise à jour partielle : seuls les champs fournis sont modifiés."""

    name: str | None = Field(default=None, min_length=1, max_length=200)
    code: str | None = Field(default=None, min_length=2, max_length=20)
    domain: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    address: dict[str, Any] | None = None
    currency_code: str | None = Field(default=None, min_length=3, max_length=3)
    tax_country: str | None = None
    logo: str | None = Field(default=None, max_length=800_000)
    establishment: str | None = Field(default=None, max_length=120)
    slogan: str | None = Field(default=None, max_length=255)
    ncc: str | None = Field(default=None, max_length=100)
    rccm: str | None = Field(default=None, max_length=100)
    share_capital: str | None = Field(default=None, max_length=100)
    # Renseignements d'entité (assistant de configuration fiscale)
    greffe: str | None = Field(default=None, max_length=120)
    importer_code: str | None = Field(default=None, max_length=60)
    social_security_code: str | None = Field(default=None, max_length=60)
    activity_code: str | None = Field(default=None, max_length=60)
    closing_date: str | None = Field(default=None, max_length=32)
    fiscal_year_months: int | None = Field(default=None, ge=1, le=24)
    chart_of_accounts: ChartOfAccounts | None = None
    is_active: bool | None = None


class CompanyRead(CompanyBase):
    id: int
    logo: str | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------ #
# Agency
# ------------------------------------------------------------------ #
class AgencyBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    code: str | None = None
    address: dict[str, Any] = Field(default_factory=dict)
    phone: str | None = None
    email: str | None = None
    is_active: bool = True


class AgencyCreate(AgencyBase):
    pass


class AgencyRead(AgencyBase):
    id: int
    company_id: int
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
