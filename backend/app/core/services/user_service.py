"""
Service utilisateur — CRUD et gestion des rôles.
"""
from __future__ import annotations

import logging

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.models.role import Role
from app.core.models.user import User, UserRole
from app.core.models.user import User
from app.core.schemas.user import UserCreate, UserUpdate
from app.core.security import hash_password

logger = logging.getLogger(__name__)


class UserService:
    """Service pour la gestion des utilisateurs."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------ #
    # CRUD
    # ------------------------------------------------------------------ #
    async def create(self, data: UserCreate, created_by: int | None = None) -> User:
        """Crée un nouvel utilisateur."""
        # Vérifie l'unicité de l'email
        existing = await self.session.execute(
            select(User).where(User.email == data.email)
        )
        if existing.scalar_one_or_none():
            raise ValueError(f"Un utilisateur avec l'email {data.email} existe déjà")

        user = User(
            email=data.email,
            phone=data.phone,
            first_name=data.first_name,
            last_name=data.last_name,
            company_id=data.company_id,
            agency_id=data.agency_id,
            password_hash=hash_password(data.password),
            created_by=created_by,
        )
        self.session.add(user)
        await self.session.flush()  # génère l'ID

        # Attribue les rôles
        if data.role_ids:
            await self.assign_roles(user.id, data.role_ids)

        await self.session.commit()
        await self.session.refresh(user)
        logger.info("Utilisateur créé : %s (id=%s)", user.email, user.id)
        return user

    async def get_by_id(self, user_id: int) -> User | None:
        """Récupère un utilisateur par ID."""
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> User | None:
        """Récupère un utilisateur par email."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()

    async def update(self, user_id: int, data: UserUpdate) -> User:
        """Met à jour un utilisateur."""
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")

        update_data = data.model_dump(exclude_unset=True)

        # Mot de passe : rehashé uniquement si fourni non vide
        if "password" in update_data:
            pwd = update_data.pop("password") or ""
            if pwd:
                update_data["password_hash"] = hash_password(pwd)

        # Les rôles sont gérés via la table d'association, pas comme colonne
        update_data.pop("role_ids", None)

        for field, value in update_data.items():
            if hasattr(user, field):
                setattr(user, field, value)

        # Gestion des rôles : uniquement si explicitement fournie
        if data.role_ids is not None:
            await self.assign_roles(user_id, data.role_ids)

        await self.session.commit()
        await self.session.refresh(user)
        return user

    async def delete(self, user_id: int) -> None:
        """Supprime un utilisateur."""
        await self.session.delete(await self.session.get(User, user_id))
        await self.session.commit()
        logger.info("Utilisateur supprimé : id=%s", user_id)

    async def deactivate(self, user_id: int) -> User:
        """Désactive un utilisateur."""
        user = await self.get_by_id(user_id)
        if not user:
            raise ValueError("Utilisateur introuvable")
        user.is_active = False
        await self.session.commit()
        await self.session.refresh(user)
        return user

    # ------------------------------------------------------------------ #
    # Rôles
    # ------------------------------------------------------------------ #
    async def assign_roles(self, user_id: int, role_ids: list[int]) -> None:
        """Assigne des rôles à un utilisateur (remplace les existants)."""
        # Supprime les anciens rôles
        await self.session.execute(
            UserRole.__table__.delete().where(UserRole.user_id == user_id)
        )
        # Ajoute les nouveaux
        for role_id in role_ids:
            self.session.add(UserRole(user_id=user_id, role_id=role_id))
        await self.session.flush()

    async def get_roles(self, user_id: int) -> list[Role]:
        """Récupère les rôles d'un utilisateur."""
        result = await self.session.execute(
            select(Role)
            .join(UserRole, Role.id == UserRole.role_id)
            .where(UserRole.user_id == user_id)
            .order_by(Role.id)
        )
        return list(result.scalars().all())
