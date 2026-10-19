"""
Service Bon de Réception (BR) — création depuis un BC, validation → stock.

À la validation :
- création des mouvements de stock ``inbound`` (StockService) ;
- mise à jour de ``quantity_received`` sur les lignes de BC ;
- recalcul du statut BC (partiellement/totalement reçu).
"""
from __future__ import annotations

import logging
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.services.sequence_service import SequenceService
from app.modules.purchases.models import (
    PurchaseOrder,
    PurchaseOrderLine,
    PurchaseReception,
    PurchaseReceptionLine,
)
from app.modules.purchases.schemas import PurchaseReceptionCreate
from app.modules.stock.services.stock_service import StockService
from app.shared.enums import PurchaseOrderStatus, PurchaseReceptionStatus

logger = logging.getLogger(__name__)


class ReceptionService:
    """Gestion des réceptions fournisseur."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sequences = SequenceService(session)

    # ------------------------------------------------------------------ #
    # Lecture
    # ------------------------------------------------------------------ #
    async def list_receptions(
        self,
        skip: int = 0,
        limit: int = 100,
        order_id: int | None = None,
        status: str | None = None,
    ) -> list[PurchaseReception]:
        stmt = select(PurchaseReception).options(
            selectinload(PurchaseReception.lines),
            selectinload(PurchaseReception.order),
            selectinload(PurchaseReception.warehouse),
        )
        if order_id:
            stmt = stmt.where(PurchaseReception.order_id == order_id)
        if status:
            stmt = stmt.where(PurchaseReception.status == status)
        stmt = stmt.order_by(PurchaseReception.id.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_reception(self, reception_id: int) -> PurchaseReception | None:
        stmt = (
            select(PurchaseReception)
            .options(
                selectinload(PurchaseReception.lines),
                selectinload(PurchaseReception.order),
                selectinload(PurchaseReception.warehouse),
            )
            .where(PurchaseReception.id == reception_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    # ------------------------------------------------------------------ #
    # Écriture
    # ------------------------------------------------------------------ #
    async def create_reception(
        self, data: PurchaseReceptionCreate, company_id: int, user_id: int
    ) -> PurchaseReception:
        """Crée un BR brouillon depuis un BC confirmé."""
        order = await self.session.get(PurchaseOrder, data.order_id)
        if order is None:
            raise ValueError("Bon de commande introuvable.")
        if order.status not in (
            PurchaseOrderStatus.CONFIRMED.value,
            PurchaseOrderStatus.PARTIALLY_RECEIVED.value,
        ):
            raise ValueError(
                "Seule une commande confirmée peut être réceptionnée."
            )
        if not data.lines:
            raise ValueError("Le bon de réception doit comporter au moins une ligne.")

        # Contrôle : quantité ≤ restante à réceptionner
        remaining: dict[int, float] = {}
        for line in order.lines:
            remaining[line.id] = line.quantity_remaining
        for line_data in data.lines:
            if line_data.order_line_id is not None:
                rest = remaining.get(line_data.order_line_id)
                if rest is None:
                    raise ValueError(
                        f"Ligne de commande {line_data.order_line_id} inconnue "
                        "pour cette commande."
                    )
                if float(line_data.quantity) > rest + 1e-9:
                    raise ValueError(
                        f"Quantité {line_data.quantity} supérieure au reste "
                        f"à réceptionner ({rest})."
                    )

        number = await self.sequences.next_value("purchase_reception", "BR")
        reception = PurchaseReception(
            number=number,
            order_id=order.id,
            warehouse_id=data.warehouse_id,
            status=PurchaseReceptionStatus.DRAFT.value,
            reception_date=data.reception_date,
            received_by=user_id,
            notes=data.notes,
            company_id=company_id,
        )
        for line_data in data.lines:
            reception.lines.append(
                PurchaseReceptionLine(
                    order_line_id=line_data.order_line_id,
                    product_id=line_data.product_id,
                    description=line_data.description,
                    quantity=line_data.quantity,
                    unit_cost=line_data.unit_cost,
                    company_id=company_id,
                )
            )

        self.session.add(reception)
        await self.session.commit()
        await self.session.refresh(reception)
        logger.info("BR %s créée (BC %s)", number, order.number)
        return reception


    async def validate(self, reception_id: int) -> PurchaseReception | None:
        """Validation → mouvements de stock + mise à jour de la BC."""
        reception = await self.get_reception(reception_id)
        if reception is None:
            return None
        if reception.status != PurchaseReceptionStatus.DRAFT.value:
            raise ValueError("Seul un brouillon peut être validé.")
        if not reception.lines:
            raise ValueError("Le bon de réception est vide.")

        order = await self.session.get(PurchaseOrder, reception.order_id)
        if order is None:
            raise ValueError("Bon de commande introuvable.")

        stock = StockService(self.session)

        for line in reception.lines:
            # 1. Mouvement de stock entrant
            if line.product_id is not None:
                await stock.record_movement(
                    movement_type="inbound",
                    warehouse_id=reception.warehouse_id,
                    product_id=line.product_id,
                    quantity=float(line.quantity),
                    unit_cost=float(line.unit_cost) if line.unit_cost else None,
                    reference_document="purchase_reception",
                    reference_id=reception.id,
                    notes=f"Réception {reception.number} — BC {order.number}",
                )
            # 2. Mise à jour de la ligne de BC
            if line.order_line_id is not None:
                po_line = await self.session.get(
                    PurchaseOrderLine, line.order_line_id
                )
                if po_line is not None:
                    po_line.quantity_received = float(
                        po_line.quantity_received
                    ) + float(line.quantity)

        reception.status = PurchaseReceptionStatus.VALIDATED.value
        reception.validated_at = datetime.utcnow()
        await self.session.commit()

        # 3. Recalcul du statut de la commande
        from app.modules.purchases.services.order_service import OrderService

        await OrderService(self.session).refresh_receipt_status(order.id)
        await self.session.refresh(reception)
        logger.info("BR %s validée — stock incrémenté", reception.number)
        return reception

