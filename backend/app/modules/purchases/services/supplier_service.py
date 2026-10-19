"""
Service Fournisseurs — annuaire, classification par catégories,
évaluation et suggestions pour la saisie des BC.

Les fournisseurs sont des ``Partner`` (``role`` = supplier / both) ;
la classification catégories et l'évaluation vivent dans le module Achats.
"""
from __future__ import annotations

import logging

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.modules.catalogue.models.product import Product, ProductSupplier
from app.modules.crm.models.partner import Partner, PartnerCategory
from app.modules.purchases.schemas import (
    PriceHistoryEntry,
    SupplierCreate,
    SupplierSuggest,
    SupplierUpdate,
)

logger = logging.getLogger(__name__)

ROLES_WITH_SUPPLIER = ("supplier", "both")


class SupplierService:
    """Gestion des fournisseurs (partenaires de type fournisseur)."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------ #
    # Lecture
    # ------------------------------------------------------------------ #
    async def list_suppliers(
        self,
        skip: int = 0,
        limit: int = 100,
        search: str | None = None,
        category_id: int | None = None,
        is_active: bool | None = True,
    ) -> list[Partner]:
        """Liste des fournisseurs, filtrable par recherche / catégorie."""
        stmt = select(Partner).options(selectinload(Partner.category_links)).where(
            Partner.role.in_(ROLES_WITH_SUPPLIER)
        )
        if search:
            like = f"%{search}%"
            stmt = stmt.where(Partner.name.ilike(like) | Partner.code.ilike(like))
        if is_active is not None:
            stmt = stmt.where(Partner.is_active.is_(is_active))
        if category_id is not None:
            stmt = stmt.where(
                Partner.id.in_(
                    select(PartnerCategory.partner_id).where(
                        PartnerCategory.category_id == category_id
                    )
                )
            )
        stmt = stmt.order_by(Partner.name).offset(skip).limit(limit)
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_supplier(self, supplier_id: int) -> Partner | None:
        stmt = (
            select(Partner)
            .options(selectinload(Partner.category_links))
            .where(Partner.id == supplier_id)
        )
        result = await self.session.execute(stmt)
        return result.scalars().first()

    # ------------------------------------------------------------------ #
    # Écriture
    # ------------------------------------------------------------------ #
    async def create_supplier(
        self, data: SupplierCreate, company_id: int
    ) -> Partner:
        supplier = Partner(
            name=data.name,
            code=data.code,
            role="supplier",
            phone=data.phone,
            email=data.email,
            website=data.website,
            tax_number=data.tax_number,
            registration_number=data.registration_number,
            payment_terms_days=data.payment_terms_days,
            is_active=data.is_active,
            rating=data.rating,
            delivery_days=data.delivery_days,
            company_id=company_id,
        )
        self.session.add(supplier)
        await self.session.flush()

        for category_id in data.category_ids:
            link = PartnerCategory(
                partner_id=supplier.id,
                category_id=category_id,
                company_id=company_id,
            )
            self.session.add(link)

        await self.session.commit()
        await self.session.refresh(supplier)
        return supplier

    async def update_supplier(
        self, supplier_id: int, data: SupplierUpdate
    ) -> Partner | None:
        supplier = await self.get_supplier(supplier_id)
        if supplier is None:
            return None

        for field in (
            "name", "code", "phone", "email", "website", "tax_number",
            "registration_number", "payment_terms_days", "is_active",
            "rating", "delivery_days",
        ):
            value = getattr(data, field, None)
            if value is not None:
                setattr(supplier, field, value)

        if data.category_ids is not None:
            # Remplacement intégral de la classification
            supplier.category_links.clear()
            await self.session.flush()
            for category_id in data.category_ids:
                self.session.add(
                    PartnerCategory(
                        partner_id=supplier.id,
                        category_id=category_id,
                        company_id=supplier.company_id,
                    )
                )

        await self.session.commit()
        await self.session.refresh(supplier)
        return supplier

    async def set_rating(self, supplier_id: int, rating: float) -> Partner | None:
        """Évaluation rapide 1-5 (endpoint dédié du PRD)."""
        supplier = await self.get_supplier(supplier_id)
        if supplier is None:
            return None
        supplier.rating = rating
        await self.session.commit()
        await self.session.refresh(supplier)
        return supplier


    # ------------------------------------------------------------------ #
    # Suggestions BC (saisie intelligente)
    # ------------------------------------------------------------------ #
    async def suggest_for_category(
        self, category_id: int, product_id: int | None = None
    ) -> list[SupplierSuggest]:
        """Fournisseurs d'une catégorie, triés par note, avec dernier prix."""
        suppliers = await self.list_suppliers(category_id=category_id, limit=200)

        last_prices: dict[int, float] = {}
        if product_id is not None:
            last_prices = await self._last_prices_by_supplier(product_id)

        suggestions: list[SupplierSuggest] = []
        for s in suppliers:
            suggestions.append(
                SupplierSuggest(
                    id=s.id,
                    name=s.name,
                    rating=float(s.rating) if s.rating is not None else None,
                    delivery_days=s.delivery_days,
                    last_price=last_prices.get(s.id),
                )
            )
        # Tri : note décroissante d'abord, puis prix connu croissant
        suggestions.sort(
            key=lambda x: (
                -(x.rating or 0),
                x.last_price if x.last_price is not None else float("inf"),
            ),
        )
        return suggestions

    async def delete_supplier(self, supplier_id: int) -> Partner | None:
        """Suppression logique du fournisseur (``is_active = False``)."""
        supplier = await self.get_supplier(supplier_id)
        if supplier is None:
            return None
        supplier.is_active = False
        await self.session.commit()
        await self.session.refresh(supplier)
        return supplier

    async def price_history(
        self, product_id: int, limit: int = 10
    ) -> list[PriceHistoryEntry]:
        """Derniers prix d'achat connus pour un produit.

        Sources : lignes de BC historiques (du plus récent au plus ancien),
        complétées par le prix d'achat du catalogue et les liens fournisseur.
        """
        from app.modules.purchases.models import PurchaseOrder, PurchaseOrderLine

        entries: list[PriceHistoryEntry] = []

        # 1. Historique BC (le plus récent d'abord)
        stmt = (
            select(PurchaseOrderLine, PurchaseOrder)
            .join(PurchaseOrder, PurchaseOrderLine.order_id == PurchaseOrder.id)
            .where(
                PurchaseOrderLine.product_id == product_id,
                PurchaseOrder.status.notin_(("draft", "cancelled")),
            )
            .order_by(PurchaseOrder.order_date.desc(), PurchaseOrderLine.id.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        for line, order in result.all():
            entries.append(
                PriceHistoryEntry(
                    supplier_id=order.supplier_id,
                    supplier_name=order.supplier.name if order.supplier else None,
                    unit_price=float(line.unit_price),
                    order_date=order.order_date,
                    source="po",
                )
            )

        # 2. Repli : prix catalogue (produit + liens fournisseur)
        if not entries:
            product = await self.session.get(Product, product_id)
            if product is not None and product.purchase_price:
                entries.append(
                    PriceHistoryEntry(
                        unit_price=float(product.purchase_price),
                        source="catalogue",
                    )
                )
            links = (
                await self.session.execute(
                    select(ProductSupplier).where(
                        ProductSupplier.product_id == product_id,
                        ProductSupplier.is_active.is_(True),
                        ProductSupplier.purchase_price.is_not(None),
                    )
                )
            ).scalars().all()
            for link in links:
                entries.append(
                    PriceHistoryEntry(
                        supplier_id=link.supplier_id,
                        supplier_name=link.supplier.name if link.supplier else None,
                        unit_price=float(link.purchase_price),
                        source="catalogue",
                    )
                )

        return entries

    async def _last_prices_by_supplier(self, product_id: int) -> dict[int, float]:
        """Dernier prix payé par produit et par fournisseur (via les BC)."""
        from app.modules.purchases.models import PurchaseOrder, PurchaseOrderLine

        stmt = (
            select(PurchaseOrderLine, PurchaseOrder)
            .join(PurchaseOrder, PurchaseOrderLine.order_id == PurchaseOrder.id)
            .where(
                PurchaseOrderLine.product_id == product_id,
                PurchaseOrder.status.notin_(("draft", "cancelled")),
            )
            .order_by(PurchaseOrder.order_date.desc(), PurchaseOrderLine.id.desc())
        )
        result = await self.session.execute(stmt)
        prices: dict[int, float] = {}
        for line, order in result.all():
            if order.supplier_id not in prices:
                prices[order.supplier_id] = float(line.unit_price)
        return prices

