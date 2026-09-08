"""Schémas du module Stock."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class WarehouseCreate(BaseModel):
    name: str
    code: str | None = None
    warehouse_type: str = "warehouse"
    address: dict[str, Any] = Field(default_factory=dict)


class WarehouseRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    code: str | None = None
    warehouse_type: str
    is_active: bool


class StockLevelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    warehouse_id: int
    product_id: int
    quantity_on_hand: float
    quantity_reserved: float
    quantity_incoming: float
    available: float


class MovementCreate(BaseModel):
    movement_type: str = "inbound"
    warehouse_id: int
    target_warehouse_id: int | None = None
    product_id: int
    quantity: float
    unit_cost: float | None = None
    reference_document: str | None = None
    reference_id: int | None = None
    notes: str | None = None


class MovementRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    movement_type: str
    warehouse_id: int
    target_warehouse_id: int | None = None
    product_id: int
    quantity: float
    unit_cost: float | None = None
    created_at: datetime