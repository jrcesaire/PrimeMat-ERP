"""
Modèle Payment — encaissements et décaissements.

Un paiement est lié à une facture (client → reçu REC-…) ou à un
fournisseur (→ reçu de paiement). Suit ``payment_type`` (receipt/payment)
et expose un ``reference`` numérotée par séquence.
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin
from app.shared.enums import PaymentMethod, PaymentStatus


class Payment(Base, TenantMixin):
    """Paiement reçu (client) ou émis (fournisseur)."""

    reference: Mapped[str] = MappedColumn(String(30), unique=True, index=True)
    payment_type: Mapped[str] = MappedColumn(String(20), default="receipt")  # receipt | payment
    direction: Mapped[str] = MappedColumn(String(20), default="in")  # in | out

    partner_id: Mapped[int | None] = MappedColumn(ForeignKey("partners.id"), nullable=True)
    invoice_id: Mapped[int | None] = MappedColumn(ForeignKey("invoices.id"), nullable=True)

    method: Mapped[str] = MappedColumn(
        String(20), default=PaymentMethod.CASH.value
    )
    # Journal comptable explicite (CAI, BAN, ...) — NULL = journal déduit du
    # mode d'encaissement par le service de comptabilisation.
    journal_code: Mapped[str | None] = MappedColumn(String(10))
    amount: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    # Monnaie rendue au client (encaissement comptoir > total) — 0 sinon.
    change_amount: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    payment_date: Mapped[date] = MappedColumn(Date, default=date.today)
    status: Mapped[str] = MappedColumn(
        String(20), default=PaymentStatus.PAID.value
    )

    notes: Mapped[str | None] = MappedColumn(String(500))

    partner: Mapped["Partner"] = relationship("Partner")
    invoice: Mapped["Invoice"] = relationship("Invoice")
    company: Mapped["Company"] = relationship("Company")

    def __repr__(self) -> str:
        return f"<Payment {self.reference} {self.amount}>"