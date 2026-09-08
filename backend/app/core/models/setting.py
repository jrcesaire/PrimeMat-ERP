"""Modèle Setting — paramètres configurables."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base


class Setting(Base):
    """
    Paramètre clé/valeur configurable.

    - ``key`` : identifiant unique (ex: ``invoice_prefix``)
    - ``value`` : valeur stockée en texte (convertie selon ``type``)
    - ``type`` : ``string``, ``integer``, ``boolean``, ``json``
    - ``is_public`` : visible par les modules métier
    - ``company_id`` : null → paramètre global

    L'unicité est garantie sur (company_id, key) via ``UniqueConstraint``.
    PostgreSQL gère correctement les NULL dans les contraintes d'unicité
    (un NULL != un autre NULL), ce qui permet un seul global par clé.
    """

    id: Mapped[int] = MappedColumn(Integer, primary_key=True, autoincrement=True)

    company_id: Mapped[int | None] = MappedColumn(
        Integer,
        ForeignKey("companies.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    key: Mapped[str] = MappedColumn(String(100), nullable=False, index=True)
    value: Mapped[str] = MappedColumn(String(5000), nullable=False)
    type: Mapped[str] = MappedColumn(String(20), default="string")
    is_public: Mapped[bool] = MappedColumn(Boolean, default=False)
    description: Mapped[str | None] = MappedColumn(String(500))

    created_at: Mapped[datetime] = MappedColumn(default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = MappedColumn(
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        nullable=False,
    )

    # Relations
    company: Mapped["Company | None"] = relationship("Company", back_populates="settings")

    __table_args__ = (
        UniqueConstraint("company_id", "key", name="uq_settings_company_key"),
    )
