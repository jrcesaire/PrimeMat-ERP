"""Modèle Tax — taxes et TVA configurables."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin
from app.shared.enums import TaxType


class Tax(Base, TenantMixin):
    """
    Taxe appliquée à un document (facture, devis, etc.).

    Exemples : TVA 19.25 %, TVA 5.5 %, Taxe intérieure 0 %, Exonération légale.
    """

    __tablename__ = "taxes"

    name: Mapped[str] = MappedColumn(String(100), nullable=False)
    code: Mapped[str] = MappedColumn(String(20), nullable=True, index=True)
    rate: Mapped[float] = MappedColumn(Numeric(10, 4), default=0)
    type: Mapped[str] = MappedColumn(String(20), default=TaxType.PERCENTAGE.value)
    is_exempt: Mapped[bool] = MappedColumn(Boolean, default=False)
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)
    is_default: Mapped[bool] = MappedColumn(Boolean, default=False)

    parent_id: Mapped[int | None] = MappedColumn(
        Integer, ForeignKey("taxes.id"), nullable=True
    )

    # Relations
    company_id: Mapped[int] = MappedColumn(  # type: ignore[assignment]
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company: Mapped["Company"] = relationship("Company", back_populates="taxes")

    children: Mapped[list["Tax"]] = relationship(
        "Tax",
        backref="parent_rel",
        remote_side="Tax.id",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Tax {self.name} ({self.rate}%)>"
