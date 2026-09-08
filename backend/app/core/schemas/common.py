"""Schémas communs — pagination, réponses génériques."""
from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class PaginationParams(BaseModel):
    """Paramètres de pagination pour les listes."""

    skip: int = Field(0, ge=0, description="Nombre d'éléments à ignorer")
    limit: int = Field(100, ge=1, le=1000, description="Nombre maximum d'éléments")


class PaginatedResponse(BaseModel, Generic[T]):
    """Réponse paginée générique."""

    items: list[T]
    total: int
    skip: int
    limit: int
    has_more: bool

    @property
    def total_pages(self) -> int:
        return max(1, (self.total + self.limit - 1) // self.limit)
