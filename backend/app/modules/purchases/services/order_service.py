"""
Service Bon de Commande (BC) — CRUD, workflow, conversion depuis DA.

Workflow (enum ``PurchaseOrderStatus``) :
    draft → pending → confirmed → partially_received → received → done
    draft / pending → cancelled

La conversion d'une demande approuvée crée un BC brouillon pré-rempli
(``origin_request_id`` tracé), sans consommer de stock.
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
    PurchaseRequest,
)
from app.modules.purchases.schemas import (
    PurchaseOrderCreate,
    PurchaseOrderUpdate,
)
from app.shared.enums import PurchaseOrderStatus, PurchaseRequestStatus

logger = logging.getLogger(__name__)


def _recompute_totals(order: PurchaseOrder) -> None:
    """Recalcule les totaux de l'en-tête depuis les lignes."""
    untaxed = sum(line.subtotal for line in order.lines)
    tax = sum(line.tax_amount for line in order.lines)
    order.amount_untaxed = untaxed
    order.amount_total = untaxed + tax
    order.tax_amount = tax


class OrderService:
    """Gestion des bons de commande fournisseur."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sequences = SequenceService(session)

    # ------------------------------------------------------------------ #
    # Lecture
    # ------------------------------------------------------------------ #
    async def list_orders(
        self,
        skip: int = 0,
        limit: int = 100,
        status: str | None = None,
        supplier_id: int | None = None,
    ) -> list[PurchaseOrder]:
        stmt = select(PurchaseOrder).options(
            selectinload(PurchaseOrder.lines),
            selectinload(PurchaseOrder.supplier),
        )
        if status:
            stmt = stmt.where(PurchaseOrder.status == status)
        if supplier_id:
            stmt = stmt.where(PurchaseOrder.supplier_id == supplier_id)
        stmt = stmt.order_by(PurchaseOrder.id.desc()).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_order(self, order_id: int) -> PurchaseOrder | None:
        stmt = (
            select(PurchaseOrder)
            .options(
                selectinload(PurchaseOrder.lines).selectinload(PurchaseOrderLine.product),
                selectinload(PurchaseOrder.supplier),
                selectinload(PurchaseOrder.receptions),
            )
            .where(PurchaseOrder.id == order_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    # ------------------------------------------------------------------ #
    # Écriture
    # ------------------------------------------------------------------ #
    async def create_order(
        self, data: PurchaseOrderCreate, company_id: int
    ) -> PurchaseOrder:
        if not data.lines:
            raise ValueError("Le bon de commande doit comporter au moins une ligne.")

        number = await self.sequences.next_value("purchase_order", "BC")
        order = PurchaseOrder(
            number=number,
            supplier_id=data.supplier_id,
            origin_request_id=data.origin_request_id,
            status=PurchaseOrderStatus.DRAFT.value,
            order_date=data.order_date,
            expected_date=data.expected_date,
            currency_code=data.currency_code,
            payment_terms_days=data.payment_terms_days,
            notes=data.notes,
            company_id=company_id,
        )
        self.session.add(order)

        # Lignes rattachées via la collection (`lines.append`) : un `session.add`
        # avec `order_id=` laisserait `order.lines` non chargée → lazy-load async
        # (MissingGreenlet) dans `_recompute_totals` et la sérialisation réponse.
        for line_data in data.lines:
            tax_rate = line_data.tax_rate or data.tax_percent
            order.lines.append(
                PurchaseOrderLine(
                    product_id=line_data.product_id,
                    description=line_data.description,
                    quantity=line_data.quantity,
                    unit=line_data.unit,
                    unit_price=line_data.unit_price,
                    tax_rate=tax_rate,
                    discount_percent=line_data.discount_percent,
                    company_id=company_id,
                )
            )

        _recompute_totals(order)
        await self.session.commit()
        await self.session.refresh(order)
        logger.info("BC %s créée (%s)", number, order.status)
        return order


    async def update_order(
        self, order_id: int, data: PurchaseOrderUpdate
    ) -> PurchaseOrder | None:
        order = await self.get_order(order_id)
        if order is None:
            return None
        if order.status != PurchaseOrderStatus.DRAFT.value:
            raise ValueError("Seul un bon de commande brouillon peut être modifié.")

        for field in ("supplier_id", "order_date", "expected_date",
                      "currency_code", "payment_terms_days", "notes"):
            value = getattr(data, field, None)
            if value is not None:
                setattr(order, field, value)

        if data.lines is not None:
            if not data.lines:
                raise ValueError("Le bon de commande doit comporter au moins une ligne.")
            order.lines.clear()
            await self.session.flush()
            for line_data in data.lines:
                order.lines.append(
                    PurchaseOrderLine(
                        product_id=line_data.product_id,
                        description=line_data.description,
                        quantity=line_data.quantity,
                        unit=line_data.unit,
                        unit_price=line_data.unit_price,
                        tax_rate=line_data.tax_rate,
                        discount_percent=line_data.discount_percent,
                        company_id=order.company_id,
                    )
                )

        _recompute_totals(order)
        await self.session.commit()
        await self.session.refresh(order)
        return order

    # ------------------------------------------------------------------ #
    # Workflow
    # ------------------------------------------------------------------ #
    async def submit(self, order_id: int) -> PurchaseOrder | None:
        """Brouillon → en attente de confirmation."""
        order = await self.get_order(order_id)
        if order is None:
            return None
        if order.status != PurchaseOrderStatus.DRAFT.value:
            raise ValueError("Seul un brouillon peut être soumis.")
        order.status = PurchaseOrderStatus.PENDING.value
        await self.session.commit()
        await self.session.refresh(order)
        return order

    async def confirm(self, order_id: int) -> PurchaseOrder | None:
        """Confirmation — la BC est validée et peut être réceptionnée."""
        order = await self.get_order(order_id)
        if order is None:
            return None
        if order.status not in (
            PurchaseOrderStatus.DRAFT.value,
            PurchaseOrderStatus.PENDING.value,
        ):
            raise ValueError("Seul un brouillon ou une demande en attente peut être confirmée.")
        order.status = PurchaseOrderStatus.CONFIRMED.value
        order.confirmed_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(order)
        logger.info("BC %s confirmée", order.number)
        return order

    async def cancel(self, order_id: int) -> PurchaseOrder | None:
        order = await self.get_order(order_id)
        if order is None:
            return None
        if order.status in (
            PurchaseOrderStatus.RECEIVED.value,
            PurchaseOrderStatus.DONE.value,
            PurchaseOrderStatus.CANCELLED.value,
        ):
            raise ValueError("Cette commande ne peut plus être annulée.")
        order.status = PurchaseOrderStatus.CANCELLED.value
        order.cancelled_at = datetime.utcnow()
        await self.session.commit()
        await self.session.refresh(order)
        logger.info("BC %s annulée", order.number)
        return order



    # ------------------------------------------------------------------ #
    # Conversion depuis une demande approuvée
    # ------------------------------------------------------------------ #
    async def convert_from_request(
        self, request_id: int, company_id: int
    ) -> PurchaseOrder:
        """Crée un BC brouillon à partir d'une DA approuvée."""
        request = await self.session.get(PurchaseRequest, request_id)
        if request is None:
            raise ValueError("Demande d'achat introuvable.")
        if request.status != PurchaseRequestStatus.APPROVED.value:
            raise ValueError("Seule une demande approuvée peut être convertie.")

        supplier_id = request.supplier_id
        if supplier_id is None:
            raise ValueError(
                "La demande n'a pas de fournisseur — choisissez-en un avant conversion."
            )

        number = await self.sequences.next_value("purchase_order", "BC")
        order = PurchaseOrder(
            number=number,
            supplier_id=supplier_id,
            origin_request_id=request.id,
            status=PurchaseOrderStatus.DRAFT.value,
            order_date=request.needed_by or request.request_date,
            expected_date=request.needed_by,
            notes=request.notes,
            company_id=company_id,
        )

        for req_line in request.lines:
            order.lines.append(
                PurchaseOrderLine(
                    product_id=req_line.product_id,
                    description=req_line.description,
                    quantity=req_line.quantity,
                    unit=req_line.unit,
                    unit_price=req_line.estimated_unit_price,
                    tax_rate=0,
                    company_id=company_id,
                )
            )

        self.session.add(order)
        _recompute_totals(order)
        request.status = PurchaseRequestStatus.CONVERTED.value
        await self.session.commit()
        await self.session.refresh(order)
        logger.info("Demande %s convertie en BC %s", request.number, number)
        return order

    # ------------------------------------------------------------------ #
    # Réception (appelé par ReceptionService)
    # ------------------------------------------------------------------ #
    async def refresh_receipt_status(self, order_id: int) -> None:
        """Recalcule le statut BC d'après les quantités reçues."""
        order = await self.get_order(order_id)
        if order is None:
            return
        if order.status not in (
            PurchaseOrderStatus.CONFIRMED.value,
            PurchaseOrderStatus.PARTIALLY_RECEIVED.value,
            PurchaseOrderStatus.RECEIVED.value,
        ):
            return
        if not order.lines:
            return
        all_received = all(
            float(l.quantity_received) >= float(l.quantity) for l in order.lines
        )
        any_received = any(float(l.quantity_received) > 0 for l in order.lines)
        if all_received:
            order.status = PurchaseOrderStatus.RECEIVED.value
        elif any_received:
            order.status = PurchaseOrderStatus.PARTIALLY_RECEIVED.value
        await self.session.commit()

