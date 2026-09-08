"""Modèle Sequence — numérotation des documents."""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import JSON, Date, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin


class Sequence(Base, TenantMixin):
    """
    Séquence de numérotation pour les documents.

    Exemple : les factures d'une entreprise sont numérotées
    ``FA-2024-0001``, ``FA-2024-0002``, ...

    - ``model`` : type d'entité (invoice, quote, order, ...)
    - ``prefix`` / ``suffix`` : texte autour du numéro
    - ``number_padding`` : zéro-fill (0001 vs 1)
    - ``number_increment`` : pas de numérotation
    - ``reset`` : reset annuel (year, month) ou jamais
    """

    model: Mapped[str] = MappedColumn(String(50), nullable=False, index=True)
    name: Mapped[str] = MappedColumn(String(100), nullable=False)
    prefix: Mapped[str] = MappedColumn(String(50), default="", nullable=False)
    suffix: Mapped[str] = MappedColumn(String(50), default="", nullable=False)
    number_padding: Mapped[int] = MappedColumn(Integer, default=4)
    number_increment: Mapped[int] = MappedColumn(Integer, default=1)
    last_number: Mapped[int] = MappedColumn(Integer, default=0)
    reset: Mapped[str] = MappedColumn(String(20), default="never")  # never, year, month
    is_active: Mapped[bool] = MappedColumn(default=True)

    # Date ranges pour reset de numérotation
    date_ranges: Mapped[dict[str, Any] | None] = MappedColumn(JSON, default=dict)

    # Relations
    company_id: Mapped[int] = MappedColumn(  # type: ignore[assignment]
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    company: Mapped["Company"] = relationship("Company", back_populates="sequences")

    def __repr__(self) -> str:
        return f"<Sequence {self.model} ({self.prefix}{{last}}{self.suffix})>"


class SequenceDateRange(Base):
    """Plage de dates pour le reset de numérotation."""

    __tablename__ = "sequence_date_ranges"

    id: Mapped[int] = MappedColumn(Integer, primary_key=True, autoincrement=True)
    sequence_id: Mapped[int] = MappedColumn(
        ForeignKey("sequences.id", ondelete="CASCADE"), nullable=False
    )
    start_date: Mapped[date] = MappedColumn(Date, nullable=False)
    end_date: Mapped[date] = MappedColumn(Date, nullable=False)
    last_number: Mapped[int] = MappedColumn(Integer, default=0)
