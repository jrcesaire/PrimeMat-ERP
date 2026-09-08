"""Schémas pour les utilisateurs."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, EmailStr, Field

from app.core.schemas.role import RoleRead


# ------------------------------------------------------------------ #
# User
# ------------------------------------------------------------------ #
class UserBase(BaseModel):
    email: EmailStr
    phone: str | None = None
    first_name: str = Field(..., min_length=1, max_length=100)
    last_name: str = Field(..., min_length=1, max_length=100)
    is_active: bool = True
    is_verified: bool = False


class UserCreate(UserBase):
    password: str = Field(..., min_length=8, max_length=128)
    company_id: int
    agency_id: int | None = None
    role_ids: list[int] = Field(default_factory=list)


class UserUpdate(BaseModel):
    email: EmailStr | None = None
    phone: str | None = None
    first_name: str | None = None
    last_name: str | None = None
    password: str | None = None
    is_active: bool | None = None
    is_verified: bool | None = None
    agency_id: int | None = None
    role_ids: list[int] | None = None


class UserRead(UserBase):
    id: int
    company_id: int
    agency_id: int | None = None
    is_superuser: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class UserReadWithRoles(UserRead):
    """Utilisateur avec ses rôles et permissions associées."""

    roles: list[RoleRead] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)
