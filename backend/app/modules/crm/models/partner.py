"""
Modèles Client / Fournisseur (Partner), Contacts et Adresses.

Un ``Partner`` peut être :
- un client (particulier, entreprise, professionnel)
- un fournisseur
- les deux (client ET fournisseur)

Le CRM gère les chantiers (Sites) attachés aux clients.
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, Date, Float, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin
from app.shared.enums import AddressType, EntityType, Gender


class Partner(Base, TenantMixin):
    """
    Partenaire commercial : client ou fournisseur.

    - ``role`` : client, supplier, ou les deux (both)
    - ``entity_type`` : individual / company / professional
    - ``credit_limit`` : limite de crédit
    """

    name: Mapped[str] = MappedColumn(String(200), nullable=False, index=True)
    code: Mapped[str | None] = MappedColumn(String(30), index=True)
    role: Mapped[str] = MappedColumn(String(10), default="client")

    entity_type: Mapped[str] = MappedColumn(String(20), default=EntityType.INDIVIDUAL.value)
    gender: Mapped[str] = MappedColumn(String(10), default=Gender.UNSET.value)

    phone: Mapped[str | None] = MappedColumn(String(50))
    email: Mapped[str | None] = MappedColumn(String(200))
    website: Mapped[str | None] = MappedColumn(String(200))

    # Informations fiscales
    tax_number: Mapped[str | None] = MappedColumn(String(50))
    registration_number: Mapped[str | None] = MappedColumn(String(50))

    # Conditions commerciales
    credit_limit: Mapped[float | None] = MappedColumn(Numeric(14, 4))
    payment_terms_days: Mapped[int | None] = MappedColumn(Integer)
    price_list_id: Mapped[int | None] = MappedColumn(Integer)
    default_discount: Mapped[float | None] = MappedColumn(Numeric(6, 2))

    # Statut
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    # Relations
    contacts: Mapped[list["Contact"]] = relationship(
        "Contact", back_populates="partner",
        cascade="all, delete-orphan", lazy="selectin",
    )
    addresses: Mapped[list["PartnerAddress"]] = relationship(
        "PartnerAddress", back_populates="partner",
        cascade="all, delete-orphan", lazy="selectin",
    )
    sites: Mapped[list["Site"]] = relationship(
        "Site", back_populates="partner",
        cascade="all, delete-orphan", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Partner {self.name} [{self.role}]>"


class Contact(Base, TenantMixin):
    """Contact d'un partenaire (nom, téléphone, email, fonction)."""

    partner_id: Mapped[int] = MappedColumn(
        ForeignKey("partners.id", ondelete="CASCADE"), nullable=False
    )
    first_name: Mapped[str] = MappedColumn(String(100), nullable=False)
    last_name: Mapped[str] = MappedColumn(String(100), nullable=False)
    phone: Mapped[str | None] = MappedColumn(String(50))
    email: Mapped[str | None] = MappedColumn(String(200))
    job_title: Mapped[str | None] = MappedColumn(String(100))
    is_primary: Mapped[bool] = MappedColumn(Boolean, default=False)

    partner: Mapped["Partner"] = relationship("Partner", back_populates="contacts")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self) -> str:
        return f"<Contact {self.full_name}>"


class PartnerAddress(Base, TenantMixin):
    """
    Adresse d'un partenaire.

    - ``address_type`` : billing (facturation), delivery (livraison), site (chantier)
    """

    partner_id: Mapped[int] = MappedColumn(
        ForeignKey("partners.id", ondelete="CASCADE"), nullable=False
    )
    address_type: Mapped[str] = MappedColumn(String(20), default=AddressType.BILLING.value)
    label: Mapped[str | None] = MappedColumn(String(100))

    line_1: Mapped[str | None] = MappedColumn(String(200))
    line_2: Mapped[str | None] = MappedColumn(String(200))
    city: Mapped[str | None] = MappedColumn(String(100))
    state: Mapped[str | None] = MappedColumn(String(100))
    postal_code: Mapped[str | None] = MappedColumn(String(20))
    country: Mapped[str] = MappedColumn(String(2), default="CI")
    latitude: Mapped[float | None] = MappedColumn(Float)
    longitude: Mapped[float | None] = MappedColumn(Float)
    is_primary: Mapped[bool] = MappedColumn(Boolean, default=False)

    partner: Mapped["Partner"] = relationship("Partner", back_populates="addresses")

    def __repr__(self) -> str:
        return f"<PartnerAddress {self.address_type} - {self.city}>"