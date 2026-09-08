"""
Service Stock — niveaux, réservations et mouvements.

- ``get_available_stock`` : stock disponible par produit
- ``reserve`` / ``release`` : réservation pour commande
- ``record_movement`` : entrée / sortie / transfert / ajustement
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.shared.events import event_bus
from app.modules.stock.models.inventory import (
    StockLevel,
    StockMovement,
    StockReservation,
)

logger = logging.getLogger(__name__)


class StockService:
    """Service du module Stock."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------ #
    # Lecture
    # ------------------------------------------------------------------ #
    async def get_available_stock(
        self, product_id: int, warehouse_id: int | None = None
    ) -> float:
        """Stock disponible = réel − réservé, tous entrepôts ou un seul."""
        stmt = select(StockLevel).where(StockLevel.product_id == product_id)
        if warehouse_id:
            stmt = stmt.where(StockLevel.warehouse_id == warehouse_id)
        result = await self.session.execute(stmt)
        levels = result.scalars().all()
        return sum(level.available for level in levels)

    async def get_or_create_level(
        self, warehouse_id: int, product_id: int
    ) -> StockLevel:
        """Récupère ou crée la ligne de niveau de stock (tenant hérité)."""
        result = await self.session.execute(
            select(StockLevel).where(
                StockLevel.warehouse_id == warehouse_id,
                StockLevel.product_id == product_id,
            )
        )
        level = result.scalars().first()
        if level is None:
            from app.modules.stock.models.inventory import Warehouse

            warehouse = await self.session.get(Warehouse, warehouse_id)
            if warehouse is None:
                raise ValueError(f"Entrepôt {warehouse_id} introuvable")
            level = StockLevel(
                warehouse_id=warehouse_id,
                product_id=product_id,
                company_id=warehouse.company_id,
            )
            self.session.add(level)
            await self.session.flush()
        return level

    # ------------------------------------------------------------------ #
    # Réservations
    # ------------------------------------------------------------------ #
    async def reserve(
        self,
        product_id: int,
        quantity: float,
        warehouse_id: int,
        order_id: int | None = None,
    ) -> float:
        """
        Réserve du stock pour une commande. Retourne la quantité réservée.

        Ne réserve jamais plus que le disponible.
        Émet ``inventory.stock.reserved``.
        """
        level = await self.get_or_create_level(warehouse_id, product_id)
        to_reserve = min(quantity, level.available)
        if to_reserve <= 0:
            return 0.0

        level.quantity_reserved = float(level.quantity_reserved) + to_reserve
        reservation = StockReservation(
            level_id=level.id,
            order_id=order_id,
            quantity=to_reserve,
            status="active",
            company_id=level.company_id,
        )
        self.session.add(reservation)
        await self.session.commit()

        await event_bus.emit("inventory.stock.reserved", {
            "product_id": product_id,
            "quantity": to_reserve,
            "order_id": order_id,
        })
        return to_reserve

    async def release(
        self, product_id: int, quantity: float, order_id: int | None = None
    ) -> float:
        """Libère une réservation. Émet ``inventory.stock.released``."""
        stmt = select(StockReservation).where(
            StockReservation.status == "active",
            StockReservation.order_id == order_id,
        )
        result = await self.session.execute(stmt)
        remaining = quantity
        released = 0.0
        for res in result.scalars().all():
            take = min(float(res.quantity), remaining)
            if take <= 0:
                break
            res.quantity = float(res.quantity) - take
            if float(res.quantity) <= 0:
                res.status = "released"
            level = await self.session.get(StockLevel, res.level_id)
            if level and level.product_id == product_id:
                level.quantity_reserved = max(
                    float(level.quantity_reserved) - take, 0.0
                )
            released += take
            remaining -= take
        await self.session.commit()

        if released > 0:
            await event_bus.emit("inventory.stock.released", {
                "product_id": product_id,
                "quantity": released,
                "order_id": order_id,
            })
        return released

    async def reserve_across_warehouses(
        self,
        product_id: int,
        quantity: float,
        order_id: int | None = None,
    ) -> float:
        """
        Réserve ``quantity`` en parcourant les entrepôts disposant de stock.

        Retourne la quantité effectivement réservée.
        """
        stmt = (
            select(StockLevel)
            .where(StockLevel.product_id == product_id)
            .order_by(StockLevel.id)
        )
        result = await self.session.execute(stmt)
        remaining = quantity
        reserved_total = 0.0
        for level in result.scalars().all():
            if remaining <= 0:
                break
            take = min(level.available, remaining)
            if take <= 0:
                continue
            level.quantity_reserved = float(level.quantity_reserved) + take
            self.session.add(StockReservation(
                level_id=level.id,
                order_id=order_id,
                quantity=take,
                status="active",
                company_id=level.company_id,
            ))
            reserved_total += take
            remaining -= take
        if reserved_total > 0:
            await self.session.commit()
            await event_bus.emit("inventory.stock.reserved", {
                "product_id": product_id,
                "quantity": reserved_total,
                "order_id": order_id,
            })
        return reserved_total

    # ------------------------------------------------------------------ #
    # Mouvements
    # ------------------------------------------------------------------ #
    async def record_movement(
        self,
        movement_type: str,
        warehouse_id: int,
        product_id: int,
        quantity: float,
        target_warehouse_id: int | None = None,
        unit_cost: float | None = None,
        reference_document: str | None = None,
        reference_id: int | None = None,
        notes: str | None = None,
    ) -> StockMovement:
        """
        Enregistre un mouvement et met à jour les niveaux de stock.

        - ``inbound``    : +quantité
        - ``outbound``   : −quantité
        - ``transfer``   : −source / +cible
        - ``adjustment`` : fixe le niveau réel à ``quantity``
        - ``loss`` / ``damage`` / ``return``
        """
        from app.shared.enums import StockMovementType
        from app.modules.stock.models.inventory import Warehouse

        # Le mouvement hérite du tenant de l'entrepôt
        warehouse = await self.session.get(Warehouse, warehouse_id)
        if warehouse is None:
            raise ValueError(f"Entrepôt {warehouse_id} introuvable")
        company_id = warehouse.company_id

        movement = StockMovement(
            movement_type=movement_type,
            warehouse_id=warehouse_id,
            target_warehouse_id=target_warehouse_id,
            product_id=product_id,
            quantity=quantity,
            unit_cost=unit_cost,
            reference_document=reference_document,
            reference_id=reference_id,
            notes=notes,
            company_id=company_id,
        )
        self.session.add(movement)

        if movement_type == StockMovementType.INBOUND.value:
            level = await self._get_level(warehouse_id, product_id, company_id)
            level.quantity_on_hand = float(level.quantity_on_hand) + quantity
            if unit_cost:
                level.unit_cost = unit_cost
        elif movement_type == StockMovementType.OUTBOUND.value:
            level = await self._get_level(warehouse_id, product_id, company_id)
            level.quantity_on_hand = float(level.quantity_on_hand) - quantity
        elif (
            movement_type == StockMovementType.TRANSFER.value
            and target_warehouse_id
        ):
            src = await self._get_level(warehouse_id, product_id, company_id)
            src.quantity_on_hand = float(src.quantity_on_hand) - quantity
            dst = await self._get_level(target_warehouse_id, product_id, company_id)
            dst.quantity_on_hand = float(dst.quantity_on_hand) + quantity
        elif movement_type == StockMovementType.ADJUSTMENT.value:
            level = await self._get_level(warehouse_id, product_id, company_id)
            level.quantity_on_hand = quantity
        elif movement_type in (
            StockMovementType.LOSS.value,
            StockMovementType.DAMAGE.value,
        ):
            level = await self._get_level(warehouse_id, product_id, company_id)
            level.quantity_on_hand = float(level.quantity_on_hand) - abs(quantity)
        elif movement_type == StockMovementType.RETURN.value:
            level = await self._get_level(warehouse_id, product_id, company_id)
            level.quantity_on_hand = float(level.quantity_on_hand) + abs(quantity)

        await self.session.commit()
        await self.session.refresh(movement)
        return movement

    async def _get_level(
        self, warehouse_id: int, product_id: int, company_id: int
    ) -> StockLevel:
        """Récupère ou crée le niveau de stock avec le bon tenant."""
        level = await self.get_or_create_level(warehouse_id, product_id)
        if level.company_id is None:
            level.company_id = company_id
        return level