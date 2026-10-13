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

#: Partenaire walk-in utilisé quand la vente comptoir n'a pas de client.
WALK_IN_PARTNER_NAME = "Client de passage"


class PosService:
    """Ventes comptoir."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.orders_ = OrderService(session)

    async def _resolve_partner_id(
        self, data: PosSaleCreate, company_id: int | None
    ) -> int:
        """Client choisi, sinon partenaire walk-in « Client de passage ».

        Le partenaire walk-in est créé à la volée (une seule fois par
        entreprise) pour que la caisse puisse encaisser sans client imposé.
        """
        if data.partner_id:
            return data.partner_id

        from sqlalchemy import select

        from app.modules.crm.models.partner import Partner

        stmt = select(Partner).where(Partner.name == WALK_IN_PARTNER_NAME)
        if company_id:
            stmt = stmt.where(Partner.company_id == company_id)
        partner = (await self.session.execute(stmt)).scalars().first()
        if partner is None:
            if company_id is None:
                raise ValueError(
                    "Impossible de créer le client de passage : entreprise absente"
                )
            partner = Partner(
                name=WALK_IN_PARTNER_NAME,
                code="WALKIN",
                role="client",
                company_id=company_id,
            )
            self.session.add(partner)
            await self.session.flush()
        return partner.id

    async def create_pos_sale(
        self, data: PosSaleCreate, company_id: int | None = None
    ) -> dict:
        """Crée la commande comptoir + sortie stock + facture + paiement."""
        # 0) Client : choisi ou walk-in « Client de passage »
        partner_id = await self._resolve_partner_id(data, company_id)

        # 1) Commande client (mode pos)
        order = await self.orders_.create_order(
            data.to_sales_order_create(partner_id)
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

        # 3) Facture (comptabilisée immédiatement — vente au comptoir finalisée)
        #    + paiement (le contrôle sur-paiement S-7 s'applique normalement).
        invoice = await InvoiceService(self.session).create_from_order(
            order.id, post=True
        )
        payment = None
        total = float(order.amount_total or 0)
        received = float(data.amount or 0)
        change = 0.0
        if received > 0:
            # Caisse : le client doit couvrir le total — aucun sous-paiement.
            if received + 1e-6 < total:
                raise ValueError(
                    f"Montant reçu insuffisant : reçu {received:.2f} "
                    f"< total {total:.2f}"
                )
            # Monnaie rendue = reçu − total (toujours ≥ 0 après le contrôle).
            change = max(0.0, received - total)
            from app.modules.payments.schemas import PaymentCreate
            from app.modules.payments.services.payment_service import PaymentService

            payment_data = PaymentCreate(
                partner_id=partner_id,
                invoice_id=invoice.id,
                amount=total,  # appliqué = total (contrôle S-7 au montant exact)
                change_amount=change,
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
            "total": total,
            "amount_received": received if received > 0 else total,
            "change_amount": change,
            "method": data.method or "cash",
        }

    async def list_pos_sales(
        self, skip: int = 0, limit: int = 15, include_archived: bool = False
    ) -> dict:
        """Historique des ventes comptoir — plus récent d'abord, paginé.

        Les ventes archivées sont exclues par défaut : elles ont été
        masquées de l'historique (comptabilité conservée).
        """
        from sqlalchemy import func, select

        from app.modules.crm.models.partner import Partner
        from app.modules.invoicing.models.invoice import Invoice
        from app.modules.payments.models.payment import Payment

        cond = SalesOrder.fulfillment_mode == "pos"
        if not include_archived:
            cond = cond & (SalesOrder.archived == False)  # noqa: E712
        total = (
            await self.session.execute(
                select(func.count()).select_from(SalesOrder).where(cond)
            )
        ).scalar_one()

        res = await self.session.execute(
            select(SalesOrder)
            .where(cond)
            .order_by(SalesOrder.id.desc())
            .offset(skip)
            .limit(limit)
        )
        orders = list(res.scalars().all())

        # Noms des clients
        partner_names: dict[int, str] = {}
        partner_ids = {o.partner_id for o in orders}
        if partner_ids:
            rows = await self.session.execute(
                select(Partner.id, Partner.name).where(Partner.id.in_(partner_ids))
            )
            partner_names = dict(rows.all())

        # Mode de paiement (via facture → paiement)
        methods: dict[int, str] = {}
        order_ids = [o.id for o in orders]
        if order_ids:
            rows = await self.session.execute(
                select(Invoice.order_id, Payment.method)
                .join(Payment, Payment.invoice_id == Invoice.id)
                .where(Invoice.order_id.in_(order_ids))
            )
            methods = {oid: m for oid, m in rows.all() if oid is not None}

        items = [
            {
                "id": o.id,
                "reference": o.reference,
                "created_at": o.created_at,
                "partner_name": partner_names.get(o.partner_id),
                "items_count": len(o.lines),
                "amount_total": float(o.amount_total or 0),
                "currency_code": o.currency_code,
                "status": o.status,
                "payment_method": methods.get(o.id),
            }
            for o in orders
        ]
        return {"items": items, "total": total}

    async def get_pos_sale(self, order_id: int) -> dict:
        """Détail d'une vente comptoir : commande + lignes + facture + paiement.

        Utilisé par la vue détail de l'historique (consultation seule —
        sortir de la vente la clôture de fait, sans aucun effet de bord).
        """
        from sqlalchemy import select

        from app.modules.crm.models.partner import Partner
        from app.modules.invoicing.models.invoice import Invoice
        from app.modules.payments.models.payment import Payment

        order = await self.orders_.get_order(order_id)
        if order is None or order.fulfillment_mode != "pos":
            raise ValueError(f"Vente comptoir {order_id} introuvable")

        partner = (
            await self.session.get(Partner, order.partner_id)
            if order.partner_id
            else None
        )
        invoice = (
            await self.session.execute(
                select(Invoice).where(Invoice.order_id == order.id)
            )
        ).scalar_one_or_none()
        payment = None
        if invoice is not None:
            payment = (
                await self.session.execute(
                    select(Payment).where(Payment.invoice_id == invoice.id)
                )
            ).scalar_one_or_none()

        return {
            "id": order.id,
            "reference": order.reference,
            "created_at": order.created_at,
            "order_date": order.order_date,
            "status": order.status,
            "currency_code": order.currency_code,
            "amount_untaxed": float(order.amount_untaxed or 0),
            "amount_total": float(order.amount_total or 0),
            "archived": bool(order.archived),
            "partner": (
                {"id": partner.id, "name": partner.name} if partner else None
            ),
            "lines": [
                {
                    "product_id": line.product_id,
                    "description": line.description
                    or (line.product.name if line.product else None),
                    "variant_name": line.variant_name,
                    "quantity": float(line.quantity_ordered or 0),
                    "unit": line.unit,
                    "unit_price": float(line.unit_price or 0),
                    "discount_percent": float(line.discount_percent or 0),
                    "subtotal": float(line.subtotal or 0),
                }
                for line in sorted(
                    order.lines, key=lambda ln: (ln.position or 0, ln.id)
                )
            ],
            "invoice": (
                {
                    "id": invoice.id,
                    "reference": invoice.reference,
                    "status": invoice.status,
                }
                if invoice
                else None
            ),
            "payment": (
                {
                    "id": payment.id,
                    "reference": payment.reference,
                    "method": payment.method,
                    "amount": float(payment.amount or 0),
                    "change_amount": float(payment.change_amount or 0),
                }
                if payment
                else None
            ),
        }

    async def archive_pos_sale(self, order_id: int) -> dict:
        """Archive une vente comptoir (masquage d'historique uniquement).

        La facture et le paiement sont conservés : aucun impact comptable.
        """
        order = await self.orders_.get_order(order_id)
        if order is None or order.fulfillment_mode != "pos":
            raise ValueError(f"Vente comptoir {order_id} introuvable")
        if not order.archived:
            order.archived = True
            await self.session.commit()
        return {"id": order.id, "reference": order.reference, "archived": True}