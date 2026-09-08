"""Schémas du module CRM (partenaires, contacts, adresses, chantiers)."""
from __future__ import annotations

from datetime import date, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ContactBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    first_name: str
    last_name: str
    phone: str | None = None
    email: str | None = None
    job_title: str | None = None
    is_primary: bool = False


class ContactCreate(ContactBase):
    pass


class ContactRead(ContactBase):
    id: int
    partner_id: int
    full_name: str
    company_id: int


class PartnerAddressBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    address_type: str = "billing"
    label: str | None = None
    line_1: str | None = None
    line_2: str | None = None
    city: str | None = None
    state: str | None = None
    postal_code: str | None = None
    country: str = "CI"
    latitude: float | None = None
    longitude: float | None = None
    is_primary: bool = False


class PartnerAddressCreate(PartnerAddressBase):
    pass


class PartnerAddressRead(PartnerAddressBase):
    id: int
    partner_id: int
    company_id: int


class PartnerBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    code: str | None = None
    role: str = "client"
    entity_type: str = "individual"
    gender: str = "unset"
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    tax_number: str | None = None
    registration_number: str | None = None
    credit_limit: float | None = None
    payment_terms_days: int | None = None
    default_discount: float | None = None


class PartnerCreate(PartnerBase):
    contacts: list[ContactCreate] = Field(default_factory=list)
    addresses: list[PartnerAddressCreate] = Field(default_factory=list)


class PartnerUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    role: str | None = None
    entity_type: str | None = None
    phone: str | None = None
    email: str | None = None
    website: str | None = None
    credit_limit: float | None = None
    payment_terms_days: int | None = None
    is_active: bool | None = None


class PartnerRead(PartnerBase):
    id: int
    company_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    contacts: list[ContactRead] = Field(default_factory=list)
    addresses: list[PartnerAddressRead] = Field(default_factory=list)


class SiteBase(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    name: str
    code: str | None = None
    address: dict[str, Any] = Field(default_factory=dict)
    city: str | None = None
    region: str | None = None
    country: str = "CI"
    start_date: date | None = None
    end_date: date | None = None
    budget: float | None = None
    status: str = "active"
    manager_name: str | None = None
    manager_phone: str | None = None
    description: str | None = None


class SiteCreate(SiteBase):
    pass


class SiteRead(SiteBase):
    id: int
    partner_id: int
    company_id: int
    is_active: bool
    created_at: datetime