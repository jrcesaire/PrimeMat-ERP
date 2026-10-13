"""
Modèles Facturation — Invoice / InvoiceLine / InvoiceLineCut.

Une facture est générée depuis une commande client, en préservant les
sous-lignes de coupes BAC (listes de longueurs à découper).

Formule ligne BAC ::
    Montant = Σ(quantité × longueur × prix unitaire)
"""
from __future__ import annotations

from datetime import date

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin
from app.shared.enums import InvoiceStatus


class Invoice(Base, TenantMixin):
    """Facture client (pro forma / émise / payée)."""

    reference: Mapped[str] = MappedColumn(String(30), unique=True, index=True)
    order_id: Mapped[int | None] = MappedColumn(ForeignKey("sales_orders.id"), nullable=True)
    partner_id: Mapped[int] = MappedColumn(
        ForeignKey("partners.id"), nullable=False, index=True
    )

    status: Mapped[str] = MappedColumn(
        String(20), default=InvoiceStatus.DRAFT.value, index=True
    )
    invoice_date: Mapped[date] = MappedColumn(Date, default=date.today)
    due_date: Mapped[date | None] = MappedColumn(Date)

    currency_code: Mapped[str] = MappedColumn(String(3), default="XOF")

    # Contact commercial hérité de la commande (pas de saisie sur la facture).
    salesperson_id: Mapped[int | None] = MappedColumn(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    amount_untaxed: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    tax_amount: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    amount_total: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    paid_amount: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)

    notes: Mapped[str | None] = MappedColumn(String(2000))
    payment_communication: Mapped[str | None] = MappedColumn(String(200))

    lines: Mapped[list["InvoiceLine"]] = relationship(
        "InvoiceLine", back_populates="invoice",
        cascade="all, delete-orphan", lazy="selectin",
    )

    partner: Mapped["Partner"] = relationship("Partner")
    company: Mapped["Company"] = relationship("Company")
    salesperson: Mapped["User | None"] = relationship(
        "User", foreign_keys=[salesperson_id], lazy="selectin"
    )

    @property
    def amount_due(self) -> float:
        return max(float(self.amount_total) - float(self.paid_amount), 0.0)

    def __repr__(self) -> str:
        return f"<Invoice {self.reference} [{self.status}]>"


class InvoiceLine(Base, TenantMixin):
    """Ligne de facture — standard ou BAC (cuts)."""

    invoice_id: Mapped[int] = MappedColumn(
        ForeignKey("invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int | None] = MappedColumn(ForeignKey("products.id"), nullable=True)
    # Variante du produit (optionnelle) — ``variant_name`` est un instantané
    # du libellé (réimpression fidèle des documents).
    variant_id: Mapped[int | None] = MappedColumn(
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    variant_name: Mapped[str | None] = MappedColumn(String(300))

    description: Mapped[str | None] = MappedColumn(String(500))
    quantity: Mapped[float] = MappedColumn(Numeric(14, 4), default=1)
    unit: Mapped[str | None] = MappedColumn(String(20))

    sell_by_length: Mapped[bool] = MappedColumn(Boolean, default=False)
    unit_price: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    discount_percent: Mapped[float] = MappedColumn(Numeric(6, 2), default=0)

    total_length: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    subtotal: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    position: Mapped[int] = MappedColumn(Integer, default=0)

    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="lines")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
    variant: Mapped["ProductVariant | None"] = relationship(
        "ProductVariant", lazy="selectin"
    )
    cuts: Mapped[list["InvoiceLineCut"]] = relationship(
        "InvoiceLineCut", back_populates="line",
        cascade="all, delete-orphan", lazy="selectin",
    )


class InvoiceLineCut(Base):
    """Sous-ligne de coupe BAC d'une facture (quantité × longueur)."""

    __tablename__ = "invoice_line_cuts"

    id: Mapped[int] = MappedColumn(Integer, primary_key=True, autoincrement=True)
    line_id: Mapped[int] = MappedColumn(
        ForeignKey("invoice_lines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity: Mapped[float] = MappedColumn(Numeric(14, 4), default=1)
    length: Mapped[float] = MappedColumn(Numeric(12, 4), nullable=False)
    unit_price: Mapped[float | None] = MappedColumn(Numeric(14, 4))

    line: Mapped["InvoiceLine"] = relationship("InvoiceLine", back_populates="cuts")