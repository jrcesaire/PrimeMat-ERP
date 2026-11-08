"""
Modèles TVA déclarative — ``VATReturn`` et ``VATLine`` (Phase 2 PRD).

- ``VATReturn`` : déclaration de TVA d'une période (TVA collectée vs
  déductible, TVA à payer ou crédit reportable), avec son cycle de vie
  ``draft`` → ``submitted`` → ``paid`` ;
- ``VATLine``   : détail par compte du plan OHADA (``443x`` TVA facturée,
  ``442x``/``445x`` TVA récupérable).

Comptabilisation SYSCOHADA :

1. **Liquidation** (passage à ``submitted``) — solde les comptes de TVA et
   constate la position nette sur le compte de l'État :
   ``D 443x (TVA facturée) / C 445x (TVA récupérable)`` et contrepartie
   ``441`` (crédit = TVA à payer, débit = crédit de TVA reportable) ;
2. **Règlement** (passage à ``paid``) — ``D 441 / C 521`` (décaissement).

Les comptes sont identifiés par leur ``technical_name`` du plan OHADA
(``tax_collected`` / ``tax_deductible``), et non par un préfixe codé en dur.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
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

__all__ = ["VATReturn", "VATLine"]


class VATReturn(Base, TenantMixin):
    """Déclaration de TVA d'une période."""

    __table_args__ = (
        UniqueConstraint(
            "company_id", "reference", name="uq_vat_return_company_reference"
        ),
        CheckConstraint(
            "status IN ('draft', 'submitted', 'paid')",
            name="ck_vat_return_status_valid",
        ),
        CheckConstraint(
            "period_end >= period_start", name="ck_vat_return_period_valid"
        ),
    )

    #: Référence de la déclaration (ex. ``TVA-2026-10``).
    reference: Mapped[str] = MappedColumn(String(40), index=True)
    #: Libellé lisible (ex. « Octobre 2026 »).
    label: Mapped[str] = MappedColumn(String(60))

    period_start: Mapped[date] = MappedColumn(Date, nullable=False, index=True)
    period_end: Mapped[date] = MappedColumn(Date, nullable=False, index=True)

    #: ``draft`` | ``submitted`` | ``paid``
    status: Mapped[str] = MappedColumn(String(10), default="draft", index=True)

    #: TVA collectée sur la période (comptes ``tax_collected``).
    collected_amount: Mapped[float] = MappedColumn(Numeric(16, 2), default=0)
    #: TVA déductible sur la période (comptes ``tax_deductible``).
    deductible_amount: Mapped[float] = MappedColumn(Numeric(16, 2), default=0)
    #: TVA à payer (0 si la période dégage un crédit).
    net_due: Mapped[float] = MappedColumn(Numeric(16, 2), default=0)
    #: Crédit de TVA reportable (0 si la période est à payer).
    credit_carry: Mapped[float] = MappedColumn(Numeric(16, 2), default=0)

    #: Compte de l'État servant de contrepartie (``441`` par défaut).
    counterpart_account: Mapped[str] = MappedColumn(String(10), default="444000")
    #: Compte de trésorerie débité au règlement (``521`` par défaut).
    payment_account: Mapped[str] = MappedColumn(String(10), default="521")
    #: Journal des écritures de liquidation et de règlement.
    journal_code: Mapped[str] = MappedColumn(String(10), default="OD")

    #: Écriture de liquidation (solde des comptes de TVA).
    journal_entry_id: Mapped[int | None] = MappedColumn(
        Integer, nullable=True, index=True
    )
    #: Écriture de règlement (décaissement de la TVA due).
    payment_entry_id: Mapped[int | None] = MappedColumn(
        Integer, nullable=True, index=True
    )

    submitted_at: Mapped[datetime | None] = MappedColumn(DateTime, nullable=True)
    paid_at: Mapped[datetime | None] = MappedColumn(DateTime, nullable=True)
    notes: Mapped[str | None] = MappedColumn(String(1000))

    lines: Mapped[list["VATLine"]] = relationship(
        "VATLine",
        back_populates="vat_return",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def is_payable(self) -> bool:
        return float(self.net_due or 0) > 0

    def __repr__(self) -> str:
        return f"<VATReturn {self.reference} [{self.status}] due={self.net_due}>"


class VATLine(Base, TenantMixin):
    """Ligne de déclaration : TVA d'un compte du plan, sur la période."""

    __table_args__ = (
        UniqueConstraint(
            "vat_return_id", "account_code", name="uq_vat_line_return_account"
        ),
        CheckConstraint(
            "kind IN ('collected', 'deductible')", name="ck_vat_line_kind_valid"
        ),
    )

    vat_return_id: Mapped[int] = MappedColumn(
        ForeignKey("vat_returns.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    account_code: Mapped[str] = MappedColumn(String(10), index=True)
    account_name: Mapped[str] = MappedColumn(String(250))
    #: ``collected`` (TVA facturée) | ``deductible`` (TVA récupérable).
    kind: Mapped[str] = MappedColumn(String(12), index=True)
    #: Montant de TVA, toujours positif (le sens est porté par ``kind``).
    amount: Mapped[float] = MappedColumn(Numeric(16, 2), default=0)
    #: Nombre de lignes d'écriture contribuant au montant.
    entry_count: Mapped[int] = MappedColumn(Integer, default=0)

    vat_return: Mapped["VATReturn"] = relationship(
        "VATReturn", back_populates="lines"
    )

    def __repr__(self) -> str:
        return f"<VATLine {self.account_code} {self.kind} {self.amount}>"
