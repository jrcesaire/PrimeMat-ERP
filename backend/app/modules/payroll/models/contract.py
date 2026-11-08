"""
Modèles Contrat de paie (PayrollContract) et Avantage en nature.

Adaptation PrimeMAT de ``hr.contract`` et ``payroll_contract_advantages``
d'OCA/payroll : le contrat porte la rémunération de base et rattache le
salarié à une **structure de paie** (jeu de règles). Les avantages en nature
(logement, véhicule…) alimentent le moteur de calcul à titre d'éléments
variables.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin
from app.shared.enums import ContractState, WageType


class PayrollContract(Base, TenantMixin):
    """Contrat de travail d'un salarié — base de la paie."""

    reference: Mapped[str] = MappedColumn(String(40), index=True)
    employee_id: Mapped[int] = MappedColumn(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    structure_id: Mapped[int] = MappedColumn(
        ForeignKey("payroll_structures.id", ondelete="RESTRICT"),
        nullable=False, index=True,
    )

    date_start: Mapped[date] = MappedColumn(Date, default=date.today)
    date_end: Mapped[date | None] = MappedColumn(Date)
    job_title: Mapped[str | None] = MappedColumn(String(120))

    wage: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)  # salaire de base
    wage_type: Mapped[str] = MappedColumn(String(20), default=WageType.MONTHLY.value)
    work_rate: Mapped[float] = MappedColumn(Numeric(6, 2), default=100)  # temps (%)

    currency_code: Mapped[str] = MappedColumn(String(3), default="XOF")
    state: Mapped[str] = MappedColumn(
        String(20), default=ContractState.DRAFT.value, index=True
    )

    employee: Mapped["Employee"] = relationship("Employee", back_populates="contracts")
    structure: Mapped["PayrollStructure"] = relationship(
        "PayrollStructure", lazy="selectin"
    )
    advantages: Mapped[list["ContractAdvantage"]] = relationship(
        "ContractAdvantage", back_populates="contract",
        cascade="all, delete-orphan", lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint(
            "company_id", "reference", name="uq_contract_company_reference"
        ),
    )

    @property
    def is_active(self) -> bool:
        """Vrai si le contrat est ouvert à la date du jour."""
        today = date.today()
        if self.state != ContractState.OPEN.value:
            return False
        if self.date_start and self.date_start > today:
            return False
        if self.date_end and self.date_end < today:
            return False
        return True

    def __repr__(self) -> str:
        return f"<PayrollContract {self.reference} [{self.state}]>"


class ContractAdvantage(Base, TenantMixin):
    """Avantage en nature rattaché à un contrat (logement, véhicule…)."""

    contract_id: Mapped[int] = MappedColumn(
        ForeignKey("payroll_contracts.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    name: Mapped[str] = MappedColumn(String(120), nullable=False)
    #: Code de l'élément variable alimenté dans le bulletin (ex. « LOGEMENT »).
    rule_code: Mapped[str | None] = MappedColumn(String(20))
    amount: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    is_taxable: Mapped[bool] = MappedColumn(Boolean, default=True)

    contract: Mapped["PayrollContract"] = relationship(
        "PayrollContract", back_populates="advantages"
    )

    def __repr__(self) -> str:
        return f"<ContractAdvantage {self.name} {self.amount}>"
