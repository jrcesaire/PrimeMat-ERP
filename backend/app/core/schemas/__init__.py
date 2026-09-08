"""Schémas Pydantic du Core."""

from app.core.schemas.user import UserBase, UserCreate, UserRead, UserReadWithRoles, UserUpdate
from app.core.schemas.auth import LoginRequest, RefreshRequest, Token, TokenPayload
from app.core.schemas.company import AgencyBase, AgencyCreate, AgencyRead, CompanyBase, CompanyCreate, CompanyRead
from app.core.schemas.role import PermissionBase, PermissionCreate, PermissionRead, RoleBase, RoleCreate, RoleRead
from app.core.schemas.common import PaginatedResponse, PaginationParams

__all__ = [
    # User
    "UserBase",
    "UserCreate",
    "UserRead",
    "UserReadWithRoles",
    "UserUpdate",
    # Auth
    "LoginRequest",
    "RefreshRequest",
    "Token",
    "TokenPayload",
    # Company
    "CompanyBase",
    "CompanyCreate",
    "CompanyRead",
    "AgencyBase",
    "AgencyCreate",
    "AgencyRead",
    # Role / Permission
    "RoleBase",
    "RoleCreate",
    "RoleRead",
    "PermissionBase",
    "PermissionCreate",
    "PermissionRead",
    # Common
    "PaginatedResponse",
    "PaginationParams",
]
