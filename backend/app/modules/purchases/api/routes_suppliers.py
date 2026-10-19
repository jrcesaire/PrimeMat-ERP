"""
API Routes Fournisseurs — annuaire, catégories, notation et suggestions.

   GET    /purchases/suppliers
   GET    /purchases/suppliers/{supplier_id}
   PUT    /purchases/suppliers/{supplier_id}
   DELETE /purchases/suppliers/{supplier_id}
   GET    /purchases/suppliers/{supplier_id}/rating
   POST   /purchases/suppliers/{supplier_id}/rating
   GET    /purchases/suggestions?category_id=&product_id=
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_permission
from app.modules.crm.models.partner import Partner
from app.modules.purchases.schemas import (
    SupplierCreate,
    SupplierRead,
    SupplierSuggest,
    SupplierUpdate,
)
from app.modules.purchases.services.supplier_service import SupplierService

router = APIRouter()


def _require_view() -> None:
    return Depends(require_permission("purchase", "view"))


# ------------------------------------------------------------------ #
# Annuaire
# ------------------------------------------------------------------ #
@router.get("/suppliers", response_model=list[SupplierRead])
async def list_suppliers(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    search: str | None = None,
    category_id: int | None = None,
    is_active: bool | None = None,
    _: None = _require_view(),
):
    service = SupplierService(session)
    return await service.list_suppliers(
        skip=skip, limit=limit, search=search, category_id=category_id, is_active=is_active
    )


@router.get("/suppliers/{supplier_id}", response_model=SupplierRead)
async def get_supplier(
    supplier_id: int,
    session: SessionDep,
    _: None = _require_view(),
):
    service = SupplierService(session)
    supplier = await service.get_supplier(supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Fournisseur introuvable.")
    return supplier


@router.post(
    "/suppliers",
    response_model=SupplierRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_supplier(
    body: SupplierCreate,
    session: SessionDep,
    user = Depends(require_permission("purchase", "create")),
):
    service = SupplierService(session)
    supplier = await service.create_supplier(body, company_id=user.company_id)
    return supplier


@router.put("/suppliers/{supplier_id}", response_model=SupplierRead)
async def update_supplier(
    supplier_id: int,
    body: SupplierUpdate,
    session: SessionDep,
    _: None = Depends(require_permission("purchase", "edit")),
):
    service = SupplierService(session)
    try:
        supplier = await service.update_supplier(supplier_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if supplier is None:
        raise HTTPException(status_code=404, detail="Fournisseur introuvable.")
    return supplier


@router.delete("/suppliers/{supplier_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_supplier(
    supplier_id: int,
    session: SessionDep,
    _: None = Depends(require_permission("purchase", "delete")),
):
    service = SupplierService(session)
    try:
        await service.delete_supplier(supplier_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


# ------------------------------------------------------------------ #
# Évaluation
# ------------------------------------------------------------------ #
@router.get("/suppliers/{supplier_id}/rating")
async def get_supplier_rating(
    supplier_id: int,
    session: SessionDep,
    _: None = _require_view(),
) -> dict[str, float | None]:
    service = SupplierService(session)
    supplier = await service.get_supplier(supplier_id)
    if supplier is None:
        raise HTTPException(status_code=404, detail="Fournisseur introuvable.")
    return {"supplier_id": supplier.id, "rating": supplier.rating}


@router.post("/suppliers/{supplier_id}/rating", response_model=SupplierRead)
async def set_supplier_rating(
    supplier_id: int,
    body: dict[str, float],
    session: SessionDep,
    _: None = Depends(require_permission("purchase", "edit")),
):
    if "rating" not in body:
        raise HTTPException(status_code=400, detail="Champ 'rating' manquant (1-5).")
    rating = float(body["rating"])
    if not (1.0 <= rating <= 5.0):
        raise HTTPException(status_code=400, detail="La note doit être entre 1 et 5.")
    service = SupplierService(session)
    try:
        supplier = await service.set_rating(supplier_id, rating)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if supplier is None:
        raise HTTPException(status_code=404, detail="Fournisseur introuvable.")
    return supplier


# ------------------------------------------------------------------ #
# Suggestions BC (saisie intelligente)
# ------------------------------------------------------------------ #
@router.get("/suppliers/suggestions", response_model=list[SupplierSuggest])
async def suggest_suppliers(
    session: SessionDep,
    category_id: int | None = None,
    product_id: int | None = None,
    _: None = _require_view(),
):
    """Fournisseurs d'une catégorie, triés par note, avec dernier prix connu.

    ``product_id`` (optionnel) restreint les suggestions au produit demandé.
    """
    service = SupplierService(session)
    return await service.suggest_for_category(category_id=category_id, product_id=product_id)
