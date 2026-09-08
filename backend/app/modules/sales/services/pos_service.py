"""Service Point de Vente — vente comptoir simple (panier → ticket).

Flux du pipeline cœur :
    panier → commande (fulfillment_mode="pos") → sortie de stock
            → facture → paiement (reçu) → ticket de caisse
"""
from __future__ import annotations

import logging

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.invoicing.services.invoice_service import InvoiceService
from app.modules.payments.services.payment_service import PaymentService
from app.modules.sales.models.order import SalesOrder
from app.modules.sales.schemas import PosSaleCreate
from app.modules.sales.services.order_service import OrderService

logger = logging.getLogger(__name__)


class PosService:
    """Ventes comptoir."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.orders_ = OrderService(session)

    async def create_pos_sale(self, data: PosSaleCreate) -> dict:
        """Crée la commande comptoir + sortie stock + facture + paiement."""
        # 1) Commande client (mode pos)
        order = await self.orders_.create_order(
            data.to_sales_order_create()
        )

        # 2) Sortie de stock immédiate (produits non gérés au ml)
        from app.modules.stock.services.stock_service import StockService

        stock_service = StockService(self.session)
        from app.modules.stock.models.inventory import Warehouse
        from sqlalchemy import select

        warehouse_id = data.warehouse_id
        if not warehouse_id:
            result = await self.session.execute(
                select(Warehouse).order_by(Warehouse.id).limit(1)
            )
            wh = result.scalar_one_or_none()
            warehouse_id = wh.id if wh else None

        if warehouse_id:
            from app.modules.stock.models.inventory import StockMovement  # noqa: F401

            for line in order.lines:
                if line.product_id and not line.sell_by_length:
                    await stock_service.record_movement(
                        movement_type="outbound",
                        warehouse_id=warehouse_id,
                        product_id=line.product_id,
                        quantity=float(line.quantity_ordered),
                        reference_document="POS",
                        reference_id=order.id,
                        notes=f"Vente comptoir {order.reference}",
                    )

        order.status = "confirmed"
        await self.session.commit()

        # 3) Facture + paiement
        invoice = await InvoiceService(self.session).create_from_order(order.id)
        payment = None
        if data.amount and data.amount > 0:
            from app.modules.payments.schemas import PaymentCreate
            from app.modules.payments.services.payment_service import PaymentService

            payment_data = PaymentCreate(
                partner_id=data.partner_id,
                invoice_id=invoice.id,
                amount=data.amount,
                method=data.method or "cash",
                direction="in",
                notes=f"Vente comptoir {order.reference}",
            )
            payment = await PaymentService(self.session).create_payment(payment_data)

        return {
            "order_id": order.id,
            "order_reference": order.reference,
            "invoice_id": invoice.id,
            "invoice_reference": invoice.reference,
            "payment_id": payment.id if payment else None,
            "payment_reference": payment.reference if payment else None,
            "total": float(order.amount_total or 0),
            "method": data.method or "cash",
        }