"""Schémas pour les rôles et permissions."""
from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


# ------------------------------------------------------------------ #
# Role
# ------------------------------------------------------------------ #
class RoleBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    code: str = Field(..., min_length=1, max_length=50)
    description: str | None = None
    is_system: bool = False
    is_global: bool = False


class RoleCreate(RoleBase):
    permission_ids: list[int] = Field(default_factory=list)


class RoleUpdate(BaseModel):
    name: str | None = None
    code: str | None = None
    description: str | None = None
    is_active: bool | None = None
    permission_ids: list[int] | None = None


class RoleRead(RoleBase):
    id: int
    company_id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime
    permissions: list["PermissionRead"] = Field(default_factory=list)

    model_config = {"from_attributes": True}


# ------------------------------------------------------------------ #
# Permission
# ------------------------------------------------------------------ #
class PermissionBase(BaseModel):
    resource: str = Field(..., min_length=1, max_length=100)
    action: str = Field(..., min_length=1, max_length=50)
    description: str | None = None


class PermissionCreate(PermissionBase):
    pass


class PermissionRead(PermissionBase):
    id: int
    company_id: int
    role_permissions: list[dict[str, Any]] = Field(default_factory=list)

    model_config = {"from_attributes": True}

    @property
    def code(self) -> str:
        return f"{self.resource}:{self.action}"
