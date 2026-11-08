"""
Modèle Employé (Employee) — socle « personnel » du module Paie.

PrimeMAT n'embarquait pas de module RH : ce modèle fournit l'identité du
salarié, indépendante de tout moteur de paie. Il est volontairement décorrélé
du ``Partner`` (CRM) : un employé peut, en outre, être client/fournisseur, au
quel cas ``partner_id`` fait le lien.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin
from app.shared.enums import EmployeeStatus, Gender, MaritalStatus


class Employee(Base, TenantMixin):
    """Salarié d'une entreprise (fiche d'identité, hors paie)."""

    reference: Mapped[str] = MappedColumn(String(30), index=True)  # matricule
    last_name: Mapped[str] = MappedColumn(String(100), nullable=False)
    first_name: Mapped[str] = MappedColumn(String(100), nullable=False)

    gender: Mapped[str] = MappedColumn(String(10), default=Gender.UNSET.value)
    birth_date: Mapped[date | None] = MappedColumn(Date)
    marital_status: Mapped[str] = MappedColumn(
        String(20), default=MaritalStatus.SINGLE.value
    )
    #: Nombre de personnes à charge (parts fiscales).
    dependents: Mapped[int] = MappedColumn(Integer, default=0)
    #: Nombre de parts fiscales (barème ITS/IGR) — sert à la RICF.
    #:   célibataire/divorcé/veuf = 1 part ; marié/veuf (chef de famille) = 2 ;
    #:   + 0,5 par enfant à charge (plafond 5 parts).
    tax_parts: Mapped[float] = MappedColumn(Numeric(3, 1), default=1)

    job_title: Mapped[str | None] = MappedColumn(String(120))
    department: Mapped[str | None] = MappedColumn(String(120))

    hire_date: Mapped[date | None] = MappedColumn(Date)
    end_date: Mapped[date | None] = MappedColumn(Date)

    # Coordonnées
    phone: Mapped[str | None] = MappedColumn(String(50))
    email: Mapped[str | None] = MappedColumn(String(200))
    address: Mapped[str | None] = MappedColumn(String(300))

    # Identifiants légaux (Côte d'Ivoire)
    cnps_number: Mapped[str | None] = MappedColumn(String(50))    # N° CNPS
    tax_id: Mapped[str | None] = MappedColumn(String(50))         # N° contribuable (NCC)
    id_number: Mapped[str | None] = MappedColumn(String(50))      # pièce d'identité

    # Règlement de la paie
    bank_name: Mapped[str | None] = MappedColumn(String(120))
    bank_account: Mapped[str | None] = MappedColumn(String(60))
    payment_method: Mapped[str | None] = MappedColumn(String(20))

    # Lien facultatif vers un partenaire commercial (CRM)
    partner_id: Mapped[int | None] = MappedColumn(
        ForeignKey("partners.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = MappedColumn(
        String(20), default=EmployeeStatus.ACTIVE.value, index=True
    )
    notes: Mapped[str | None] = MappedColumn(String(500))

    contracts: Mapped[list["PayrollContract"]] = relationship(
        "PayrollContract", back_populates="employee",
        cascade="all, delete-orphan", lazy="selectin",
        order_by="PayrollContract.date_start",
    )
    partner: Mapped["Partner | None"] = relationship("Partner", lazy="selectin")

    __table_args__ = (
        UniqueConstraint(
            "company_id", "reference", name="uq_employee_company_reference"
        ),
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self) -> str:
        return f"<Employee {self.reference} {self.full_name}>"
