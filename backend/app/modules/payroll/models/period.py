"""
Modèles Période de paie (PayrollPeriod) et Lot de bulletins (PayrollRun).

Adaptation de ``hr_payroll_period`` et ``hr.payslip.run`` : la paie mensuelle
est traitée en **lot** — un lot par période regroupe les bulletins des
contrats actifs, ce qui simplifie le calcul de masse, la validation groupée
et la comptabilisation.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin
from app.shared.enums import PayrollPeriodState, PayrollRunState


class PayrollPeriod(Base, TenantMixin):
    """Période de paie (mensuelle, quinzaine…)."""

    name: Mapped[str] = MappedColumn(String(80), nullable=False)
    date_start: Mapped[date] = MappedColumn(Date, nullable=False)
    date_end: Mapped[date] = MappedColumn(Date, nullable=False)
    payment_date: Mapped[date | None] = MappedColumn(Date)
    state: Mapped[str] = MappedColumn(
        String(20), default=PayrollPeriodState.DRAFT.value, index=True
    )
    fiscal_year_id: Mapped[int | None] = MappedColumn(
        ForeignKey("fiscal_years.id", ondelete="SET NULL"), nullable=True
    )

    runs: Mapped[list["PayrollRun"]] = relationship(
        "PayrollRun", back_populates="period",
        cascade="all, delete-orphan", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<PayrollPeriod {self.name} [{self.state}]>"


class PayrollRun(Base, TenantMixin):
    """Lot de bulletins d'une période (traitement de paie)."""

    period_id: Mapped[int] = MappedColumn(
        ForeignKey("payroll_periods.id", ondelete="CASCADE"),
        nullable=False, index=True,
    )
    reference: Mapped[str] = MappedColumn(String(40), index=True)
    state: Mapped[str] = MappedColumn(
        String(20), default=PayrollRunState.DRAFT.value, index=True
    )
    entry_id: Mapped[int | None] = MappedColumn(
        ForeignKey("journal_entries.id", ondelete="SET NULL"), nullable=True
    )

    period: Mapped["PayrollPeriod"] = relationship(
        "PayrollPeriod", back_populates="runs"
    )
    payslips: Mapped[list["Payslip"]] = relationship(
        "Payslip", back_populates="run",
        cascade="all, delete-orphan", lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("company_id", "reference", name="uq_run_company_reference"),
    )

    @property
    def total_net(self) -> float:
        return float(sum(float(p.net_wage or 0) for p in self.payslips))

    def __repr__(self) -> str:
        return f"<PayrollRun {self.reference} [{self.state}]>"
