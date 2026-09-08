"""Modèle Currency — devises ISO 4217."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, Column, Integer, Numeric, String
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base


class Currency(Base):
    """
    Devise ISO 4217.

    Codes standard : XOF (Franc CFA), EUR (Euro), USD (Dollar), etc.
    """

    code: Mapped[str] = MappedColumn(String(3), primary_key=True)
    name: Mapped[str] = MappedColumn(String(50), nullable=False)
    symbol: Mapped[str] = MappedColumn(String(10), nullable=False)
    decimal_places: Mapped[int] = MappedColumn(Integer, default=2)
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    # Companies using this currency
    companies: Mapped[list["Company"]] = relationship(
        "Company",
        secondary="company_currencies",
        back_populates="currencies",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Currency {self.code} ({self.symbol})>"
