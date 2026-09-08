"""
Utilitaires de sécurité : hachage de mots de passe, JWT, tokens.
"""
from __future__ import annotations

import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Any

from jose import JWTError, jwt

from app.core.config import settings


def hash_password(password: str) -> str:
    """Hache un mot de passe avec bcrypt (API native, compatible bcrypt >= 4)."""
    if len(password.encode("utf-8")) > 72:
        password = password[:72]
    hashed = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    return hashed.decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    """Vérifie un mot de passe contre son hash bcrypt."""
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_access_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
    *,
    company_id: int | None = None,
    scopes: list[str] | None = None,
) -> str:
    """
    Crée un token d'accès JWT.

    Le token contient :
    - ``sub`` : identifiant de l'utilisateur
    - ``company_id`` : entreprise courante
    - ``scopes`` : permissions accordées
    - ``exp`` / ``iat`` : date d'expiration / d'émission
    """
    expire = datetime.now(tz=timezone.utc) + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(tz=timezone.utc),
        "iss": settings.jwt_issuer,
        "type": "access",
    }
    if company_id is not None:
        to_encode["company_id"] = company_id
    if scopes:
        to_encode["scopes"] = scopes
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def create_refresh_token(
    subject: str | Any,
    expires_delta: timedelta | None = None,
) -> str:
    """Crée un token de rafraîchissement JWT."""
    expire = datetime.now(tz=timezone.utc) + (
        expires_delta
        or timedelta(days=settings.refresh_token_expire_days)
    )
    to_encode: dict[str, Any] = {
        "sub": str(subject),
        "exp": expire,
        "iat": datetime.now(tz=timezone.utc),
        "iss": settings.jwt_issuer,
        "type": "refresh",
    }
    return jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_token(token: str) -> dict[str, Any]:
    """Décode un token JWT — lève JWTError si invalide."""
    return jwt.decode(
        token,
        settings.secret_key,
        algorithms=[settings.jwt_algorithm],
        issuer=settings.jwt_issuer,
    )


def decode_access_token(token: str) -> dict[str, Any]:
    """Décode un access token — lève JWTError si invalide ou si mauvais type."""
    payload = decode_token(token)
    if payload.get("type") != "access":
        raise JWTError("Invalid token type")
    return payload


def decode_refresh_token(token: str) -> dict[str, Any]:
    """Décode un refresh token."""
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise JWTError("Invalid token type")
    return payload
