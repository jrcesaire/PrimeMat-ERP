"""Modèles Entreprise et Agence — isolation multi-tenant."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from enum import Enum as PyEnum

from sqlalchemy import JSON, Boolean, Column, Enum, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base
from app.shared.enums import ChartOfAccounts, TaxRegime


# Table d'association Entreprise <-> Devise autorisée
company_currencies = Table(
    "company_currencies",
    Base.metadata,
    Column("company_id", Integer, ForeignKey("companies.id", ondelete="CASCADE"), primary_key=True),
    Column("currency_code", String(3), ForeignKey("currencies.code"), primary_key=True),
)


class Company(Base):
    """
    Entreprise — entité racine de l'isolation multi-tenant.

    Une entreprise possède :
    - Un ou plusieurs agences / magasins
    - Une devise principale
    - Des paramètres propres
    - Des utilisateurs, rôles, taxes, etc.

    Company hérite de ``Base`` directement (pas de ``TenantMixin``)
    car c'est la racine hiérarchique.
    """

    id: Mapped[int] = MappedColumn(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = MappedColumn(String(200), nullable=False)
    code: Mapped[str] = MappedColumn(String(20), unique=True, nullable=False, index=True)
    domain: Mapped[str | None] = MappedColumn(String(200), default=None)
    phone: Mapped[str | None] = MappedColumn(String(50))
    email: Mapped[str | None] = MappedColumn(String(200))
    website: Mapped[str | None] = MappedColumn(String(200))
    address: Mapped[dict[str, Any]] = MappedColumn(JSON, default=dict)

    # Logo de l'entreprise : image encodée en data URL (base64)
    logo: Mapped[str | None] = MappedColumn(Text, nullable=True, default=None)

    # Établissement / agence principale (affiché à côté du nom dans le dashboard)
    establishment: Mapped[str | None] = MappedColumn(String(120), nullable=True, default=None)

    # Slogan affiché sur les documents (devis, factures, reçus...)
    slogan: Mapped[str | None] = MappedColumn(String(255), nullable=True, default=None)

    # Informations fiscales et légales
    ncc: Mapped[str | None] = MappedColumn(String(100), nullable=True, default=None)
    rccm: Mapped[str | None] = MappedColumn(String(100), nullable=True, default=None)
    share_capital: Mapped[str | None] = MappedColumn(String(100), nullable=True, default=None)

    # Renseignements d'entité — saisis à l'assistant de configuration fiscale
    # et repris sur les documents officiels (devis, factures, états).
    greffe: Mapped[str | None] = MappedColumn(String(120), nullable=True, default=None)
    importer_code: Mapped[str | None] = MappedColumn(String(60), nullable=True, default=None)
    social_security_code: Mapped[str | None] = MappedColumn(String(60), nullable=True, default=None)
    activity_code: Mapped[str | None] = MappedColumn(String(60), nullable=True, default=None)
    # Date d'arrêté des comptes — « 31/12 » ou une date complète.
    closing_date: Mapped[str | None] = MappedColumn(String(32), nullable=True, default=None)
    # Durée de l'exercice en mois (12 = année civile).
    fiscal_year_months: Mapped[int] = MappedColumn(
        Integer, nullable=False, default=12, server_default="12"
    )

    currency_code: Mapped[str] = MappedColumn(
        String(3), ForeignKey("currencies.code"), nullable=False, default="XOF"
    )
    tax_country: Mapped[str | None] = MappedColumn(String(2))

    # Régime fiscal OHADA Côte d'Ivoire — pas de basculement automatique,
    # pas de blocage : alerte uniquement en cas de dépassement de seuil CA.
    tax_regime: Mapped[TaxRegime | None] = MappedColumn(
        Enum(TaxRegime), nullable=True, default=None
    )
    suggested_tax_regime: Mapped[TaxRegime | None] = MappedColumn(
        Enum(TaxRegime), nullable=True, default=None
    )

    # Référentiel du plan comptable — commercial par défaut. Il détermine le
    # plan chargé par le seed et la codification des comptes (6 chiffres dans
    # les deux cas, mais les comptes de capitaux et la classe 7 diffèrent).
    chart_of_accounts: Mapped[ChartOfAccounts] = MappedColumn(
        Enum(ChartOfAccounts),
        nullable=False,
        default=ChartOfAccounts.SYSCOHADA,
        server_default=ChartOfAccounts.SYSCOHADA.value,
    )

    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    created_at: Mapped[datetime] = MappedColumn(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = MappedColumn(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relations
    agencies: Mapped[list["Agency"]] = relationship(
        "Agency", back_populates="company",
        cascade="all, delete-orphan", lazy="selectin",
    )
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="company",
        cascade="all, delete-orphan", lazy="selectin",
    )
    settings: Mapped[list["Setting"]] = relationship(
        "Setting", back_populates="company",
        cascade="all, delete-orphan", lazy="selectin",
    )
    taxes: Mapped[list["Tax"]] = relationship(
        "Tax", back_populates="company",
        cascade="all, delete-orphan", lazy="selectin",
    )
    sequences: Mapped[list["Sequence"]] = relationship(
        "Sequence", back_populates="company",
        cascade="all, delete-orphan", lazy="selectin",
    )
    currencies: Mapped[list["Currency"]] = relationship(
        "Currency",
        secondary="company_currencies",
        back_populates="companies",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Company {self.code} - {self.name}>"


class Agency(Base):
    """
    Agence / magasin appartenant à une entreprise.

    Exemple : entreprise 'ABC' → agences 'Cocody', 'Bingerville', 'Yopougon'.
    """

    id: Mapped[int] = MappedColumn(Integer, primary_key=True, autoincrement=True)

    company_id: Mapped[int] = MappedColumn(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = MappedColumn(String(200), nullable=False)
    code: Mapped[str] = MappedColumn(String(20), nullable=True, index=True)
    address: Mapped[dict[str, Any]] = MappedColumn(JSON, default=dict)
    phone: Mapped[str | None] = MappedColumn(String(50))
    email: Mapped[str | None] = MappedColumn(String(200))
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    created_at: Mapped[datetime] = MappedColumn(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = MappedColumn(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relations
    company: Mapped["Company"] = relationship("Company", back_populates="agencies")
    users: Mapped[list["User"]] = relationship(
        "User", back_populates="agency",
        cascade="all, delete-orphan", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Agency {self.code} - {self.name}>"
