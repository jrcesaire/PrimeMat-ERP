"""
Service Ventes — commandes client.

Modes de fulfillment :
- ``stock``  : réservation depuis le stock interne
- ``direct`` : livraison directe fournisseur → client (sans stock)
- ``hybrid`` : partie stock + partie achat fournisseur
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.services.sequence_service import SequenceService
from app.shared.events import event_bus
from app.modules.sales.models.order import OrderLineCut, SalesOrder, SalesOrderLine
from app.modules.sales.schemas import (
    OrderLineCreate,
    SalesOrderCreate,
    SalesOrderUpdate,
)

logger = logging.getLogger(__name__)


class OrderService:
    """Service des commandes clients."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.sequences = SequenceService(session)

    async def _build_line(self, data: OrderLineCreate) -> SalesOrderLine:
        line = SalesOrderLine(
            product_id=data.product_id,
            description=data.description,
            quantity_ordered=data.quantity_ordered,
            unit=data.unit,
            sell_by_length=data.sell_by_length,
            unit_price=data.unit_price,
            purchase_price=data.purchase_price,
            discount_percent=data.discount_percent,
        )
        if data.sell_by_length and data.cuts:
            total_len = 0.0
            raw = 0.0
            for cut in data.cuts:
                line.cuts.append(
                    OrderLineCut(
                        quantity=cut.quantity,
                        length=cut.length,
                        unit_price=cut.unit_price,
                    )
                )
                total_len += cut.quantity * cut.length
                price = cut.unit_price if cut.unit_price is not None else data.unit_price
                raw += cut.quantity * cut.length * float(price)
            line.total_length = total_len
            line.subtotal = raw * (1 - data.discount_percent / 100)
        else:
            line.total_length = data.quantity_ordered
            line.subtotal = (
                data.quantity_ordered * data.unit_price
                * (1 - data.discount_percent / 100)
            )
        return line

    async def create_order(self, data: SalesOrderCreate) -> SalesOrder:
        order = SalesOrder(
            reference=await self.sequences.next_value("order", "COM"),
            partner_id=data.partner_id,
            site_id=data.site_id,
            quote_id=data.quote_id,
            fulfillment_mode=data.fulfillment_mode,
            delivery_date_planned=data.delivery_date_planned,
            currency_code=data.currency_code,
            notes=data.notes,
        )
        for line_data in data.lines:
            order.lines.append(await self._build_line(line_data))
        order.amount_untaxed = sum(float(l.subtotal or 0) for l in order.lines)
        order.tax_amount = float(order.tax_amount or 0)
        order.shipping_amount = float(order.shipping_amount or 0)
        order.amount_total = (
            float(order.amount_untaxed)
            + order.tax_amount
            + order.shipping_amount
        )

        # Le document hérite du tenant de son partenaire
        if order.company_id is None:
            from app.modules.crm.models.partner import Partner

            partner = await self.session.get(Partner, data.partner_id)
            if partner is None:
                raise ValueError(f"Client {data.partner_id} introuvable")
            order.company_id = partner.company_id
        for line in order.lines:
            line.company_id = order.company_id

        self.session.add(order)
        await self.session.commit()

        # Recharge avec lignes + coupes (évite les lazy-loads async non awaités)
        result = await self.session.execute(
            select(SalesOrder)
            .options(
                selectinload(SalesOrder.lines).selectinload(SalesOrderLine.cuts)
            )
            .where(SalesOrder.id == order.id)
        )
        order = result.scalar_one()

        await event_bus.emit(
            "sales.order.created",
            {"order_id": order.id, "reference": order.reference},
        )
        return order

    async def get_order(self, order_id: int) -> SalesOrder | None:
        return await self.session.get(SalesOrder, order_id)

    async def list_orders(
        self, skip: int = 0, limit: int = 100, partner_id: int | None = None
    ) -> list[SalesOrder]:
        stmt = select(SalesOrder).offset(skip).limit(limit).order_by(SalesOrder.id.desc())
        if partner_id:
            stmt = stmt.where(SalesOrder.partner_id == partner_id)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_order(self, order_id: int, data: SalesOrderUpdate) -> SalesOrder:
        """Met à jour une commande — autorisé uniquement au statut brouillon.

        Si ``data.lines`` est fourni, toutes les lignes existantes sont
        remplacées (coupes BAC comprises) et les totaux recalculés.
        """
        order = await self.get_order(order_id)
        if order is None:
            raise ValueError(f"Commande {order_id} introuvable")
        if order.status != "draft":
            raise ValueError(
                "Seule une commande au statut « brouillon » peut être modifiée."
            )

        if data.partner_id is not None:
            order.partner_id = data.partner_id
        if data.site_id is not None:
            order.site_id = data.site_id
        if data.delivery_date_planned is not None:
            order.delivery_date_planned = data.delivery_date_planned
        if data.currency_code is not None:
            order.currency_code = data.currency_code
        if data.notes is not None:
            order.notes = data.notes

        if data.lines is not None:
            order.lines.clear()  # cascade delete-orphan (coupes incluses)
            await self.session.flush()
            for line_data in data.lines:
                line = await self._build_line(line_data)
                line.company_id = order.company_id
                order.lines.append(line)
            order.amount_untaxed = sum(float(l.subtotal or 0) for l in order.lines)
            order.amount_total = (
                float(order.amount_untaxed)
                + float(order.tax_amount or 0)
                + float(order.shipping_amount or 0)
            )

        await self.session.commit()

        result = await self.session.execute(
            select(SalesOrder)
            .options(
                selectinload(SalesOrder.lines).selectinload(SalesOrderLine.cuts)
            )
            .where(SalesOrder.id == order.id)
        )
        return result.scalar_one()

    async def delete_order(self, order_id: int) -> None:
        """Supprime une commande — brouillon uniquement (aucune réservation)."""
        order = await self.get_order(order_id)
        if order is None:
            raise ValueError(f"Commande {order_id} introuvable")
        if order.status != "draft":
            raise ValueError(
                "Seule une commande au statut « brouillon » peut être supprimée. "
                "Une commande confirmée a déjà des réservations de stock."
            )
        await self.session.delete(order)  # cascade lines + cuts
        await self.session.commit()

    async def back_to_draft(self, order_id: int) -> SalesOrder:
        """Remet une commande confirmée au statut brouillon.

        - libère les réservations de stock
        - refuse si une facture ou un bon de livraison est déjà lié
        """
        order = await self.get_order(order_id)
        if order is None:
            raise ValueError(f"Commande {order_id} introuvable")
        if order.status != "confirmed":
            raise ValueError(
                "Seule une commande confirmée peut être remise au brouillon."
            )

        # Refus si des documents sont déjà liés
        from app.modules.invoicing.models.invoice import Invoice
        from app.modules.delivery.models.delivery import DeliveryNote

        inv = await self.session.execute(
            select(Invoice).where(Invoice.order_id == order.id).limit(1)
        )
        if inv.scalar_one_or_none() is not None:
            raise ValueError(
                "Impossible : une facture est liée à cette commande. "
                "Annulez d'abord la facture."
            )
        dlv = await self.session.execute(
            select(DeliveryNote).where(DeliveryNote.order_id == order.id).limit(1)
        )
        if dlv.scalar_one_or_none() is not None:
            raise ValueError(
                "Impossible : un bon de livraison est lié à cette commande. "
                "Annulez d'abord le bon de livraison."
            )

        # Libère les réservations de stock
        from app.modules.stock.services.stock_service import StockService

        stock_service = StockService(self.session)
        for line in order.lines:
            reserved = float(line.quantity_reserved or 0)
            if reserved > 0 and line.product_id:
                await stock_service.release(line.product_id, reserved, order_id=order.id)
            line.quantity_reserved = 0
            line.quantity_available = 0
            line.quantity_to_purchase = 0

        order.status = "draft"
        await self.session.commit()

        await event_bus.emit("sales.order.back_to_draft", {"order_id": order.id})

        result = await self.session.execute(
            select(SalesOrder)
            .options(
                selectinload(SalesOrder.lines).selectinload(SalesOrderLine.cuts)
            )
            .where(SalesOrder.id == order.id)
        )
        return result.scalar_one()

    async def close_order(self, order_id: int) -> SalesOrder:
        """Clôture la vente — dernière étape du parcours de vente.

        Conditions : commande non annulée ni déjà clôturée, au moins une
        facture active **entièrement soldée**, et chaque bon de livraison
        éventuel au statut ``delivered`` ou ``completed`` (la vente peut se
        clôturer dès la livraison physique).  La commande passe à ``delivered``.

        La commande peut encore être au brouillon : dans le parcours de vente
        elle sert de conteneur technique (le devis confirmé la crée), et sa
        confirmation (réservation de stock) n'est pas une condition de vente.
        """
        from app.modules.delivery.models.delivery import DeliveryNote
        from app.modules.invoicing.models.invoice import Invoice

        order = await self.get_order(order_id)
        if order is None:
            raise ValueError(f"Commande {order_id} introuvable")
        if order.status == "delivered":
            raise ValueError("Cette vente est déjà clôturée.")
        if order.status == "cancelled":
            raise ValueError("Une commande annulée ne peut pas être clôturée.")

        invoices = list(
            (
                await self.session.execute(
                    select(Invoice).where(Invoice.order_id == order.id)
                )
            ).scalars().all()
        )
        active = [i for i in invoices if i.status not in ("cancelled", "credit")]
        if not active:
            raise ValueError(
                "Aucune facture active : facturez la vente avant de clôturer."
            )
        total = float(order.amount_total or 0)
        paid = sum(float(i.paid_amount or 0) for i in active)
        if paid + 0.005 < total:
            raise ValueError(
                f"Reste à encaisser {total - paid:.2f} — la vente doit être "
                "entièrement réglée avant clôture."
            )

        deliveries = list(
            (
                await self.session.execute(
                    select(DeliveryNote).where(DeliveryNote.order_id == order.id)
                )
            ).scalars().all()
        )
        unfinished = [
            d
            for d in deliveries
            if (d.status or "") not in ("delivered", "completed")
        ]
        if unfinished:
            raise ValueError(
                "Bon(s) de livraison non terminé(s) : "
                + ", ".join(d.reference for d in unfinished)
            )

        order.status = "delivered"
        await self.session.commit()
        logger.info("Vente %s clôturée (commande livrée)", order.reference)

        result = await self.session.execute(
            select(SalesOrder)
            .options(selectinload(SalesOrder.lines).selectinload(SalesOrderLine.cuts))
            .where(SalesOrder.id == order.id)
        )
        return result.scalar_one()

    async def confirm_order(self, order_id: int) -> dict:
        """
        Confirme une commande et lance l'analyse de fulfillment.

        - réserve le stock disponible
        - crée les besoins d'achat pour le solde
        Émet ``sales.order.confirmed``.
        """
        order = await self.get_order(order_id)
        if order is None:
            raise ValueError(f"Commande {order_id} introuvable")

        analysis = await self.analyze_fulfillment(order_id)
        order.status = "confirmed"
        await self.session.commit()

        await event_bus.emit(
            "sales.order.confirmed",
            {"order_id": order.id, "analysis": analysis},
        )
        return analysis

    async def analyze_fulfillment(self, order_id: int) -> dict:
        """
        Analyse hybride : répartit stock disponible vs besoin d'achat.

        Pour chaque ligne :
        - quantité commandée par le client
        - quantité disponible en stock
        - quantité réservée
        - quantité à acheter
        Émet ``inventory.stock.reserved`` et/ou ``purchase.need.created``.
        """
        order = await self.get_order(order_id)
        if order is None:
            raise ValueError(f"Commande {order_id} introuvable")

        from app.modules.stock.services.stock_service import StockService

        stock_service = StockService(self.session)
        needs: list[dict] = []
        reservations: list[dict] = []

        for line in order.lines:
            available = 0.0
            # Type de produit : on_demand (production) ne touche jamais au stock
            stype = "stockable"
            if line.product_id and line.product is not None:
                stype = str(getattr(line.product, "storage_type", "") or "stockable")
            on_demand = stype == "on_demand"
            if line.product_id and not line.sell_by_length and not on_demand:
                available = await stock_service.get_available_stock(line.product_id)

            to_purchase = max(float(line.quantity_ordered) - available, 0.0)

            line.quantity_available = available
            line.quantity_to_purchase = to_purchase

            # Réservation réelle du stock disponible
            if available > 0 and line.product_id:
                reserved = await stock_service.reserve_across_warehouses(
                    line.product_id,
                    min(float(line.quantity_ordered), available),
                    order_id=order.id,
                )
                line.quantity_reserved = reserved
                if reserved > 0:
                    reservations.append({
                        "product_id": line.product_id,
                        "quantity": reserved,
                    })
            else:
                line.quantity_reserved = 0

            if to_purchase > 0:
                needs.append({
                    "product_id": line.product_id,
                    "description": line.description,
                    "quantity": to_purchase,
                    "unit": line.unit,
                    "sell_by_length": line.sell_by_length,
                })

        await self.session.commit()

        result = {
            "order_id": order.id,
            "reservations": reservations,
            "purchase_needs": needs,
        }
        if reservations:
            await event_bus.emit("inventory.stock.reserved", {"order_id": order.id})
        if needs:
            await event_bus.emit(
                "purchase.need.created", {"order_id": order.id, "needs": needs}
            )
        return result