"""Service Livraison — bons de livraison depuis les commandes."""
from __future__ import annotations

import logging
from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.services.sequence_service import SequenceService
from app.modules.delivery.models.delivery import (
    DeliveryLine,
    DeliveryLineCut,
    DeliveryNote,
)
from app.shared.enums import DeliveryStatus

logger = logging.getLogger(__name__)


class DeliveryService:
    """Service des bons de livraison."""

    #: Transitions autorisées entre statuts (un bon complété n'est plus modifiable).
    _NEXT_STATUS: dict[str, tuple[str, ...]] = {
        DeliveryStatus.DRAFT.value: (
            DeliveryStatus.PENDING.value,
            DeliveryStatus.IN_PROGRESS.value,
            DeliveryStatus.CANCELLED.value,
        ),
        DeliveryStatus.PENDING.value: (
            DeliveryStatus.IN_PROGRESS.value,
            DeliveryStatus.DELIVERED.value,
            DeliveryStatus.COMPLETED.value,
            DeliveryStatus.CANCELLED.value,
        ),
        DeliveryStatus.IN_PROGRESS.value: (
            DeliveryStatus.DELIVERED.value,
            DeliveryStatus.COMPLETED.value,
            DeliveryStatus.CANCELLED.value,
        ),
        DeliveryStatus.DELIVERED.value: (
            DeliveryStatus.COMPLETED.value,
        ),
        DeliveryStatus.COMPLETED.value: (),
        DeliveryStatus.CANCELLED.value: (),
    }

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sequences = SequenceService(session)

    async def get_delivery(self, delivery_id: int) -> DeliveryNote | None:
        return await self.session.get(DeliveryNote, delivery_id)

    async def list_deliveries(
        self, skip: int = 0, limit: int = 100, order_id: int | None = None
    ) -> list[DeliveryNote]:
        """Bons de livraison (plus récents d'abord), filtrables par commande."""
        stmt = select(DeliveryNote)
        if order_id is not None:
            stmt = stmt.where(DeliveryNote.order_id == order_id)
        result = await self.session.execute(
            stmt.options(
                selectinload(DeliveryNote.lines).selectinload(DeliveryLine.cuts),
            )
            .order_by(DeliveryNote.id.desc())
            .offset(skip)
            .limit(limit)
        )
        return list(result.scalars().all())

    async def update_status(self, delivery_id: int, status: str) -> DeliveryNote | None:
        """Fait avancer un bon de livraison selon les transitions autorisées.

        ``pending → in_progress → delivered → completed`` (ou ``cancelled``
        avant complétion).  La date de livraison est horodatée dès la
        livraison (ou à la complétion si livrée directement).
        Lève ``ValueError`` si la transition demandée est interdite.
        """
        delivery = await self.session.get(DeliveryNote, delivery_id)
        if delivery is None:
            return None
        current = delivery.status or DeliveryStatus.PENDING.value
        if status == current:
            return delivery
        allowed = self._NEXT_STATUS.get(current, ())
        if status not in allowed:
            raise ValueError(
                f"Transition « {current} » → « {status} » impossible "
                f"(statut attendu : {', '.join(allowed) or 'aucun'})."
            )
        delivery.status = status
        if (
            status
            in (DeliveryStatus.DELIVERED.value, DeliveryStatus.COMPLETED.value)
            and delivery.delivery_date is None
        ):
            delivery.delivery_date = date.today()
        await self.session.commit()
        await self.session.refresh(delivery)
        return delivery

    async def create_from_order(
        self, order_id: int, expected_date=None, notes: str | None = None
    ) -> DeliveryNote:
        """Crée un bon de livraison depuis une commande (coupes préservées)."""
        from app.modules.sales.models.order import SalesOrder, SalesOrderLine

        result = await self.session.execute(
            select(SalesOrder)
            .options(
                selectinload(SalesOrder.lines).selectinload(SalesOrderLine.cuts),
            )
            .where(SalesOrder.id == order_id)
        )
        order = result.scalar_one_or_none()
        if order is None:
            raise ValueError(f"Commande {order_id} introuvable")

        reference = await self.sequences.next_value("delivery", "BL")

        delivery = DeliveryNote(
            reference=reference,
            order_id=order.id,
            partner_id=order.partner_id,
            status=DeliveryStatus.PENDING.value,
            expected_date=expected_date or order.delivery_date_planned,
            notes=notes,
            company_id=order.company_id,
        )

        for oline in order.lines:
            line = DeliveryLine(
                product_id=oline.product_id,
                description=oline.description,
                quantity=float(oline.quantity_ordered or 0),
                quantity_ordered=float(oline.quantity_ordered or 0),
                unit=oline.unit,
                sell_by_length=oline.sell_by_length,
                total_length=float(oline.total_length or 0),
                company_id=order.company_id,
            )
            if oline.cuts:
                for cut in oline.cuts:
                    line.cuts.append(
                        DeliveryLineCut(
                            quantity=float(cut.quantity),
                            length=float(cut.length),
                        )
                    )
            delivery.lines.append(line)

        self.session.add(delivery)
        await self.session.commit()

        # Recharge avec les relations (lazy-load interdit hors session sync)
        result = await self.session.execute(
            select(DeliveryNote)
            .options(
                selectinload(DeliveryNote.lines).selectinload(DeliveryLine.cuts),
            )
            .where(DeliveryNote.id == delivery.id)
        )
        loaded = result.scalar_one()
        return loaded