"""
Modèle Compte comptable (plan comptable OHADA/SYSCOHADA).

Le plan complet (637 comptes, classes 1 à 9) est chargé via le seed
``app.modules.accounting.data.ohada_chart``.
"""

from __future__ import annotations

from sqlalchemy import Boolean, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin


class Account(Base, TenantMixin):
    """Compte du plan comptable (multi-entreprise, isolé par ``company_id``)."""

    code: Mapped[str] = MappedColumn(String(10), index=True)
    name: Mapped[str] = MappedColumn(String(250))
    #: 1..9 — classe OHADA
    class_no: Mapped[str] = MappedColumn(String(1), index=True)
    #: Type fonctionnel — sert aux écritures automatiques & états financiers
    account_type: Mapped[str] = MappedColumn(
        String(30),
        default="asset",
        index=True,
    )
    #: Nom technique stable pour retrouver le compte depuis le code métier
    #: (ex. ``customers``, ``tax_collected``, ``bank``…)
    technical_name: Mapped[str] = MappedColumn(String(50), default="")
    #: Compte de regroupement (parent) — pas utilisé directement en écriture
    is_group: Mapped[bool] = MappedColumn(Boolean, default=False)
    #: Actif / ouvert aux écritures
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)
    #: Niveau dans la hiérarchie (1 chiffre = racine, 2-3 = sous-compte…)
    level: Mapped[int] = MappedColumn(Integer, default=1)

    __table_args__ = (
        UniqueConstraint("company_id", "code", name="uq_account_company_code"),
    )

    def __repr__(self) -> str:
        return f"<Account {self.code} {self.name}>"


__all__ = ["Account"]