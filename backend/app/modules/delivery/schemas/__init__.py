"""Schémas Livraison."""
from __future__ import annotations

from datetime import date

from pydantic import BaseModel, ConfigDict


class DeliveryCutRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    quantity: float
    length: float


class DeliveryLineRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    product_id: int | None
    description: str | None
    quantity: float
    quantity_ordered: float
    unit: str | None
    sell_by_length: bool
    total_length: float
    cuts: list[DeliveryCutRead] = []


class DeliveryRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    reference: str
    order_id: int
    partner_id: int
    status: str
    delivery_date: date | None
    expected_date: date | None
    notes: str | None
    shipping_address: str | None
    lines: list[DeliveryLineRead] = []


class DeliveryFromOrder(BaseModel):
    """Body : créer un bon de livraison depuis une commande."""

    order_id: int
    expected_date: date | None = None
    notes: str | None = None


class DeliveryStatusUpdate(BaseModel):
    status: str
