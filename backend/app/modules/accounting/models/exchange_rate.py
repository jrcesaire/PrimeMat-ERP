"""
Modèle ExchangeRate — taux de change pour la conversion multi-devise.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, MappedColumn

from app.core.database import Base, TenantMixin


class ExchangeRate(Base, TenantMixin):
    """
    Taux de change entre deux devises.

    L'unicité est garantie par la contrainte `uq_exchange_rate_company_currency_pair`
    sur (company_id, base_currency, quote_currency).
    """

    __table_args__ = (
        UniqueConstraint(
            "company_id",
            "base_currency",
            "quote_currency",
            name="uq_exchange_rate_company_currency_pair",
        ),
    )

    base_currency: Mapped[str] = MappedColumn(
        String(3), index=True, nullable=False
    )
    quote_currency: Mapped[str] = MappedColumn(
        String(3), index=True, nullable=False
    )
    rate: Mapped[float] = MappedColumn(
        Numeric(18, 8), default=1.0, nullable=False
    )
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    def __repr__(self) -> str:
        return (
            f"<ExchangeRate {self.company_id} "
            f"{self.base_currency}->{self.quote_currency} "
            f"({self.rate})>"
        )
