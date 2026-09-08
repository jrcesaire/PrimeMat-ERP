"""
Configuration de la base de données.

Fournit :
- ``engine``      — moteur asynchrone SQLAlchemy 2
- ``AsyncSession`` — session asynchrone injectable
- ``Base``        — classe de base déclarative partagée
- ``TenantMixin`` — colonnes multi-entreprise + audit
- ``init_db``     — création des tables (dev / tests)
- ``close_db``    — fermeture du moteur
"""
from __future__ import annotations

import re
from datetime import datetime
from typing import Any, AsyncIterator

from sqlalchemy import ForeignKey, Integer, or_
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    async_engine_from_config,
    async_sessionmaker,
)
from sqlalchemy.orm import (
    DeclarativeBase,
    Mapped,
    MappedColumn,
    declared_attr,
    sessionmaker,
)
from sqlalchemy import event

from app.core.config import settings
from app.core.tenant import get_current_company, TENANT_EXCLUDED_MODELS


# ------------------------------------------------------------------ #
# Helpers
# ------------------------------------------------------------------ #
def _camel_to_snake(name: str) -> str:
    s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
    return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()


def _pluralize(snake: str) -> str:
    if snake.endswith("y"):
        return snake[:-1] + "ies"
    if not snake.endswith("s"):
        return snake + "s"
    return snake


# ------------------------------------------------------------------ #
# Declarative base
# ------------------------------------------------------------------ #
class Base(DeclarativeBase):
    """Classe de base — génère __tablename__ en snake_case pluriel."""

    @declared_attr  # type: ignore[misc]
    def __tablename__(cls) -> str:  # noqa: N805
        snake = _camel_to_snake(cls.__name__)
        return _pluralize(snake)


# ------------------------------------------------------------------ #
# TenantMixin — colonnes communes multi-entreprise + audit
# ------------------------------------------------------------------ #
class TenantMixin:
    """
    Mixin ajoutant les colonnes communes à tous les modèles métier.

    - id          — clé primaire auto-incrémentée
    - company_id  — isolation multi-entreprise
    - created_at / updated_at  — audit temporel
    - created_by / updated_by  — traçabilité utilisateur (optionnel)
    """

    __allow_unmapped__ = True

    id: Mapped[int] = MappedColumn(Integer, primary_key=True, autoincrement=True)

    @declared_attr  # type: ignore[misc]
    def company_id(cls) -> Mapped[int]:
        return MappedColumn(
            Integer,
            ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )

    @declared_attr  # type: ignore[misc]
    def created_at(cls) -> Mapped[datetime]:
        return MappedColumn(default=datetime.utcnow, nullable=False)

    @declared_attr  # type: ignore[misc]
    def updated_at(cls) -> Mapped[datetime]:
        return MappedColumn(
            default=datetime.utcnow,
            onupdate=datetime.utcnow,
            nullable=False,
        )

    @declared_attr  # type: ignore[misc]
    def created_by(cls) -> Mapped[int | None]:
        return MappedColumn(
            Integer,
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        )

    @declared_attr  # type: ignore[misc]
    def updated_by(cls) -> Mapped[int | None]:
        return MappedColumn(
            Integer,
            ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        )


# ------------------------------------------------------------------ #
# Engine & session
# ------------------------------------------------------------------ #
engine = async_engine_from_config(
    {"sqlalchemy.url": str(settings.database_url)},
    pool_size=20,
    max_overflow=30,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=settings.debug,
    future=True,
)

AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False,
)


# ------------------------------------------------------------------ #
# Isolation multi-tenant automatique
# ------------------------------------------------------------------ #
@event.listens_for(AsyncSession.sync_session_class, "do_orm_execute")
def _apply_tenant_filter(orm_exec_state):  # noqa: ANN001
    """
    Ajoute automatiquement ``WHERE company_id = ?`` à toute requête SELECT
    ORM ciblant un modèle multi-tenant, si une entreprise est définie dans
    le contexte d'exécution (utilisateur non-superadmin authentifié).

    - Superadmin / tâches système / login : contexte ``None`` → pas de filtre.
    - Les chargements de colonnes/relations (selectinload, lazy) ne sont pas
      refiltrés : ils dérivent d'objets parents déjà filtrés.
    - Opt-out ponctuel : ``.execution_options(include_all_tenants=True)``.
    """
    if not orm_exec_state.is_select:
        return
    if orm_exec_state.is_column_load or orm_exec_state.is_relationship_load:
        return
    company_id = get_current_company()
    if company_id is None:
        return
    if orm_exec_state.execution_options.get("include_all_tenants"):
        return

    clauses = []
    seen: set[type] = set()
    for mapper in orm_exec_state.all_mappers:
        cls = mapper.class_
        if cls in seen:
            continue
        seen.add(cls)
        if cls.__name__ in TENANT_EXCLUDED_MODELS:
            continue
        table = cls.__table__
        if "company_id" in table.columns:
            clauses.append(table.c.company_id == company_id)

    if clauses:
        orm_exec_state.statement = orm_exec_state.statement.where(or_(*clauses))


async def get_session() -> AsyncIterator[AsyncSession]:
    """Dépendance FastAPI — fournit une session async."""
    async with AsyncSessionLocal() as session:
        yield session


SessionDep = AsyncSession


async def init_db() -> None:
    """Crée toutes les tables (développement / tests uniquement)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)


async def close_db() -> None:
    """Ferme le moteur — appelée au shutdown de l'application."""
    await engine.dispose()
