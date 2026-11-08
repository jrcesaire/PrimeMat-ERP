"""
Modèles Immobilisations — ``FixedAsset`` et ``Depreciation`` (Phase 2 PRD).

- ``FixedAsset``   : immobilisation amortissable, rattachée à un compte du
  plan OHADA (ex. 245 matériel de transport) et à son compte d'amortissement
  cumulé (ex. 284) ;
- ``Depreciation`` : échéance du plan d'amortissement (une ligne par période),
  avec la dotation, le cumul et la valeur nette comptable après la période.

Comptabilisation SYSCOHADA : ``D 681 (dotations aux amortissements
d'exploitation) / C 28x (amortissements des immobilisations)``.

Méthodes supportées :

- **linéaire** : dotation constante = base amortissable / durée ;
- **dégressif** : taux accéléré appliqué à la valeur nette comptable, avec
  basculement automatique en linéaire sur la durée restante dès que le taux
  linéaire résiduel devient supérieur au taux dégressif.
"""

from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin

__all__ = ["FixedAsset", "Depreciation"]


class FixedAsset(Base, TenantMixin):
    """Immobilisation amortissable d'une entreprise."""

    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_fixed_asset_company_code"),
        CheckConstraint(
            "acquisition_cost >= 0", name="ck_fixed_asset_cost_nonnegative"
        ),
        CheckConstraint(
            "residual_value >= 0", name="ck_fixed_asset_residual_nonnegative"
        ),
        CheckConstraint(
            "useful_life_years > 0", name="ck_fixed_asset_life_positive"
        ),
        CheckConstraint(
            "method IN ('linear', 'declining')", name="ck_fixed_asset_method_valid"
        ),
        CheckConstraint(
            "periodicity IN ('annual', 'monthly')",
            name="ck_fixed_asset_periodicity_valid",
        ),
        CheckConstraint(
            "status IN ('draft', 'active', 'disposed')",
            name="ck_fixed_asset_status_valid",
        ),
    )

    #: Code interne unique par entreprise (ex. ``IMM-2026-001``).
    code: Mapped[str] = MappedColumn(String(30), index=True)
    name: Mapped[str] = MappedColumn(String(200))
    #: Catégorie fonctionnelle : ``incorporeal``, ``land``, ``building``,
    #: ``equipment``, ``financial``, ``other``.
    category: Mapped[str] = MappedColumn(String(20), default="equipment", index=True)

    #: Compte d'immobilisation du plan OHADA (ex. ``245``).
    asset_account: Mapped[str] = MappedColumn(String(10), index=True)
    #: Compte d'amortissement cumulé (ex. ``284``).
    depreciation_account: Mapped[str] = MappedColumn(String(10))
    #: Compte de dotation (``681000`` exploitation, ``686000`` financier).
    expense_account: Mapped[str] = MappedColumn(String(10), default="681000")
    #: Journal des écritures d'amortissement (``OD`` par défaut).
    journal_code: Mapped[str] = MappedColumn(String(10), default="OD")

    acquisition_date: Mapped[date] = MappedColumn(Date, nullable=False, index=True)
    #: Mise en service : point de départ du plan d'amortissement.
    in_service_date: Mapped[date] = MappedColumn(Date, nullable=False)
    #: Valeur d'acquisition (coût d'entrée).
    acquisition_cost: Mapped[float] = MappedColumn(Numeric(16, 2), default=0)
    #: Valeur résiduelle non amortissable (défaut 0).
    residual_value: Mapped[float] = MappedColumn(Numeric(16, 2), default=0)
    #: Durée d'utilité en années.
    useful_life_years: Mapped[int] = MappedColumn(Integer, default=1)
    #: ``linear`` | ``declining``.
    method: Mapped[str] = MappedColumn(String(10), default="linear")
    #: ``annual`` | ``monthly`` (le dégressif n'accepte que l'annuel).
    periodicity: Mapped[str] = MappedColumn(String(10), default="annual")

    #: ``draft`` | ``active`` | ``disposed``.
    status: Mapped[str] = MappedColumn(String(10), default="draft", index=True)
    #: Date de cession / mise au rebut (statut ``disposed``).
    disposal_date: Mapped[date | None] = MappedColumn(Date, nullable=True)

    notes: Mapped[str | None] = MappedColumn(String(1000))

    depreciations: Mapped[list["Depreciation"]] = relationship(
        "Depreciation",
        back_populates="asset",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="Depreciation.period_index",
    )

    @property
    def depreciable_base(self) -> float:
        """Base amortissable = valeur d'acquisition − valeur résiduelle."""
        return max(
            float(self.acquisition_cost or 0) - float(self.residual_value or 0), 0.0
        )

    @property
    def is_declining(self) -> bool:
        return self.method == "declining"

    def __repr__(self) -> str:
        return f"<FixedAsset {self.code} {self.name} [{self.status}]>"


class Depreciation(Base, TenantMixin):
    """Échéance du plan d'amortissement d'une immobilisation."""

    __table_args__ = (
        UniqueConstraint(
            "asset_id", "period_index", name="uq_depreciation_asset_period"
        ),
        CheckConstraint(
            "status IN ('planned', 'posted')", name="ck_depreciation_status_valid"
        ),
    )

    asset_id: Mapped[int] = MappedColumn(
        ForeignKey("fixed_assets.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    #: Rang de l'échéance dans le plan (1 à n).
    period_index: Mapped[int] = MappedColumn(Integer, nullable=False)
    #: Date de clôture de la période amortie.
    period_date: Mapped[date] = MappedColumn(Date, nullable=False, index=True)

    #: Valeur nette comptable au début de la période.
    opening_value: Mapped[float] = MappedColumn(Numeric(16, 2), default=0)
    #: Dotation de la période.
    amount: Mapped[float] = MappedColumn(Numeric(16, 2), default=0)
    #: Cumul des dotations après cette période.
    accumulated: Mapped[float] = MappedColumn(Numeric(16, 2), default=0)
    #: Valeur nette comptable après cette période.
    net_value: Mapped[float] = MappedColumn(Numeric(16, 2), default=0)

    #: ``planned`` (à comptabiliser) | ``posted`` (comptabilisée).
    status: Mapped[str] = MappedColumn(String(10), default="planned", index=True)
    journal_entry_id: Mapped[int | None] = MappedColumn(
        Integer, nullable=True, index=True
    )
    posted_at: Mapped[datetime | None] = MappedColumn(DateTime, nullable=True)

    asset: Mapped["FixedAsset"] = relationship(
        "FixedAsset", back_populates="depreciations"
    )

    def __repr__(self) -> str:
        return (
            f"<Depreciation asset={self.asset_id} #{self.period_index} "
            f"{self.amount} [{self.status}]>"
        )
