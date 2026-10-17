"""
Modèles OHADA — paramètres comptables pour l'Ouagadougou Common Charge System.

Ce module contient la configuration par pays (taux de change, exercice fiscal,
taux TVA par défaut) ainsi que la gestion de l'exercice comptable.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from sqlalchemy import (
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
)
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin


class OHADAParameter(Base, TenantMixin):
    """
    Paramètre OHADA par entreprise.

    Chaque entreprise peut avoir un ou plusieurs pays associés, chacun avec :
    - une devise
    - un taux de change par rapport à la devise de la société
    - la période d'exercice comptable (ouverture / clôture)
    - le taux TVA par défaut applicable à ce pays
    - le statut d'activation

    Notes :
    - la clé primaire est id
    - la contrainte d'unicité par entreprise et pays est gérée au niveau
      application (voir OHADAService.upsert)
    """

    __tablename__ = "ohada_parameters"

    id: Mapped[int] = MappedColumn(Integer, primary_key=True, autoincrement=True)

    company_id: Mapped[int] = MappedColumn(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    country_code: Mapped[str] = MappedColumn(
        String(2),
        index=True,
        default="BF",  # Burkina Faso par défaut
    )

    currency_code: Mapped[str] = MappedColumn(
        String(3),
        ForeignKey("currencies.code"),
        default="XOF",
    )

    rate_to_fx: Mapped[Optional[float]] = MappedColumn(
        Numeric(10, 6),
        default=600.0,
        doc="Taux de change par rapport à la devise de la société.",
    )

    fiscal_year_start: Mapped[Optional[date]] = MappedColumn(Date)
    fiscal_year_end: Mapped[Optional[date]] = MappedColumn(Date)

    tax_rate_percentage: Mapped[Optional[float]] = MappedColumn(
        Numeric(5, 2),
        default=0.0,
        doc="Taux TVA par défaut pour ce pays.",
    )

    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    # Relations
    company: Mapped["Company"] = relationship(
        "Company",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<OHADAParameter {self.company_id} {self.country_code} ({self.currency_code})>"
