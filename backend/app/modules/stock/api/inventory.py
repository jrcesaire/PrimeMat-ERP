"""
Endpoints API du module Stock — entrepôts, niveaux, mouvements.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_permission
from app.core.models.user import User
from app.modules.stock.models.inventory import (
    Warehouse,
    StockLevel,
    StockMovement,
)
from app.modules.stock.schemas import (
    MovementCreate,
    MovementRead,
    StockLevelRead,
    WarehouseCreate,
    WarehouseRead,
)
from app.modules.stock.services.stock_service import StockService

router = APIRouter()


@router.get("/warehouses", response_model=list[WarehouseRead])
async def list_warehouses(
    session: SessionDep,
    _: User = Depends(require_permission("warehouse", "view")),
):
    result = await session.execute(select(Warehouse).order_by(Warehouse.id))
    return list(result.scalars().all())


@router.post("/warehouses", response_model=WarehouseRead, status_code=status.HTTP_201_CREATED)
async def create_warehouse(
    body: WarehouseCreate,
    session: SessionDep,
    _: User = Depends(require_permission("warehouse", "create")),
):
    warehouse = Warehouse(**body.model_dump())
    session.add(warehouse)
    await session.commit()
    await session.refresh(warehouse)
    return warehouse


@router.get("/levels", response_model=list[StockLevelRead])
async def list_stock_levels(
    session: SessionDep,
    product_id: int | None = None,
    warehouse_id: int | None = None,
    _: User = Depends(require_permission("stock_level", "view")),
):
    stmt = select(StockLevel).order_by(StockLevel.id)
    if product_id:
        stmt = stmt.where(StockLevel.product_id == product_id)
    if warehouse_id:
        stmt = stmt.where(StockLevel.warehouse_id == warehouse_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/levels/available")
async def get_available(
    session: SessionDep,
    product_id: int,
    warehouse_id: int | None = None,
    _: User = Depends(require_permission("stock_level", "view")),
):
    service = StockService(session)
    available = await service.get_available_stock(product_id, warehouse_id)
    return {"product_id": product_id, "available": available}


@router.get("/movements", response_model=list[MovementRead])
async def list_movements(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    product_id: int | None = None,
    _: User = Depends(require_permission("stock_movement", "view")),
):
    stmt = select(StockMovement).offset(skip).limit(limit).order_by(StockMovement.id.desc())
    if product_id:
        stmt = stmt.where(StockMovement.product_id == product_id)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.post("/movements", response_model=MovementRead, status_code=status.HTTP_201_CREATED)
async def create_movement(
    body: MovementCreate,
    session: SessionDep,
    _: User = Depends(require_permission("stock_movement", "create")),
):
    """Enregistre un mouvement de stock (entrée, sortie, transfert...)."""
    service = StockService(session)
    return await service.record_movement(**body.model_dump())