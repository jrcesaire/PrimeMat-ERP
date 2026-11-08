"""
Modèles Bulletin de paie (Payslip) et ses composants.

Adaptation de ``hr.payslip``, ``hr.payslip.line``, ``hr.payslip.input`` et
``hr.payslip.worked_days`` : le bulletin agrège des **lignes** produites par
le moteur à partir des règles de la structure, ainsi que des **éléments
variables** (primes, retenues) et les **jours travaillés**.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import (
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin
from app.shared.enums import PayslipState


class Payslip(Base, TenantMixin):
    """Bulletin de paie d'un salarié pour une période."""

    run_id: Mapped[int | None] = MappedColumn(
        ForeignKey("payroll_runs.id", ondelete="CASCADE"), index=True, nullable=True
    )
    period_id: Mapped[int | None] = MappedColumn(
        ForeignKey("payroll_periods.id", ondelete="SET NULL"), index=True, nullable=True
    )
    number: Mapped[str] = MappedColumn(String(40), index=True)  # séquence PAIE-...
    employee_id: Mapped[int] = MappedColumn(
        ForeignKey("employees.id", ondelete="CASCADE"), nullable=False, index=True
    )
    contract_id: Mapped[int | None] = MappedColumn(
        ForeignKey("payroll_contracts.id", ondelete="SET NULL"),
        index=True, nullable=True,
    )
    structure_id: Mapped[int | None] = MappedColumn(
        ForeignKey("payroll_structures.id", ondelete="SET NULL"), nullable=True
    )

    date_from: Mapped[date] = MappedColumn(Date, nullable=False)
    date_to: Mapped[date] = MappedColumn(Date, nullable=False)
    payment_date: Mapped[date | None] = MappedColumn(Date)

    state: Mapped[str] = MappedColumn(
        String(20), default=PayslipState.DRAFT.value, index=True
    )

    gross: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    total_deductions: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    net_wage: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    employer_cost: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)

    entry_id: Mapped[int | None] = MappedColumn(
        ForeignKey("journal_entries.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = MappedColumn(String(500))

    run: Mapped["PayrollRun | None"] = relationship(
        "PayrollRun", back_populates="payslips"
    )
    employee: Mapped["Employee"] = relationship("Employee", lazy="selectin")
    contract: Mapped["PayrollContract | None"] = relationship(
        "PayrollContract", lazy="selectin"
    )
    structure: Mapped["PayrollStructure | None"] = relationship(
        "PayrollStructure", lazy="selectin"
    )

    lines: Mapped[list["PayslipLine"]] = relationship(
        "PayslipLine", back_populates="payslip",
        cascade="all, delete-orphan", lazy="selectin",
        order_by="PayslipLine.sequence",
    )
    inputs: Mapped[list["PayslipInput"]] = relationship(
        "PayslipInput", back_populates="payslip",
        cascade="all, delete-orphan", lazy="selectin",
    )
    worked_days: Mapped[list["PayslipWorkedDay"]] = relationship(
        "PayslipWorkedDay", back_populates="payslip",
        cascade="all, delete-orphan", lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("company_id", "number", name="uq_payslip_company_number"),
    )

    def __repr__(self) -> str:
        return f"<Payslip {self.number} [{self.state}]>"


class PayslipLine(Base, TenantMixin):
    """Ligne d'un bulletin : résultat d'une règle de paie."""

    payslip_id: Mapped[int] = MappedColumn(
        ForeignKey("payslips.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    rule_id: Mapped[int | None] = MappedColumn(
        ForeignKey("payroll_rules.id", ondelete="SET NULL"), nullable=True
    )
    category_id: Mapped[int | None] = MappedColumn(
        ForeignKey("payroll_rule_categories.id", ondelete="SET NULL"), nullable=True
    )

    code: Mapped[str] = MappedColumn(String(20), index=True)
    name: Mapped[str] = MappedColumn(String(160))
    category_code: Mapped[str | None] = MappedColumn(String(20))
    sequence: Mapped[int] = MappedColumn(Integer, default=10)

    quantity: Mapped[float] = MappedColumn(Numeric(14, 4), default=1)
    rate: Mapped[float] = MappedColumn(Numeric(18, 6), default=0)
    amount: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    total: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)

    account_debit: Mapped[str | None] = MappedColumn(String(10))
    account_credit: Mapped[str | None] = MappedColumn(String(10))

    payslip: Mapped["Payslip"] = relationship("Payslip", back_populates="lines")

    def __repr__(self) -> str:
        return f"<PayslipLine {self.code} {self.total}>"


class PayslipInput(Base, TenantMixin):
    """Élément variable saisi sur un bulletin (prime, retenue ponctuelle)."""

    payslip_id: Mapped[int] = MappedColumn(
        ForeignKey("payslips.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    input_code: Mapped[str] = MappedColumn(String(20), index=True)
    name: Mapped[str] = MappedColumn(String(160))
    quantity: Mapped[float] = MappedColumn(Numeric(14, 4), default=1)
    amount: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)

    payslip: Mapped["Payslip"] = relationship("Payslip", back_populates="inputs")

    def __repr__(self) -> str:
        return f"<PayslipInput {self.input_code} {self.amount}>"


class PayslipWorkedDay(Base, TenantMixin):
    """Jours / heures travaillés pris en compte pour le bulletin."""

    # Le pluriel automatique produirait ``payslip_worked_daies`` (règle y→ies) :
    # on fixe un nom de table lisible et cohérent.
    __tablename__ = "payslip_worked_days"

    payslip_id: Mapped[int] = MappedColumn(
        ForeignKey("payslips.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    work_entry_type: Mapped[str] = MappedColumn(String(30), index=True)
    name: Mapped[str | None] = MappedColumn(String(120))
    number_of_days: Mapped[float] = MappedColumn(Numeric(6, 2), default=0)
    number_of_hours: Mapped[float] = MappedColumn(Numeric(7, 2), default=0)

    payslip: Mapped["Payslip"] = relationship("Payslip", back_populates="worked_days")

    def __repr__(self) -> str:
        return f"<PayslipWorkedDay {self.work_entry_type} {self.number_of_days}>"

