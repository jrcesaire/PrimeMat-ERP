"""Service d'analytique BI — agrégats pour le module Reporting.

Agrégations calculées côté application (Python) pour rester
indépendant du moteur de base (SQLite / PostgreSQL), conformément
à la philosophie du projet. Les volumes traités (documents de
l'entreprise courante) restent modestes.

Les métriques excluent les factures brouillon/proforma/annulées :
CA facturé = statuts ``posted | paid | partially_paid``.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalogue.models.product import Product, ProductCategory
from app.modules.crm.models.partner import Partner
from app.modules.finance.models.expense import Expense
from app.modules.invoicing.models.invoice import Invoice, InvoiceLine
from app.modules.payments.models.payment import Payment
from app.modules.sales.models.order import SalesOrder

# Statuts comptabilisés dans le chiffre d'affaires facturé
_REVENUE_STATUSES = ("posted", "paid", "partially_paid")


def _month_key(d: date) -> str:
    return f"{d.year:04d}-{d.month:02d}"


def _last_months(n: int) -> list[str]:
    """Clés ``YYYY-MM`` des n derniers mois (le mois courant en dernier)."""
    today = date.today().replace(day=1)
    keys: list[str] = []
    y, m = today.year, today.month
    for _ in range(n):
        keys.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    return list(reversed(keys))


class AnalyticsService:
    """Agrégats BI de l'entreprise courante (filtrage tenant automatique)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------ #
    # Sources brutes
    # ------------------------------------------------------------------ #
    async def _revenue_invoices(self) -> list[Invoice]:
        result = await self.session.execute(
            select(Invoice).where(Invoice.status.in_(_REVENUE_STATUSES))
        )
        return list(result.scalars().all())

    async def _all_invoices(self) -> list[Invoice]:
        result = await self.session.execute(select(Invoice))
        return list(result.scalars().all())

    async def _payments_in(self) -> list[Payment]:
        result = await self.session.execute(
            select(Payment).where(Payment.direction == "in")
        )
        return list(result.scalars().all())

    async def _expenses(self) -> list[Expense]:
        result = await self.session.execute(select(Expense))
        return list(result.scalars().all())

    async def _orders(self) -> list[SalesOrder]:
        result = await self.session.execute(select(SalesOrder))
        return list(result.scalars().all())

    # ------------------------------------------------------------------ #
    # KPIs consolidés
    # ------------------------------------------------------------------ #
    async def kpis(self) -> dict[str, Any]:
        invoices = await self._revenue_invoices()
        payments = await self._payments_in()
        expenses = await self._expenses()
        orders = await self._orders()

        total_invoiced = sum(float(i.amount_total or 0) for i in invoices)
        total_collected = sum(float(p.amount or 0) for p in payments)
        total_expenses = sum(float(e.amount or 0) for e in expenses)
        outstanding = max(total_invoiced - total_collected, 0.0)

        confirmed_orders = [o for o in orders if o.status == "confirmed"]
        draft_orders = [o for o in orders if o.status == "draft"]

        # Reste à livrer (commandes confirmées non livrées)
        pending_delivery = sum(
            max(
                sum(float(l.quantity_ordered or 0) for l in o.lines)
                - sum(float(l.quantity_delivered or 0) for l in o.lines),
                0.0,
            )
            for o in confirmed_orders
        )

        return {
            "total_invoiced": total_invoiced,
            "total_collected": total_collected,
            "total_expenses": total_expenses,
            "cash_flow": total_collected - total_expenses,
            "outstanding": outstanding,
            "invoice_count": len(invoices),
            "orders_total": len(orders),
            "orders_confirmed": len(confirmed_orders),
            "orders_draft": len(draft_orders),
            "pending_delivery_qty": pending_delivery,
            "gross_margin": total_invoiced - total_expenses,
        }

    # ------------------------------------------------------------------ #
    # Tendance mensuelle (CA facturé / encaissé / dépenses)
    # ------------------------------------------------------------------ #
    async def sales_trend(self, months: int = 6) -> list[dict[str, Any]]:
        months = max(1, min(months, 24))
        keys = _last_months(months)
        start = date.fromisoformat(f"{keys[0]}-01")

        invoices = [
            i for i in await self._revenue_invoices()
            if i.invoice_date and i.invoice_date >= start
        ]
        payments = [
            p for p in await self._payments_in()
            if p.payment_date and p.payment_date >= start
        ]
        expenses = [
            e for e in await self._expenses()
            if e.expense_date and e.expense_date >= start
        ]

        buckets = {
            k: {"month": k, "invoiced": 0.0, "collected": 0.0, "expenses": 0.0}
            for k in keys
        }
        for i in invoices:
            buckets[_month_key(i.invoice_date)]["invoiced"] += float(i.amount_total or 0)
        for p in payments:
            buckets[_month_key(p.payment_date)]["collected"] += float(p.amount or 0)
        for e in expenses:
            if e.expense_date:
                buckets[_month_key(e.expense_date)]["expenses"] += float(e.amount or 0)
        return [buckets[k] for k in keys]

    # ------------------------------------------------------------------ #
    # Top produits (par CA facturé)
    # ------------------------------------------------------------------ #
    async def top_products(self, limit: int = 10) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 50))
        invoice_ids = (await self.session.execute(
            select(Invoice.id).where(Invoice.status.in_(_REVENUE_STATUSES))
        )).scalars().all()
        if not invoice_ids:
            return []

        lines = (await self.session.execute(
            select(InvoiceLine, Product.name, ProductCategory.name)
            .join(Product, Product.id == InvoiceLine.product_id, isouter=True)
            .join(ProductCategory, ProductCategory.id == Product.category_id, isouter=True)
            .where(InvoiceLine.invoice_id.in_(invoice_ids))
        )).all()

        agg: dict[str, dict[str, Any]] = {}
        for line, product_name, category_name in lines:
            label = product_name or line.description or "Non catégorisé"
            item = agg.setdefault(
                label,
                {"product": label, "category": category_name or "—",
                 "revenue": 0.0, "quantity": 0.0},
            )
            item["revenue"] += float(line.subtotal or 0)
            item["quantity"] += float(line.quantity or 0)

        return sorted(agg.values(), key=lambda x: -x["revenue"])[:limit]

    # ------------------------------------------------------------------ #
    # Top clients
    # ------------------------------------------------------------------ #
    async def top_partners(self, limit: int = 10) -> list[dict[str, Any]]:
        limit = max(1, min(limit, 50))
        invoices = await self._revenue_invoices()
        if not invoices:
            return []

        partner_ids = {i.partner_id for i in invoices}
        names: dict[int, str] = {}
        if partner_ids:
            rows = (await self.session.execute(
                select(Partner.id, Partner.name).where(Partner.id.in_(partner_ids))
            )).all()
            names = {pid: name for pid, name in rows}

        agg: dict[int, dict[str, Any]] = {}
        for i in invoices:
            item = agg.setdefault(i.partner_id, {
                "partner": names.get(i.partner_id, f"#{i.partner_id}"),
                "revenue": 0.0,
                "invoice_count": 0,
            })
            item["revenue"] += float(i.amount_total or 0)
            item["invoice_count"] += 1

        return sorted(agg.values(), key=lambda x: -x["revenue"])[:limit]

    # ------------------------------------------------------------------ #
    # Répartition par statut de facture
    # ------------------------------------------------------------------ #
    async def invoice_status(self) -> list[dict[str, Any]]:
        invoices = await self._all_invoices()
        agg: dict[str, dict[str, Any]] = {}
        for i in invoices:
            item = agg.setdefault(
                i.status, {"status": i.status, "count": 0, "amount": 0.0}
            )
            item["count"] += 1
            item["amount"] += float(i.amount_total or 0)
        return sorted(agg.values(), key=lambda x: -x["amount"])

    # ------------------------------------------------------------------ #
    # Encaissements par mode de paiement
    # ------------------------------------------------------------------ #
    async def payments_by_method(self) -> list[dict[str, Any]]:
        payments = await self._payments_in()
        agg: dict[str, dict[str, Any]] = {}
        for p in payments:
            item = agg.setdefault(
                p.method, {"method": p.method, "amount": 0.0, "count": 0}
            )
            item["amount"] += float(p.amount or 0)
            item["count"] += 1
        return sorted(agg.values(), key=lambda x: -x["amount"])

    # ------------------------------------------------------------------ #
    # Dépenses par catégorie
    # ------------------------------------------------------------------ #
    async def expenses_by_category(self) -> list[dict[str, Any]]:
        expenses = await self._expenses()
        agg: dict[str, dict[str, Any]] = {}
        for e in expenses:
            item = agg.setdefault(
                e.category, {"category": e.category, "amount": 0.0, "count": 0}
            )
            item["amount"] += float(e.amount or 0)
            item["count"] += 1
        return sorted(agg.values(), key=lambda x: -x["amount"])
