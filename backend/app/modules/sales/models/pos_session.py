"""
Modèle PosSession — session de caisse (Point de Vente).

Une session représente l'ensemble des transactions comptoir sur une
période de 24 heures (cycle journalier). Elle encadre les ventes PoS
et permet le rapprochement financier quotidien.

Cycle de vie : open → closing → closed
"""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin
from app.shared.enums import PosSessionStatus

if TYPE_CHECKING:
    from app.core.models.company import Company
    from app.core.models.user import User


class PosSession(Base, TenantMixin):
    """Session de caisse journalière."""

    __tablename__ = "pos_sessions"

    # Référence unique de la session (ex: SESSION-20261025-001)
    reference: Mapped[str] = MappedColumn(String(40), unique=True, index=True)

    # Statut de la session
    status: Mapped[str] = MappedColumn(
        String(20),
        default=PosSessionStatus.OPEN.value,
        index=True,
    )

    # Heures configurables (défaut : 00:00 pour fermeture, 00:00 pour écriture comptable)
    closing_hour: Mapped[int] = MappedColumn(
        Integer, default=0, nullable=False
    )  # heure de fermeture automatique (0-23)
    accounting_write_up_hour: Mapped[int] = MappedColumn(
        Integer, default=0, nullable=False
    )  # heure d'écriture comptable / heure-valeur (0-23)

    # Solde
    initial_balance: Mapped[float] = MappedColumn(
        Numeric(14, 4), default=0, nullable=False
    )
    closing_balance: Mapped[float | None] = MappedColumn(
        Numeric(14, 4), nullable=True
    )

    # Timestamps
    opened_at: Mapped[datetime] = MappedColumn(
        DateTime, default=datetime.utcnow, nullable=False
    )
    closed_at: Mapped[datetime | None] = MappedColumn(DateTime, nullable=True)

    # Utilisateurs
    opened_by_id: Mapped[int | None] = MappedColumn(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    closed_by_id: Mapped[int | None] = MappedColumn(
        ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    notes: Mapped[str | None] = MappedColumn(Text)

    # Relations
    opened_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[opened_by_id], lazy="selectin"
    )
    closed_by: Mapped["User | None"] = relationship(
        "User", foreign_keys=[closed_by_id], lazy="selectin"
    )
    company: Mapped["Company"] = relationship("Company", lazy="selectin")

    def __repr__(self) -> str:  # pragma: no cover
        return f"<PosSession {self.reference} [{self.status}]>"