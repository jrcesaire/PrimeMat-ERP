"""
Modèles du module Achats — demandes d'achat, bons de commande,
réceptions et factures fournisseur.

Workflow (PRD Module Achats V1) :
    DA  : draft → submitted → approved/rejected → converted (→ BC)
    BC  : draft → pending → confirmed → partially_received → received/done
    BR  : draft → validated (→ mouvement de stock INBOUND)
    FA  : draft → posted (→ écriture comptable) → paid
"""
from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import JSON, Date, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, MappedColumn, mapped_column, relationship

from app.core.database import Base, TenantMixin
from app.core.models.user import User
from app.modules.crm.models.partner import Partner
from app.modules.catalogue.models.product import Product
from app.modules.stock.models.inventory import Warehouse
from app.shared.enums import (
    PurchaseOrderStatus,
    PurchaseReceptionStatus,
    PurchaseRequestStatus,
    SupplierInvoiceStatus,
)


# ------------------------------------------------------------------ #
# Demande d'Achat (DA)
# ------------------------------------------------------------------ #
class PurchaseRequest(Base, TenantMixin):
    """Demande d'achat soumise par un demandeur, validée par un acheteur."""

    number: Mapped[str] = MappedColumn(String(30), unique=True, index=True)
    requester_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    validator_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("partners.id", ondelete="SET NULL"), nullable=True, index=True
    )

    status: Mapped[str] = MappedColumn(
        String(20), default=PurchaseRequestStatus.DRAFT.value, index=True
    )
    priority: Mapped[str] = MappedColumn(String(10), default="normal")

    request_date: Mapped[date] = mapped_column(Date, default=date.today)
    needed_by: Mapped[date | None] = mapped_column(Date)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime)
    rejection_reason: Mapped[str | None] = mapped_column(Text)

    # Montant estimé (re-calculé depuis les lignes)
    estimated_total: Mapped[float] = mapped_column(Numeric(14, 4), default=0)

    notes: Mapped[str | None] = mapped_column(Text)

    lines: Mapped[list["PurchaseRequestLine"]] = relationship(
        "PurchaseRequestLine", back_populates="request",
        cascade="all, delete-orphan", lazy="selectin",
    )
    requester: Mapped["User | None"] = relationship(
        User, foreign_keys=[requester_id], lazy="selectin"
    )
    validator: Mapped["User | None"] = relationship(
        User, foreign_keys=[validator_id], lazy="selectin"
    )
    supplier: Mapped["Partner | None"] = relationship(Partner, lazy="selectin")

    def __repr__(self) -> str:
        return f"<PurchaseRequest {self.number} [{self.status}]>"


class PurchaseRequestLine(Base, TenantMixin):
    """Ligne d'une demande d'achat."""

    request_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_requests.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(500))
    quantity: Mapped[float] = mapped_column(Numeric(14, 4), default=1)
    unit: Mapped[str | None] = mapped_column(String(30))
    estimated_unit_price: Mapped[float] = mapped_column(Numeric(14, 4), default=0)

    request: Mapped["PurchaseRequest"] = relationship("PurchaseRequest", back_populates="lines")
    product: Mapped["Product | None"] = relationship(Product, lazy="selectin")

    @property
    def subtotal(self) -> float:
        return float(self.quantity) * float(self.estimated_unit_price)

    def __repr__(self) -> str:
        return f"<PurchaseRequestLine req={self.request_id} qty={self.quantity}>"


# ------------------------------------------------------------------ #
# Bon de Commande (BC)
# ------------------------------------------------------------------ #
class PurchaseOrder(Base, TenantMixin):
    """Bon de commande fournisseur."""

    number: Mapped[str] = MappedColumn(String(30), unique=True, index=True)
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("partners.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    origin_request_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchase_requests.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(30), default=PurchaseOrderStatus.DRAFT.value, index=True
    )
    order_date: Mapped[date] = mapped_column(Date, default=date.today)
    expected_date: Mapped[date | None] = mapped_column(Date)

    currency_code: Mapped[str] = mapped_column(String(3), default="XOF")

    # Totaux recalculés depuis les lignes
    amount_untaxed: Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    amount_total: Mapped[float] = mapped_column(Numeric(14, 4), default=0)

    payment_terms_days: Mapped[int | None] = mapped_column(Integer)
    notes: Mapped[str | None] = mapped_column(Text)
    confirmed_at: Mapped[datetime | None] = mapped_column(DateTime)
    cancelled_at: Mapped[datetime | None] = mapped_column(DateTime)

    lines: Mapped[list["PurchaseOrderLine"]] = relationship(
        "PurchaseOrderLine", back_populates="order",
        cascade="all, delete-orphan", lazy="selectin",
    )
    supplier: Mapped["Partner"] = relationship(Partner, lazy="selectin")
    receptions: Mapped[list["PurchaseReception"]] = relationship(
        "PurchaseReception", back_populates="order", lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<PurchaseOrder {self.number} [{self.status}]>"


class PurchaseOrderLine(Base, TenantMixin):
    """Ligne d'un bon de commande fournisseur."""

    order_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(500))
    quantity: Mapped[float] = mapped_column(Numeric(14, 4), default=1)
    quantity_received: Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    unit: Mapped[str | None] = mapped_column(String(30))
    unit_price: Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    tax_rate: Mapped[float] = mapped_column(Numeric(6, 2), default=0)  # %
    discount_percent: Mapped[float] = mapped_column(Numeric(6, 2), default=0)

    order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="lines")
    product: Mapped["Product | None"] = relationship(Product, lazy="selectin")

    @property
    def subtotal(self) -> float:
        base = float(self.quantity) * float(self.unit_price)
        if self.discount_percent:
            base *= 1 - float(self.discount_percent) / 100
        return base

    @property
    def tax_amount(self) -> float:
        return self.subtotal * float(self.tax_rate) / 100

    @property
    def total(self) -> float:
        return self.subtotal + self.tax_amount

    @property
    def quantity_remaining(self) -> float:
        return max(float(self.quantity) - float(self.quantity_received), 0.0)

    def __repr__(self) -> str:
        return f"<PurchaseOrderLine order={self.order_id} qty={self.quantity}>"


# ------------------------------------------------------------------ #
# Bon de Réception (BR)
# ------------------------------------------------------------------ #
class PurchaseReception(Base, TenantMixin):
    """Bon de réception fournisseur — alimente le stock à la validation."""

    number: Mapped[str] = MappedColumn(String(30), unique=True, index=True)
    order_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    warehouse_id: Mapped[int] = mapped_column(
        ForeignKey("warehouses.id", ondelete="RESTRICT"), nullable=False
    )
    status: Mapped[str] = mapped_column(
        String(20), default=PurchaseReceptionStatus.DRAFT.value, index=True
    )
    reception_date: Mapped[date] = mapped_column(Date, default=date.today)
    validated_at: Mapped[datetime | None] = mapped_column(DateTime)
    received_by: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    notes: Mapped[str | None] = mapped_column(Text)

    lines: Mapped[list["PurchaseReceptionLine"]] = relationship(
        "PurchaseReceptionLine", back_populates="reception",
        cascade="all, delete-orphan", lazy="selectin",
    )
    order: Mapped["PurchaseOrder"] = relationship("PurchaseOrder", back_populates="receptions")
    warehouse: Mapped["Warehouse"] = relationship(Warehouse, lazy="selectin")

    def __repr__(self) -> str:
        return f"<PurchaseReception {self.number} [{self.status}]>"


class PurchaseReceptionLine(Base, TenantMixin):
    """Ligne d'un bon de réception — référencée à la ligne de BC."""

    reception_id: Mapped[int] = mapped_column(
        ForeignKey("purchase_receptions.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchase_order_lines.id", ondelete="SET NULL"), nullable=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(500))
    quantity: Mapped[float] = mapped_column(Numeric(14, 4), default=1)
    unit_cost: Mapped[float | None] = mapped_column(Numeric(14, 4))

    reception: Mapped["PurchaseReception"] = relationship(
        "PurchaseReception", back_populates="lines"
    )
    order_line: Mapped["PurchaseOrderLine | None"] = relationship(
        "PurchaseOrderLine", lazy="selectin"
    )
    product: Mapped["Product | None"] = relationship(Product, lazy="selectin")

    def __repr__(self) -> str:
        return f"<PurchaseReceptionLine reception={self.reception_id} qty={self.quantity}>"




# ------------------------------------------------------------------ #
# Facture fournisseur
# ------------------------------------------------------------------ #
class SupplierInvoice(Base, TenantMixin):
    """Facture fournisseur — rapprochée avec BC et BR (3 voies)."""

    reference: Mapped[str] = MappedColumn(String(30), unique=True, index=True)
    supplier_invoice_number: Mapped[str | None] = MappedColumn(String(50))  # n° éditeur
    supplier_id: Mapped[int] = mapped_column(
        ForeignKey("partners.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    order_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True, index=True
    )
    reception_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchase_receptions.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(
        String(20), default=SupplierInvoiceStatus.DRAFT.value, index=True
    )
    invoice_date: Mapped[date] = mapped_column(Date, default=date.today)
    due_date: Mapped[date | None] = mapped_column(Date)
    currency_code: Mapped[str] = mapped_column(String(3), default="XOF")

    amount_untaxed: Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    tax_amount: Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    amount_total: Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    paid_amount: Mapped[float] = mapped_column(Numeric(14, 4), default=0)

    # Rapprochement 3 voies — résultat du dernier contrôle
    matching_status: Mapped[str | None] = mapped_column(String(20))
    matching_details: Mapped[dict | None] = mapped_column(JSON)

    posted_at: Mapped[datetime | None] = mapped_column(DateTime)
    notes: Mapped[str | None] = mapped_column(Text)

    lines: Mapped[list["SupplierInvoiceLine"]] = relationship(
        "SupplierInvoiceLine", back_populates="invoice",
        cascade="all, delete-orphan", lazy="selectin",
    )
    supplier: Mapped["Partner"] = relationship(Partner, lazy="selectin")
    order: Mapped["PurchaseOrder | None"] = relationship("PurchaseOrder", lazy="selectin")

    @property
    def amount_due(self) -> float:
        return max(float(self.amount_total) - float(self.paid_amount), 0.0)

    def __repr__(self) -> str:
        return f"<SupplierInvoice {self.reference} [{self.status}]>"


class SupplierInvoiceLine(Base, TenantMixin):
    """Ligne d'une facture fournisseur."""

    invoice_id: Mapped[int] = mapped_column(
        ForeignKey("supplier_invoices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    order_line_id: Mapped[int | None] = mapped_column(
        ForeignKey("purchase_order_lines.id", ondelete="SET NULL"), nullable=True
    )
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id", ondelete="SET NULL"), nullable=True
    )
    description: Mapped[str | None] = mapped_column(String(500))
    quantity: Mapped[float] = mapped_column(Numeric(14, 4), default=1)
    unit_price: Mapped[float] = mapped_column(Numeric(14, 4), default=0)
    tax_rate: Mapped[float] = mapped_column(Numeric(6, 2), default=0)

    invoice: Mapped["SupplierInvoice"] = relationship("SupplierInvoice", back_populates="lines")
    order_line: Mapped["PurchaseOrderLine | None"] = relationship(
        "PurchaseOrderLine", lazy="selectin"
    )
    product: Mapped["Product | None"] = relationship(Product, lazy="selectin")

    @property
    def subtotal(self) -> float:
        return float(self.quantity) * float(self.unit_price)

    @property
    def tax_amount(self) -> float:
        return self.subtotal * float(self.tax_rate) / 100

    def __repr__(self) -> str:
        return f"<SupplierInvoiceLine invoice={self.invoice_id} qty={self.quantity}>"


__all__ = [
    "PurchaseRequest", "PurchaseRequestLine",
    "PurchaseOrder", "PurchaseOrderLine",
    "PurchaseReception", "PurchaseReceptionLine",
    "SupplierInvoice", "SupplierInvoiceLine",
]

