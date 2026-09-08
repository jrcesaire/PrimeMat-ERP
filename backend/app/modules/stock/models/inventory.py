"""
Modèles Stock — entrepôts, niveaux de stock et mouvements.

- ``StockLevel`` : stock réel / réservé / disponible par produit et entrepôt
- ``StockMovement`` : entrées, sorties, transferts, ajustements, pertes
"""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin
from app.shared.enums import StockMovementType


class Warehouse(Base, TenantMixin):
    """Entrepôt / magasin / emplacement."""

    name: Mapped[str] = MappedColumn(String(200), nullable=False)
    code: Mapped[str | None] = MappedColumn(String(30), index=True)
    warehouse_type: Mapped[str] = MappedColumn(String(20), default="warehouse")
    address: Mapped[dict[str, Any]] = MappedColumn(JSON, default=dict)
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    levels: Mapped[list["StockLevel"]] = relationship(
        "StockLevel", back_populates="warehouse",
        cascade="all, delete-orphan", lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Warehouse {self.code or self.name}>"


class StockLevel(Base, TenantMixin):
    """
    Niveau de stock d'un produit dans un entrepôt.

    - ``quantity_on_hand``  : stock réel (physique)
    - ``quantity_reserved`` : stock réservé pour des commandes
    - ``quantity_incoming`` : stock attendu (commandes fournisseurs)
    """

    __tablename__ = "stock_levels"
    __table_args__ = (
        UniqueConstraint("company_id", "warehouse_id", "product_id",
                         name="uq_stock_level"),
    )

    warehouse_id: Mapped[int] = MappedColumn(
        ForeignKey("warehouses.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int] = MappedColumn(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    location: Mapped[str | None] = MappedColumn(String(100))

    quantity_on_hand: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    quantity_reserved: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    quantity_incoming: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)

    # Valorisation
    unit_cost: Mapped[float | None] = MappedColumn(Numeric(14, 6))

    warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse", back_populates="levels"
    )

    @property
    def available(self) -> float:
        return float(self.quantity_on_hand) - float(self.quantity_reserved)

    def __repr__(self) -> str:
        return f"<StockLevel wh={self.warehouse_id} p={self.product_id} qoh={self.quantity_on_hand}>"


class StockMovement(Base, TenantMixin):
    """
    Mouvement de stock.

    Types : entrée, sortie, transfert, ajustement, retour, perte, casse.
    """

    movement_type: Mapped[str] = MappedColumn(
        String(20), default=StockMovementType.INBOUND.value, index=True
    )
    warehouse_id: Mapped[int] = MappedColumn(
        ForeignKey("warehouses.id"), nullable=False, index=True
    )
    target_warehouse_id: Mapped[int | None] = MappedColumn(
        ForeignKey("warehouses.id"), nullable=True
    )  # pour les transferts

    product_id: Mapped[int] = MappedColumn(
        ForeignKey("products.id"), nullable=False, index=True
    )
    quantity: Mapped[float] = MappedColumn(Numeric(14, 4), nullable=False)
    unit_cost: Mapped[float | None] = MappedColumn(Numeric(14, 6))

    reference_document: Mapped[str | None] = MappedColumn(String(50))
    reference_id: Mapped[int | None] = MappedColumn(Integer)
    notes: Mapped[str | None] = MappedColumn(String(1000))
    metadata_json: Mapped[dict[str, Any]] = MappedColumn(JSON, default=dict)

    warehouse: Mapped["Warehouse"] = relationship(
        "Warehouse", foreign_keys=[warehouse_id]
    )

    def __repr__(self) -> str:
        return f"<StockMovement {self.movement_type} p={self.product_id} q={self.quantity}>"


class StockReservation(Base, TenantMixin):
    """Réservation de stock pour une commande client."""

    level_id: Mapped[int] = MappedColumn(
        ForeignKey("stock_levels.id", ondelete="CASCADE"), nullable=False
    )
    order_id: Mapped[int | None] = MappedColumn(Integer, index=True)
    order_line_id: Mapped[int | None] = MappedColumn(Integer)
    quantity: Mapped[float] = MappedColumn(Numeric(14, 4), nullable=False)
    status: Mapped[str] = MappedColumn(String(20), default="active")

    level: Mapped["StockLevel"] = relationship("StockLevel")

    def __repr__(self) -> str:
        return f"<StockReservation level={self.level_id} q={self.quantity} [{self.status}]>"