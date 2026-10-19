"""
API Routes du module Achats (fournisseurs) — Endpoints publics.

   /purchases
   - Fournisseurs  : GET/POST /suppliers, /{id}, /{id}/category, /{id}/ratings
   - Demandes      : GET/POST /requests, /{id}, /{id}/{action}
   - Commandes     : GET/POST /orders, /{id}, /{id}/lines, /{id}/convert-from-request
   - Réceptions    : GET/POST /receptions, /{id}, /{id}/validate
   - Factures      : GET/POST /invoices, /{id}, /{id}/match, /{id}/post, /{id}/pay
   - Suggestions   : GET /suggestions?query=&product_id=&warehouse_id=
   - Rapprochement : GET /reconciliation?order_id=&invoice_id=

Paramètres : ``skip``/``limit`` pour la pagination, ``transaction_date``
pour filtrer les documents dont la date est comprise dans une plage.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.modules.purchases.api.routes_invoices import router as invoices_router
from app.modules.purchases.api.routes_orders import router as orders_router
from app.modules.purchases.api.routes_receptions import router as receptions_router
from app.modules.purchases.api.routes_reconciliation import (
    router as reconciliation_router,
)
from app.modules.purchases.api.routes_requests import router as requests_router
from app.modules.purchases.api.routes_suggestions import router as suggestions_router
from app.modules.purchases.api.routes_suppliers import router as suppliers_router

router = APIRouter()

router.include_router(suppliers_router)
router.include_router(requests_router)
router.include_router(orders_router)
router.include_router(receptions_router)
router.include_router(invoices_router)
router.include_router(suggestions_router)
router.include_router(reconciliation_router)

routers = [router]

__all__ = [
    "router",
    "routers",
    "suppliers_router",
    "requests_router",
    "orders_router",
    "receptions_router",
    "invoices_router",
    "suggestions_router",
    "reconciliation_router",
]

