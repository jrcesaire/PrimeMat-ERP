"""
Modèle CreditNote (avoir / note de crédit).

Un avoir est un document comptable qui réduit le montant dû par un tiers
(client ou fournisseur), lié à une facture d'origine.

États :
- draft    : brouillon, pas encore comptabilisé
- issued   : émis / comptabilisé (écriture comptable créée)
- applied  : totalement imputé (soldé via lettrage ou paiement)

Comptabilisation OHADA :
- Avoir client   : D 709 (Ventes retournées) + 4431 (TVA à répercuter) / C 411 (Client)
- Avoir fournisseur : D 401 (Fournisseur) / C 609 (Achats retournés) + 4452 (TVA déductible)
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin

__all__ = ["CreditNote"]


class CreditNote(Base, TenantMixin):
    """Avoir / note de crédit client ou fournisseur."""

    __tablename__ = "credit_notes"

    __table_args__ = (
        CheckConstraint(
            "amount_total >= 0",
            name="ck_credit_note_amount_total_nonnegative",
        ),
        CheckConstraint(
            "type IN ('customer', 'supplier')",
            name="ck_credit_note_type_valid",
        ),
        CheckConstraint(
            "status IN ('draft', 'issued', 'applied')",
            name="ck_credit_note_status_valid",
        ),
    )

    reference: Mapped[str] = MappedColumn(String(30), unique=True, index=True)

    # Facture d'origine à laquelle cet avoir est rattaché
    original_invoice_id: Mapped[int | None] = MappedColumn(
        Integer, nullable=True, index=True
    )

    # Type d'avoir : client (on doit de l'argent au client) ou fournisseur
    type: Mapped[str] = MappedColumn(String(20), nullable=False, index=True)

    # Tiers concerné
    partner_id: Mapped[int | None] = MappedColumn(Integer, nullable=True, index=True)

    # Montants
    amount_untaxed: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    tax_amount: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    amount_total: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    currency_code: Mapped[str] = MappedColumn(String(3), default="XOF")

    # État du cycle de vie
    status: Mapped[str] = MappedColumn(
        String(20), default="draft", nullable=False, index=True
    )

    # Dates
    credit_date: Mapped[date] = MappedColumn(Date, default=date.today, index=True)

    # Motif / justification
    reason: Mapped[str | None] = MappedColumn(String(1000))
    notes: Mapped[str | None] = MappedColumn(String(2000))

    # Comptabilisation liée
    journal_entry_id: Mapped[int | None] = MappedColumn(
        Integer, nullable=True, index=True
    )

    # Relations
    company: Mapped["Company"] = relationship("Company")

    def __repr__(self) -> str:
        return f"<CreditNote {self.reference} [{self.status}] {self.amount_total}>"

    @property
    def amount_due(self) -> float:
        """Montant encore à imputer (non utilisé si applied)."""
        return max(float(self.amount_total or 0), 0.0)

    @property
    def is_customer(self) -> bool:
        return self.type == "customer"

    @property
    def is_supplier(self) -> bool:
        return self.type == "supplier"