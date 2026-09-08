"""Modèle AuditLog — journalisation des actions sensibles."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base


class AuditLog(Base):
    """
    Journal d'audit pour les actions sensibles.

    Capture : utilisateur, entreprise, action, entité, ancien/nouveau
    état, IP, user-agent.

    Chaque entrée est immuable.
    """

    id: Mapped[int] = MappedColumn(Integer, primary_key=True, autoincrement=True)

    company_id: Mapped[int | None] = MappedColumn(
        Integer, ForeignKey("companies.id", ondelete="SET NULL"), nullable=True, index=True
    )
    user_id: Mapped[int | None] = MappedColumn(
        Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # Action et cible
    action: Mapped[str] = MappedColumn(String(100), nullable=False, index=True)
    entity_type: Mapped[str] = MappedColumn(String(100), nullable=False, index=True)
    entity_id: Mapped[int | None] = MappedColumn(Integer, nullable=True)

    # Avant / Après
    old_values: Mapped[dict[str, Any] | None] = MappedColumn(JSON, default=None)
    new_values: Mapped[dict[str, Any] | None] = MappedColumn(JSON, default=None)

    # Contexte technique
    ip_address: Mapped[str | None] = MappedColumn(String(45), default=None)
    user_agent: Mapped[str | None] = MappedColumn(Text, default=None)

    created_at: Mapped[datetime] = MappedColumn(
        default=datetime.utcnow, nullable=False, index=True
    )

    # Relations
    user: Mapped["User | None"] = relationship("User", lazy="selectin")

    def __repr__(self) -> str:
        return f"<AuditLog {self.action} on {self.entity_type}:{self.entity_id}>"
