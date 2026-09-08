"""
Modèle Journal comptable (Journal).

Codes standards SYSCOHADA : ACH (achats), VTE (ventes), BAN (banque),
CAI (caisse), PAY (paiements), OD (opérations diverses).
"""

from __future__ import annotations

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, MappedColumn

from app.core.database import Base, TenantMixin

JOURNAL_TYPES = (
    "purchase",
    "sale",
    "bank",
    "cash",
    "payment",
    "misc",
)


class Journal(Base, TenantMixin):
    """Journal comptable d'une entreprise."""

    code: Mapped[str] = MappedColumn(String(10), index=True)
    name: Mapped[str] = MappedColumn(String(100))
    journal_type: Mapped[str] = MappedColumn(String(20))
    is_active: Mapped[bool] = MappedColumn(default=True)

    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_journal_company_code"),
    )

    def __repr__(self) -> str:
        return f"<Journal {self.code} {self.name}>"


__all__ = ["Journal", "JOURNAL_TYPES"]