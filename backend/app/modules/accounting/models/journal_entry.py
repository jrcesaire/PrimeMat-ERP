"""
Modèles Écriture comptable (JournalEntry + JournalEntryLine).

Une écriture est équilibrée : total débit == total crédit. Chaque ligne est
rattachée à un compte du plan (OHADA) et, optionnellement, à un tiers
(client / fournisseur).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin

__all__ = ["JournalEntry", "JournalEntryLine"]


class JournalEntry(Base, TenantMixin):
    """Écriture comptable (en-tête)."""

    reference: Mapped[str] = MappedColumn(String(40), index=True)
    entry_date: Mapped[date] = MappedColumn(Date, nullable=False, index=True)
    journal_code: Mapped[str] = MappedColumn(String(10), index=True)
    fiscal_year_id: Mapped[int | None] = MappedColumn(
        ForeignKey("fiscal_years.id"), nullable=True
    )

    #: Origine de l'écriture : ``manual``, ``invoice``, ``payment``,
    #: ``expense``, ``purchase``, ``stock``, ``sale``…
    source_type: Mapped[str] = MappedColumn(String(30), default="manual")
    #: Identifiant du document source (facture, paiement, dépense…)
    source_id: Mapped[int | None] = MappedColumn(Integer)

    description: Mapped[str | None] = MappedColumn(String(500))

    total_debit: Mapped[float] = MappedColumn(Numeric(16, 2), default=0)
    total_credit: Mapped[float] = MappedColumn(Numeric(16, 2), default=0)

    #: ``draft`` | ``posted`` | ``canceled``
    status: Mapped[str] = MappedColumn(String(10), default="draft", index=True)

    lines: Mapped[list["JournalEntryLine"]] = relationship(
        "JournalEntryLine",
        back_populates="entry",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="JournalEntryLine.position",
    )

    def __repr__(self) -> str:
        return f"<JournalEntry {self.reference} [{self.status}]>"


class JournalEntryLine(Base, TenantMixin):
    """Ligne d'une écriture (débit ou crédit)."""

    entry_id: Mapped[int] = MappedColumn(
        ForeignKey("journal_entries.id", ondelete="CASCADE"), nullable=False, index=True
    )
    account_code: Mapped[str] = MappedColumn(String(10), index=True)
    label: Mapped[str | None] = MappedColumn(String(250))
    debit: Mapped[float] = MappedColumn(Numeric(16, 2), default=0)
    credit: Mapped[float] = MappedColumn(Numeric(16, 2), default=0)
    #: Tiers associé (client / fournisseur / personnel…), optionnel
    partner_id: Mapped[int | None] = MappedColumn(Integer, nullable=True)
    position: Mapped[int] = MappedColumn(Integer, default=0)

    entry: Mapped["JournalEntry"] = relationship("JournalEntry", back_populates="lines")