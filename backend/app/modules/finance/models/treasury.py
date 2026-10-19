"""
Modeles Tresorerie — comptes, releves bancaires et rapprochement.

Phase 2 du PRD (integration Tresorerie + rapprochement bancaire) :

- ``TreasuryAccount`` — compte de tresorerie (banque, caisse, mobile money)
  rattache a un compte du plan comptable (511, 512, 531...).
- ``BankStatement`` — releve bancaire (solde d'ouverture / cloture).
- ``BankStatementLine`` — ligne du releve a rapprocher avec une ecriture
  comptable (ligne du journal sur le compte de tresorerie).

Convention de montant signe :
- releve : positif = encaissement, negatif = decaissement ;
- ecriture : ``debit - credit`` (meme signe que le releve).
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin


class TreasuryAccount(Base, TenantMixin):
    """Compte de tresorerie (banque / caisse / mobile money)."""

    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_treasury_account_company_code"),
    )

    #: Code interne court (ex. ``BQ1``, ``CAI1``, ``OM1``).
    code: Mapped[str] = MappedColumn(String(20), index=True)
    name: Mapped[str] = MappedColumn(String(120))
    #: Compte du plan comptable OHADA ratache (ex. ``511`` Banque, ``531`` Caisse).
    account_code: Mapped[str] = MappedColumn(String(10), index=True)
    bank_name: Mapped[str | None] = MappedColumn(String(120))
    account_number: Mapped[str | None] = MappedColumn(String(64))
    currency: Mapped[str] = MappedColumn(String(3), default="XOF")
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    statements: Mapped[list["BankStatement"]] = relationship(
        "BankStatement",
        back_populates="account",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<TreasuryAccount {self.code} ({self.account_code})>"


class BankStatement(Base, TenantMixin):
    """Releve bancaire / etat de caisse."""

    account_id: Mapped[int] = MappedColumn(
        ForeignKey("treasury_accounts.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    label: Mapped[str] = MappedColumn(String(120))
    statement_date: Mapped[date] = MappedColumn(Date, nullable=False)
    opening_balance: Mapped[float] = MappedColumn(Numeric(14, 2), default=0)
    closing_balance: Mapped[float] = MappedColumn(Numeric(14, 2), default=0)
    #: ``open`` | ``closed`` — un releve cloture n'accepte plus de modification.
    status: Mapped[str] = MappedColumn(String(10), default="open", index=True)

    account: Mapped["TreasuryAccount"] = relationship(
        "TreasuryAccount", back_populates="statements"
    )
    lines: Mapped[list["BankStatementLine"]] = relationship(
        "BankStatementLine",
        back_populates="statement",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="BankStatementLine.line_date",
    )

    def __repr__(self) -> str:
        return f"<BankStatement {self.label} ({self.status})>"


class BankStatementLine(Base, TenantMixin):
    """Ligne de releve — montant signe, rapprochable avec une ecriture."""

    statement_id: Mapped[int] = MappedColumn(
        ForeignKey("bank_statements.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_date: Mapped[date] = MappedColumn(Date, nullable=False)
    label: Mapped[str] = MappedColumn(String(255))
    #: Positif = encaissement, negatif = decaissement.
    amount: Mapped[float] = MappedColumn(Numeric(14, 2), nullable=False)
    #: Ligne du journal rapprochee (NULL = non rapprochee).
    entry_line_id: Mapped[int | None] = MappedColumn(
        ForeignKey("journal_entry_lines.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    reconciled_at: Mapped[datetime | None] = MappedColumn(DateTime)
    reconciled_by: Mapped[int | None] = MappedColumn(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )

    statement: Mapped["BankStatement"] = relationship(
        "BankStatement", back_populates="lines"
    )

    def __repr__(self) -> str:
        return f"<BankStatementLine {self.line_date} {self.amount} {self.label[:20]!r}>"


__all__ = ["TreasuryAccount", "BankStatement", "BankStatementLine"]
