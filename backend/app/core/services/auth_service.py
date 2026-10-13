"""
Service d'authentification.

Gère :
- la connexion (vérification mot de passe, génération de tokens)
- le rafraîchissement de token
- la récupération de l'utilisateur par email
"""
from __future__ import annotations

import logging
from datetime import timedelta

from app.core.security import JWTError
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.schemas.auth import Token
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_access_token,
    verify_password,
)
from app.core.models.user import User

logger = logging.getLogger(__name__)


class AuthService:
    """Service d'authentification — sans dépendance à un module métier."""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ------------------------------------------------------------------ #
    # Login / Logout
    # ------------------------------------------------------------------ #
    async def authenticate(self, email: str, password: str) -> User | None:
        """
        Vérifie les identifiants et retourne l'utilisateur si valide.

        Retourne ``None`` si l'email ou le mot de passe est incorrect.
        """
        result = await self.session.execute(
            select(User)
            .options(selectinload(User.company))
            .where(User.email == email)
        )
        user: User | None = result.scalar_one_or_none()

        if not user or not user.is_active:
            return None

        if not verify_password(password, user.password_hash):
            logger.warning("Tentative de connexion échouée pour %s", email)
            return None

        logger.info("Connexion réussie pour %s", email)
        return user

    async def get_tokens(self, user: User) -> Token:
        """Génère les tokens d'accès et de rafraîchissement."""
        access_token = create_access_token(
            subject=str(user.id),
            company_id=user.company_id,
            scopes=[],
        )
        refresh_token = create_refresh_token(subject=str(user.id))

        expires_in = settings.access_token_expire_minutes * 60

        return Token(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=expires_in,
        )

    # ------------------------------------------------------------------ #
    # Token refresh
    # ------------------------------------------------------------------ #
    async def refresh_access_token(self, refresh_token: str) -> Token:
        """Rafraîchit le token d'accès à partir d'un refresh token valide."""
        try:
            from app.core.security import decode_refresh_token
            payload = decode_refresh_token(refresh_token)
        except JWTError as exc:
            raise ValueError(f"Refresh token invalide : {exc}") from exc

        user_id = int(payload["sub"])
        result = await self.session.execute(
            select(User).where(User.id == user_id)
        )
        user: User | None = result.scalar_one_or_none()
        if not user or not user.is_active:
            raise ValueError("Utilisateur introuvable ou inactif")

        return await self.get_tokens(user)

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #
    async def get_user_by_email(self, email: str) -> User | None:
        """Récupère un utilisateur par email."""
        result = await self.session.execute(
            select(User).where(User.email == email)
        )
        return result.scalar_one_or_none()
