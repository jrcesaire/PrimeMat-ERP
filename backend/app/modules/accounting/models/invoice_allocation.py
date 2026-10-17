"""
Modèle InvoiceAllocation — lettrage d'un paiement sur une facture.

Permet de rapprocher un paiement (encaissement ou décaissement) avec une ou
plusieurs factures, en allouant un montant partiel ou total. Le solde
restant à lettrer d'une facture = amount_total - Σ(allocations).
"""

from __future__ import annotations

from datetime import date
from sqlalchemy import Date, ForeignKey, Integer, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, MappedColumn, relationship, validates

from app.core.database import Base, TenantMixin


class InvoiceAllocation(Base, TenantMixin):
    """Lettrage : alloue un paiement à une facture (client ou fournisseur)."""

    invoice_id: Mapped[int] = MappedColumn(
        Integer,
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    payment_id: Mapped[int] = MappedColumn(
        Integer,
        ForeignKey("payments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    allocated_amount: Mapped[float] = MappedColumn(
        Numeric(14, 4), nullable=False, default=0
    )
    allocation_date: Mapped[date] = MappedColumn(Date, nullable=False)
    notes: Mapped[str | None] = MappedColumn(String(500))

    # Unicité : un couple (invoice, payment) ne peut être alloué qu'une fois
    __table_args__ = (
        UniqueConstraint("invoice_id", "payment_id", name="uq_invoice_payment_allocation"),
    )

    # Relations (chaînes pour éviter les imports circulaires inter-modules)
    invoice: Mapped["Invoice"] = relationship("Invoice", lazy="selectin")
    payment: Mapped["Payment"] = relationship("Payment", lazy="selectin")

    @validates("allocated_amount")
    def _validate_amount(self, key, value):
        if value is None or value < 0:
            raise ValueError("Le montant alloué doit être positif")
        return value

    def __repr__(self) -> str:
        return (
            f"<InvoiceAllocation invoice={self.invoice_id} "
            f"payment={self.payment_id} amount={self.allocated_amount}>"
        )


__all__ = ["InvoiceAllocation"]
