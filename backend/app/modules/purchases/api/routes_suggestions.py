"""
API Routes Suggestions — recherche/fournisseurs pour la saisie.

    GET /purchases/suggestions?query=&category_id=&product_id=&warehouse_id=
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep
from app.core.dependencies.permissions import require_permission
from app.modules.purchases.schemas import PriceHistoryEntry, SupplierSuggest
from app.modules.purchases.services.supplier_service import SupplierService

router = APIRouter()

require_view = require_permission("purchase", "view")


# ------------------------------------------------------------------ #
# Suggestions
# ------------------------------------------------------------------ #
@router.get("/suggestions", response_model=list[SupplierSuggest])
async def suggest_products(
    session: SessionDep,
    query: str | None = None,
    category_id: int | None = None,
    product_id: int | None = None,
    warehouse_id: int | None = None,
    _: None = Depends(require_view),
):
    """Retourne une liste de fournisseurs/tendance de prix.

    Si ``category_id`` est fourni, on utilise le tri par note de la
    suggestion de catégorie (``suggest_for_category``). Sinon, un simple
    rattachement par recherche textuelle (``query``) est proposé.
    ``warehouse_id`` est retenu pour la compatibilité avec la couche
    frontend (il n'influence pas la sélection des fournisseurs).
    """
    service = SupplierService(session)

    if category_id is not None:
        return await service.suggest_for_category(
            category_id=category_id, product_id=product_id
        )

    if not query:
        # Aucun critère : retour vide (frontend peut afficher une zone
        # de recherche vide).
        return []

    suppliers = await service.list_suppliers(search=query, limit=100)

    # Derniers prix connus par fournisseur pour le produit demandé.
    last_prices: dict[int, float] = {}
    if product_id is not None:
        history = await service.price_history(product_id=product_id)
        for entry in history:
            if entry.supplier_id is not None and entry.supplier_id not in last_prices:
                last_prices[entry.supplier_id] = float(entry.unit_price)

    return [
        SupplierSuggest(
            id=s.id,
            name=s.name,
            rating=s.rating,
            delivery_days=s.delivery_days,
            last_price=last_prices.get(s.id),
        )
        for s in suppliers
    ]
