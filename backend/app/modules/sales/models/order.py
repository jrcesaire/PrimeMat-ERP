"""
Modèles Commande Client (SalesOrder) — modes stock, direct et hybride.

Chaque ligne suit l'approvisionnement :
- quantité commandée / réservée / à acheter / achetée / livrée
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
from app.shared.enums import SalesOrderStatus


class SalesOrder(Base, TenantMixin):
    """
    Commande client.

    Modes de fulfillment :
    - ``FROM_STOCK`` : satisfaction depuis le stock interne
    - ``DIRECT``     : livraison directe fournisseur → client
    - ``HYBRID``     : partie stock + partie achat fournisseur
    """

    reference: Mapped[str] = MappedColumn(String(30), unique=True, index=True)
    partner_id: Mapped[int] = MappedColumn(
        ForeignKey("partners.id"), nullable=False, index=True
    )
    site_id: Mapped[int | None] = MappedColumn(ForeignKey("sites.id"), nullable=True)
    quote_id: Mapped[int | None] = MappedColumn(ForeignKey("quotes.id"), nullable=True)
    fulfillment_mode: Mapped[str] = MappedColumn(String(20), default="stock")

    # Contact commercial hérité du devis (pas de saisie sur la commande).
    salesperson_id: Mapped[int | None] = MappedColumn(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    status: Mapped[str] = MappedColumn(
        String(20), default=SalesOrderStatus.DRAFT.value, index=True
    )
    order_date: Mapped[date] = MappedColumn(Date, default=date.today)
    delivery_date_planned: Mapped[date | None] = MappedColumn(Date)

    currency_code: Mapped[str] = MappedColumn(String(3), default="XOF")

    amount_untaxed: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    discount_amount: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    tax_amount: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    shipping_amount: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    amount_total: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    paid_amount: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)

    notes: Mapped[str | None] = MappedColumn(String(2000))

    # Archivage caisse : masque la vente de l'historique du Point de Vente
    # sans toucher à la comptabilité (facture + paiement conservés).
    archived: Mapped[bool] = MappedColumn(Boolean, default=False, nullable=False)

    lines: Mapped[list["SalesOrderLine"]] = relationship(
        "SalesOrderLine", back_populates="order",
        cascade="all, delete-orphan", lazy="selectin",
    )

    partner: Mapped["Partner"] = relationship("Partner")
    company: Mapped["Company"] = relationship("Company")
    salesperson: Mapped["User | None"] = relationship(
        "User", foreign_keys=[salesperson_id], lazy="selectin"
    )

    def __repr__(self) -> str:
        return f"<SalesOrder {self.reference} [{self.status}]>"


class SalesOrderLine(Base, TenantMixin):
    """Ligne de commande avec suivi d'approvisionnement détaillé."""

    order_id: Mapped[int] = MappedColumn(
        ForeignKey("sales_orders.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int | None] = MappedColumn(
        ForeignKey("products.id"), nullable=True
    )
    # Variante du produit (optionnelle) — ``variant_name`` est un instantané
    # du libellé (réimpression fidèle des documents).
    variant_id: Mapped[int | None] = MappedColumn(
        ForeignKey("product_variants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    variant_name: Mapped[str | None] = MappedColumn(String(300))

    description: Mapped[str | None] = MappedColumn(String(500))
    quantity_ordered: Mapped[float] = MappedColumn(Numeric(14, 4), default=1)
    quantity_reserved: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    quantity_available: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    quantity_to_purchase: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    quantity_purchased: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    quantity_delivered: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)

    unit: Mapped[str | None] = MappedColumn(String(20))
    sell_by_length: Mapped[bool] = MappedColumn(Boolean, default=False)
    unit_price: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    purchase_price: Mapped[float | None] = MappedColumn(Numeric(14, 4))
    discount_percent: Mapped[float] = MappedColumn(Numeric(6, 2), default=0)

    total_length: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    subtotal: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    position: Mapped[int] = MappedColumn(Integer, default=0)

    order: Mapped["SalesOrder"] = relationship("SalesOrder", back_populates="lines")
    product: Mapped["Product"] = relationship("Product", lazy="selectin")
    variant: Mapped["ProductVariant | None"] = relationship(
        "ProductVariant", lazy="selectin"
    )
    cuts: Mapped[list["OrderLineCut"]] = relationship(
        "OrderLineCut", back_populates="line",
        cascade="all, delete-orphan", lazy="selectin",
    )

    @property
    def remaining_to_supply(self) -> float:
        return max(
            float(self.quantity_ordered)
            - float(self.quantity_reserved)
            - float(self.quantity_purchased),
            0.0,
        )


class OrderLineCut(Base):
    """Sous-ligne de coupe BAC d'une ligne de commande (jamais perdue)."""

    __tablename__ = "sales_order_line_cuts"

    id: Mapped[int] = MappedColumn(Integer, primary_key=True, autoincrement=True)
    line_id: Mapped[int] = MappedColumn(
        ForeignKey("sales_order_lines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    quantity: Mapped[float] = MappedColumn(Numeric(14, 4), default=1)
    length: Mapped[float] = MappedColumn(Numeric(12, 4), nullable=False)
    unit_price: Mapped[float | None] = MappedColumn(Numeric(14, 4))

    line: Mapped["SalesOrderLine"] = relationship("SalesOrderLine", back_populates="cuts")