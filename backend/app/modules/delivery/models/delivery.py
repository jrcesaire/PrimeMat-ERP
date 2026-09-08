"""
Modèles Livraison — DeliveryNote / DeliveryLine / DeliveryLineCut.

Un bon de livraison est généré depuis une commande confirmée. Il présente
la commande de référence et les quantités à livrer, avec les listes de
longueurs à découper (coupes BAC) pour la préparation.
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
from app.shared.enums import DeliveryStatus


class DeliveryNote(Base, TenantMixin):
    """Bon de livraison attaché à une commande client."""

    reference: Mapped[str] = MappedColumn(String(30), unique=True, index=True)
    order_id: Mapped[int] = MappedColumn(
        ForeignKey("sales_orders.id"), nullable=False, index=True
    )
    partner_id: Mapped[int] = MappedColumn(
        ForeignKey("partners.id"), nullable=False, index=True
    )

    status: Mapped[str] = MappedColumn(
        String(20), default=DeliveryStatus.PENDING.value, index=True
    )
    delivery_date: Mapped[date | None] = MappedColumn(Date)
    expected_date: Mapped[date | None] = MappedColumn(Date)

    notes: Mapped[str | None] = MappedColumn(String(2000))
    shipping_address: Mapped[str | None] = MappedColumn(String(500))

    lines: Mapped[list["DeliveryLine"]] = relationship(
        "DeliveryLine", back_populates="delivery",
        cascade="all, delete-orphan", lazy="selectin",
    )

    partner: Mapped["Partner"] = relationship("Partner")
    company: Mapped["Company"] = relationship("Company")
    order: Mapped["SalesOrder"] = relationship("SalesOrder")

    def __repr__(self) -> str:
        return f"<DeliveryNote {self.reference} [{self.status}]>"


class DeliveryLine(Base, TenantMixin):
    """Ligne de bon de livraison — quantité commandée vs livrée."""

    delivery_id: Mapped[int] = MappedColumn(
        ForeignKey("delivery_notes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int | None] = MappedColumn(ForeignKey("products.id"), nullable=True)

    description: Mapped[str | None] = MappedColumn(String(500))
    quantity: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    quantity_ordered: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    unit: Mapped[str | None] = MappedColumn(String(20))

    sell_by_length: Mapped[bool] = MappedColumn(Boolean, default=False)
    total_length: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)

    delivery: Mapped["DeliveryNote"] = relationship("DeliveryNote", back_populates="lines")
    cuts: Mapped[list["DeliveryLineCut"]] = relationship(
        "DeliveryLineCut", back_populates="line",
        cascade="all, delete-orphan", lazy="selectin",
    )


class DeliveryLineCut(Base):
    """Sous-ligne de coupe BAC d'un bon de livraison."""

    __tablename__ = "delivery_line_cuts"

    id: Mapped[int] = MappedColumn(Integer, primary_key=True, autoincrement=True)
    line_id: Mapped[int] = MappedColumn(
        ForeignKey("delivery_lines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity: Mapped[float] = MappedColumn(Numeric(14, 4), default=1)
    length: Mapped[float] = MappedColumn(Numeric(12, 4), nullable=False)

    line: Mapped["DeliveryLine"] = relationship("DeliveryLine", back_populates="cuts")