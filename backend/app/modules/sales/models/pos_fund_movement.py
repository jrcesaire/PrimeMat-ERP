"""
Modèle PosFundMovement — mouvement de fonds manuel en caisse (Point de Vente).

Permet d'enregistrer les entrées et sorties de fonds non liées à une vente
(dépôt de monnaie, retrait pour changement, etc.) afin de tenir un journal
des mouvements de caisse conforme au PRD §4.1.2 §5.

Les colonnes ``id``, ``company_id``, ``created_at``, ``updated_at``,
``created_by`` et ``updated_by`` sont fournies par ``TenantMixin``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import (
    ForeignKey,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin
from app.shared.enums import PosFundMovementType

if TYPE_CHECKING:
    from app.core.models.company import Company
    from app.core.models.user import User


class PosFundMovement(Base, TenantMixin):
    """Mouvement de fonds manuel enregistré dans une session de caisse."""

    __tablename__ = "pos_fund_movements"

    # Type de mouvement : dépôt (entrée) ou retrait (sortie)
    movement_type: Mapped[str] = MappedColumn(
        String(20),
        nullable=False,
        index=True,
    )

    # Montant du mouvement (toujours positif, le sens est donné par movement_type)
    amount: Mapped[float] = MappedColumn(
        Numeric(14, 4),
        nullable=False,
    )

    # Libellé / motif du mouvement (ex: "Dépôt de monnaie", "Retrait pour change")
    label: Mapped[str] = MappedColumn(String(255), nullable=False)

    # Référence optionnelle d'une pièce justificative (ticket, n° de pièce, etc.)
    reference: Mapped[str | None] = MappedColumn(String(100), nullable=True)

    # Clés étrangères spécifiques
    session_id: Mapped[int] = MappedColumn(
        ForeignKey("pos_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    notes: Mapped[str | None] = MappedColumn(Text)

    # Relations
    session: Mapped["PosSession"] = relationship(
        "PosSession", lazy="selectin"
    )
    # ``created_by`` et ``company_id`` sont fournis par TenantMixin.
    # ``TenantMixin`` porte DEUX FK vers ``users`` (``created_by`` et
    # ``updated_by``) : sans ``foreign_keys`` explicite, SQLAlchemy ne peut pas
    # choisir le chemin de jointure et l'initialisation des mappers échoue
    # (AmbiguousForeignKeysError) — ce qui empêchait le démarrage de l'API.
    creator: Mapped["User | None"] = relationship(
        "User",
        foreign_keys="PosFundMovement.created_by",
        lazy="selectin",
    )
    company: Mapped["Company"] = relationship("Company", lazy="selectin")

    def __repr__(self) -> str:  # pragma: no cover
        return (
            f"<PosFundMovement {self.movement_type} "
            f"{self.amount} session={self.session_id}>"
        )
