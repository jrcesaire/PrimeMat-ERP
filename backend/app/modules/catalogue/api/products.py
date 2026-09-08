"""
Endpoints API du module Catalogue — produits, catégories, unités, tôles BAC.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.catalogue.models.product import (
    Product,
    ProductCategory,
    ProductUnit,
    UnitConversion,
)
from app.modules.catalogue.models.bac import BACSheet, BACCut
from app.modules.catalogue.schemas import (
    ProductCreate,
    ProductRead,
    ProductUpdate,
    ProductCategoryCreate,
    ProductCategoryRead,
    ProductUnitCreate,
    ProductUnitRead,
    UnitConversionCreate,
    UnitConversionRead,
    BACSheetCreate,
    BACSheetRead,
    BACCutCreate,
)
from app.modules.catalogue.services.product_service import CatalogueService

router = APIRouter()


@router.get("/products", response_model=list[ProductRead])
async def list_products(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    _: User = Depends(require_permission("product", "view")),
):
    result = await session.execute(
        select(Product).offset(skip).limit(limit).order_by(Product.id)
    )
    return list(result.scalars().all())


@router.post("/products", response_model=ProductRead, status_code=status.HTTP_201_CREATED)
async def create_product(
    session: SessionDep,
    body: ProductCreate,
    _: User = Depends(require_permission("product", "create")),
):
    service = CatalogueService(session)
    try:
        return await service.create_product(body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@router.get("/products/{product_id}", response_model=ProductRead)
async def get_product(
    session: SessionDep,
    product_id: int,
    _: User = Depends(require_permission("product", "view")),
):
    service = CatalogueService(session)
    product = await service.get_product(product_id)
    if product is None:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return product
@router.put("/products/{product_id}", response_model=ProductRead)
async def update_product(
    session: SessionDep,
    product_id: int,
    body: ProductUpdate,
    _: User = Depends(require_permission("product", "edit")),
):
    service = CatalogueService(session)
    try:
        product = await service.update_product(product_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    if product is None:
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return product


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    session: SessionDep,
    product_id: int,
    _: User = Depends(require_permission("product", "delete")),
):
    service = CatalogueService(session)
    if not await service.delete_product(product_id):
        raise HTTPException(status_code=404, detail="Produit introuvable")
    return None


# ------------------------------------------------------------------ #
# Catégories
# ------------------------------------------------------------------ #
@router.get("/categories", response_model=list[ProductCategoryRead])
async def list_categories(
    session: SessionDep,
    _: User = Depends(require_permission("category", "view")),
):
    result = await session.execute(
        select(ProductCategory).order_by(ProductCategory.id)
    )
    return list(result.scalars().all())


@router.get("/categories/tree")
async def get_category_tree(
    session: SessionDep,
    _: User = Depends(require_permission("category", "view")),
):
    """Arborescence des catégories avec mode de vente effectif résolu.

    - ``resolved_sale_mode`` : mode hérité (unit/length/dual)
    - ``sells_by_length`` : vrai si vente au mètre linéaire possible
    """
    service = CatalogueService(session)
    return await service.build_category_tree()


@router.post("/categories", response_model=ProductCategoryRead, status_code=status.HTTP_201_CREATED)
async def create_category(
    session: SessionDep,
    body: ProductCategoryCreate,
    _: User = Depends(require_permission("category", "create")),
):
    category = ProductCategory(**body.model_dump())
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return category


# ------------------------------------------------------------------ #
# Unités
# ------------------------------------------------------------------ #
@router.get("/units", response_model=list[ProductUnitRead])
async def list_units(
    session: SessionDep,
    _: User = Depends(require_permission("unit", "view")),
):
    result = await session.execute(select(ProductUnit).order_by(ProductUnit.id))
    return list(result.scalars().all())


@router.post("/units", response_model=ProductUnitRead, status_code=status.HTTP_201_CREATED)
async def create_unit(
    session: SessionDep,
    body: ProductUnitCreate,
    _: User = Depends(require_permission("unit", "create")),
):
    unit = ProductUnit(**body.model_dump())
    session.add(unit)
    await session.commit()
    await session.refresh(unit)
    return unit


@router.get("/units/conversions", response_model=list[UnitConversionRead])
async def list_conversions(
    session: SessionDep,
    _: User = Depends(require_permission("unit", "view")),
):
    result = await session.execute(select(UnitConversion).order_by(UnitConversion.id))
    return list(result.scalars().all())


@router.post("/units/conversions", response_model=UnitConversionRead, status_code=status.HTTP_201_CREATED)
async def create_conversion(
    session: SessionDep,
    body: UnitConversionCreate,
    _: User = Depends(require_permission("unit", "create")),
):
    conv = UnitConversion(**body.model_dump())
    session.add(conv)
    await session.commit()
    await session.refresh(conv)
    return conv
# ------------------------------------------------------------------ #
# Tôles BAC
# ------------------------------------------------------------------ #
@router.post("/bac-sheets", response_model=BACSheetRead, status_code=status.HTTP_201_CREATED)
async def create_bac_sheet(
    session: SessionDep,
    body: BACSheetCreate,
    _: User = Depends(require_permission("product", "edit")),
):
    service = CatalogueService(session)
    return await service.create_bac_sheet(body)


@router.get("/bac-sheets/{sheet_id}", response_model=BACSheetRead)
async def get_bac_sheet(
    session: SessionDep,
    sheet_id: int,
    _: User = Depends(require_permission("product", "view")),
):
    service = CatalogueService(session)
    sheet = await service.get_bac_sheet(sheet_id)
    if sheet is None:
        raise HTTPException(status_code=404, detail="Tôle BAC introuvable")
    return sheet


@router.post("/bac-sheets/{sheet_id}/cuts", status_code=status.HTTP_201_CREATED)
async def add_bac_cut(
    session: SessionDep,
    sheet_id: int,
    body: BACCutCreate,
    _: User = Depends(require_permission("product", "edit")),
):
    service = CatalogueService(session)
    cut = await service.add_bac_cut(sheet_id, body.model_dump())
    if cut is None:
        raise HTTPException(status_code=404, detail="Tôle BAC introuvable")
    return cut


@router.delete("/bac-sheets/cuts/{cut_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bac_cut(
    session: SessionDep,
    cut_id: int,
    _: User = Depends(require_permission("product", "edit")),
):
    service = CatalogueService(session)
    if not await service.delete_bac_cut(cut_id):
        raise HTTPException(status_code=404, detail="Coupe BAC introuvable")
    return None