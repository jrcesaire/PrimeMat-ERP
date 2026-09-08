"""
Dépendances d'authentification.

Fournit :
- ``get_current_user``      — valide le JWT et retourne l'utilisateur
- ``get_current_active_user`` — même chose + vérifie ``is_active``
- ``get_current_company``    — extrait l'entreprise du token
- ``get_current_superuser``  — vérifie le statut super-utilisateur
- ``TokenPayloadDep``        — payload JWT injecté
"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, Request, status
from jose import JWTError

from app.core.config import settings
from app.core.database import AsyncSession, get_session
from app.core.models.user import User
from app.core.schemas.auth import TokenPayload


async def get_current_user(
    request: Request,
    session: AsyncSession = Depends(get_session),
) -> User:
    """
    Extrait et valide le token JWT depuis l'en-tête Authorization.

    Lève ``HTTPException(401)`` si le token est absent, invalide ou expiré.
    Charge l'utilisateur depuis la base.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token d'authentification requis",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = auth_header[7:]  # strip "Bearer "

    try:
        from app.core.security import decode_access_token
        payload = decode_access_token(token)
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Token invalide : {exc}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    user_id = payload.get("sub")
    if user_id is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token invalide",
            headers={"WWW-Authenticate": "Bearer"},
        )

    from sqlalchemy import select
    result = await session.execute(
        select(User).where(User.id == int(user_id))
    )
    user: User | None = result.scalar_one_or_none()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Utilisateur introuvable",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Isolation multi-tenant : le contexte est dérivé de l'utilisateur
    # authentifié (source de vérité : la base, pas le token).
    from app.core.tenant import set_current_company

    set_current_company(None if user.is_superuser else user.company_id)

    # Expose company_id from token for tenant awareness
    request.state.company_id = payload.get("company_id")
    return user


async def get_current_active_user(
    current_user: User = Depends(get_current_user),
) -> User:
    """Valide que l'utilisateur est actif."""
    if not current_user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Utilisateur inactif",
        )
    return current_user


async def get_current_company_id(
    request: Request,
    current_user: User = Depends(get_current_user),
) -> int:
    """Retourne l'ID de l'entreprise courante (du token ou du profil utilisateur)."""
    company_id = getattr(request.state, "company_id", None)
    if company_id is None:
        company_id = current_user.company_id
    return company_id


def get_current_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    """Vérifie que l'utilisateur est super-administrateur."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privilèges administrateur requis",
        )
    return current_user


def get_token_payload(request: Request) -> TokenPayload:
    """Extrait le payload JWT de la requête (pour les logs)."""
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        try:
            from app.core.security import decode_access_token
            payload = decode_access_token(auth_header[7:])
            return TokenPayload(**payload)
        except JWTError:
            pass
    return TokenPayload(sub=None)


# Dépendances FastAPI réutilisables
CurrentUser = Any  # type: ignore[type-arg]
