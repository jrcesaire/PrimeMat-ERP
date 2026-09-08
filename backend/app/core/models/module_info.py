"""Modèle ModuleInfo — état des modules du système."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import JSON, Boolean, DateTime, Integer, String
from sqlalchemy.orm import Mapped, MappedColumn

from app.core.database import Base


class ModuleInfo(Base):
    """
    Métadonnées d'un module installé dans le système.

    Un module peut être :
    - ``not_installed`` → disponible mais pas encore installé
    - ``installed``     → tables créées, prêt à l'emploi
    - ``active``        → fonctionnel, les routes sont exposées
    - ``inactive``      → désactivé (les routes sont masquées)

    La configuration du module (paramètres clés/valeurs) est stockée
    dans la colonne ``config`` (JSON).
    """

    id: Mapped[int] = MappedColumn(Integer, primary_key=True, autoincrement=True)

    name: Mapped[str] = MappedColumn(String(50), unique=True, nullable=False, index=True)
    version: Mapped[str] = MappedColumn(String(20), nullable=False)
    status: Mapped[str] = MappedColumn(String(20), default="not_installed", nullable=False)
    is_active: Mapped[bool] = MappedColumn(Boolean, default=False)
    config: Mapped[dict[str, Any] | None] = MappedColumn(JSON, default=dict)

    installed_at: Mapped[datetime | None] = MappedColumn(DateTime, default=None)
    activated_at: Mapped[datetime | None] = MappedColumn(DateTime, default=None)
    updated_at: Mapped[datetime] = MappedColumn(
        default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    def __repr__(self) -> str:
        return f"<ModuleInfo {self.name} ({self.status})>"
