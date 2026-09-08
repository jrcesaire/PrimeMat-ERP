"""
Modèle Exercice comptable (FiscalYear).

Un exercice délimite la période des écritures (date de début / de fin) et
son état (ouvert / clôturé).
"""

from __future__ import annotations

from datetime import date

from sqlalchemy import Date, String
from sqlalchemy.orm import Mapped, MappedColumn

from app.core.database import Base, TenantMixin


class FiscalYear(Base, TenantMixin):
    """Exercice comptable d'une entreprise."""

    name: Mapped[str] = MappedColumn(String(50))
    start_date: Mapped[date] = MappedColumn(Date, nullable=False)
    end_date: Mapped[date] = MappedColumn(Date, nullable=False)
    #: ``open`` | ``closed``
    status: Mapped[str] = MappedColumn(String(10), default="open", index=True)

    def __repr__(self) -> str:
        return f"<FiscalYear {self.name} ({self.start_date} → {self.end_date})>"


__all__ = ["FiscalYear"]