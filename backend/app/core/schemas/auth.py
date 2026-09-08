"""Schémas pour l'authentification — JWT, login, refresh."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class LoginRequest(BaseModel):
    """Payload pour la connexion."""

    email: str = Field(..., min_length=3, max_length=255)
    password: str = Field(..., min_length=1)
    company_code: str | None = Field(
        default=None,
        description="Code d'entreprise (requis si multi-entreprise)",
    )


class RefreshRequest(BaseModel):
    """Payload pour rafraîchir le token."""

    refresh_token: str


class Token(BaseModel):
    """Token JWT retourné après authentification."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # secondes


class TokenPayload(BaseModel):
    """Payload décodé d'un JWT."""

    sub: str | None = None
    company_id: int | None = None
    scopes: list[str] = []
    exp: int | None = None
    iat: int | None = None
    type: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)
