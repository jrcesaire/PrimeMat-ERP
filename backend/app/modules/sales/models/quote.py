"""
Modèles Devis (Quote) — avec lignes multi-longueurs pour tôles BAC.

Formule ligne BAC ::
    Montant = Σ(quantité × longueur × prix unitaire)
"""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin


class Quote(Base, TenantMixin):
    """Devis client."""

    reference: Mapped[str] = MappedColumn(String(30), unique=True, index=True)
    partner_id: Mapped[int] = MappedColumn(
        ForeignKey("partners.id"), nullable=False, index=True
    )
    site_id: Mapped[int | None] = MappedColumn(ForeignKey("sites.id"), nullable=True)

    status: Mapped[str] = MappedColumn(String(20), default="draft", index=True)
    quote_date: Mapped[date] = MappedColumn(Date, default=date.today)
    valid_until: Mapped[date | None] = MappedColumn(Date)

    currency_code: Mapped[str] = MappedColumn(String(3), default="XOF")

    amount_untaxed: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    discount_amount: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    tax_amount: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    amount_total: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)

    # Marge prévisionnelle
    expected_cost: Mapped[float | None] = MappedColumn(Numeric(14, 4))
    expected_margin: Mapped[float | None] = MappedColumn(Numeric(14, 4))

    notes: Mapped[str | None] = MappedColumn(String(2000))
    terms: Mapped[str | None] = MappedColumn(String(2000))
    metadata_json: Mapped[dict[str, Any]] = MappedColumn(JSON, default=dict)

    lines: Mapped[list["QuoteLine"]] = relationship(
        "QuoteLine", back_populates="quote",
        cascade="all, delete-orphan", lazy="selectin",
    )

    partner: Mapped["Partner"] = relationship("Partner")
    company: Mapped["Company"] = relationship("Company")

    def __repr__(self) -> str:
        return f"<Quote {self.reference} [{self.status}]>"


class QuoteLine(Base, TenantMixin):
    """
    Ligne de devis.

    - Standard : ``quantity × unit_price``
    - Tôle BAC : ``sell_by_length=True`` → ``cuts`` (multi-longueurs)
    """

    quote_id: Mapped[int] = MappedColumn(
        ForeignKey("quotes.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_id: Mapped[int | None] = MappedColumn(
        ForeignKey("products.id"), nullable=True
    )

    description: Mapped[str | None] = MappedColumn(String(500))
    quantity: Mapped[float] = MappedColumn(Numeric(14, 4), default=1)
    unit: Mapped[str | None] = MappedColumn(String(20))

    sell_by_length: Mapped[bool] = MappedColumn(Boolean, default=False)
    unit_price: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    discount_percent: Mapped[float] = MappedColumn(Numeric(6, 2), default=0)

    total_length: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    subtotal: Mapped[float] = MappedColumn(Numeric(14, 4), default=0)
    position: Mapped[int] = MappedColumn(Integer, default=0)

    quote: Mapped["Quote"] = relationship("Quote", back_populates="lines")
    cuts: Mapped[list["QuoteLineCut"]] = relationship(
        "QuoteLineCut", back_populates="line",
        cascade="all, delete-orphan", lazy="selectin",
    )

    def compute_totals(self) -> None:
        """Calcule les totaux de la ligne (standard ou BAC multi-longueurs)."""
        price = float(self.unit_price or 0)
        if self.sell_by_length and self.cuts:
            total_len = sum(float(c.quantity) * float(c.length) for c in self.cuts)
            self.total_length = total_len
            raw = sum(
                float(c.quantity) * float(c.length) * float(c.unit_price or price)
                for c in self.cuts
            )
            self.subtotal = raw
        else:
            qty = float(self.quantity or 0)
            self.total_length = qty
            raw = qty * price
            self.subtotal = raw
        if self.discount_percent:
            self.subtotal = float(self.subtotal) * (
                1 - float(self.discount_percent) / 100
            )


class QuoteLineCut(Base):
    """Sous-ligne de coupe BAC d'une ligne de devis (quantité × longueur)."""

    __tablename__ = "quote_line_cuts"

    id: Mapped[int] = MappedColumn(Integer, primary_key=True, autoincrement=True)
    line_id: Mapped[int] = MappedColumn(
        ForeignKey("quote_lines.id", ondelete="CASCADE"), nullable=False, index=True
    )
    quantity: Mapped[float] = MappedColumn(Numeric(14, 4), default=1)
    length: Mapped[float] = MappedColumn(Numeric(12, 4), nullable=False)
    unit_price: Mapped[float | None] = MappedColumn(Numeric(14, 4))

    line: Mapped["QuoteLine"] = relationship("QuoteLine", back_populates="cuts")