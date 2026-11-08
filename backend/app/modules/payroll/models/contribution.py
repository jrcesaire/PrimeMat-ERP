"""
Modèle Organisme de cotisation (ContributionRegister).

Adaptation de ``hr.contribution.register`` : chaque cotisation (CNPS,
caisse de retraite, mutuelle…) est rattachée à un organisme collecteur, ce
qui permet d'agréger les parts salariale et patronale par organisme pour la
déclaration sociale.
"""
from __future__ import annotations

from sqlalchemy import ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin


class ContributionRegister(Base, TenantMixin):
    """Organisme collecteur d'une cotisation (CNPS, caisse de retraite…)."""

    name: Mapped[str] = MappedColumn(String(120), nullable=False)
    code: Mapped[str] = MappedColumn(String(20), index=True)      # CNPS, RETRAITE...
    #: Compte de tiers du plan comptable (ex. 431000) pour la comptabilisation.
    account_code: Mapped[str | None] = MappedColumn(String(10))
    partner_id: Mapped[int | None] = MappedColumn(
        ForeignKey("partners.id", ondelete="SET NULL"), nullable=True
    )

    partner: Mapped["Partner | None"] = relationship("Partner", lazy="selectin")

    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_contribution_company_code"),
    )

    def __repr__(self) -> str:
        return f"<ContributionRegister {self.code}>"
