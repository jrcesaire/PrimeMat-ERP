"""
Modèle Site (chantier).

Un client peut posséder plusieurs chantiers.  Un chantier peut être
associé à des devis, commandes, livraisons, factures, paiements.
"""
from __future__ import annotations

from datetime import date
from typing import Any

from sqlalchemy import JSON, Boolean, Date, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin


class Site(Base, TenantMixin):
    """
    Chantier appartenant à un client.

    Exemple : Client 'Entreprise ABC' → chantiers 'Cocody', 'Bingerville', 'Yopougon'.
    """

    partner_id: Mapped[int] = MappedColumn(
        ForeignKey("partners.id", ondelete="CASCADE"), nullable=False
    )
    name: Mapped[str] = MappedColumn(String(200), nullable=False)
    code: Mapped[str | None] = MappedColumn(String(30), index=True)

    address: Mapped[dict[str, Any]] = MappedColumn(JSON, default=dict)
    city: Mapped[str | None] = MappedColumn(String(100))
    region: Mapped[str | None] = MappedColumn(String(100))
    country: Mapped[str] = MappedColumn(String(2), default="CI")

    start_date: Mapped[date | None] = MappedColumn(Date)
    end_date: Mapped[date | None] = MappedColumn(Date)
    budget: Mapped[float | None] = MappedColumn(Numeric(14, 4))
    status: Mapped[str] = MappedColumn(String(20), default="active")

    manager_name: Mapped[str | None] = MappedColumn(String(100))
    manager_phone: Mapped[str | None] = MappedColumn(String(50))
    description: Mapped[str | None] = MappedColumn(String(1000))

    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    partner: Mapped["Partner"] = relationship("Partner", back_populates="sites")

    def __repr__(self) -> str:
        return f"<Site {self.code or self.name} (partner={self.partner_id})>"