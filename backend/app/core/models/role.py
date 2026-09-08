"""Modèles Role et Permission — contrôle d'accès RBAC."""
from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin


class Role(Base, TenantMixin):
    """
    Un rôle regroupe un ensemble de permissions.

    Exemples : ``admin``, ``sales_manager``, ``stock_operator``.

    - ``is_system`` : rôle système (non supprimable)
    - ``is_global`` : s'applique à toutes les entreprises
    """

    name: Mapped[str] = MappedColumn(String(100), nullable=False)
    code: Mapped[str] = MappedColumn(String(50), index=True)
    description: Mapped[str | None] = MappedColumn(String(500))
    is_system: Mapped[bool] = MappedColumn(Boolean, default=False)
    is_global: Mapped[bool] = MappedColumn(Boolean, default=False)
    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)

    # Relations
    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="role",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    def __repr__(self) -> str:
        return f"<Role {self.code}>"


class Permission(Base, TenantMixin):
    """
    Une permission représente une action sur une ressource.

    Exemples : ``product:create``, ``order:confirm``, ``invoice:cancel``.
    """

    resource: Mapped[str] = MappedColumn(String(100), nullable=False, index=True)
    action: Mapped[str] = MappedColumn(String(50), nullable=False)
    description: Mapped[str | None] = MappedColumn(String(500))

    role_permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="permission",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    @property
    def code(self) -> str:
        return f"{self.resource}:{self.action}"

    def __repr__(self) -> str:
        return f"<Permission {self.code}>"


class RolePermission(Base):
    """Table d'association many-to-many Role <-> Permission."""

    __tablename__ = "roles_permissions"

    role_id: Mapped[int] = MappedColumn(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )
    permission_id: Mapped[int] = MappedColumn(
        Integer, ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True
    )

    role: Mapped["Role"] = relationship("Role", back_populates="role_permissions")
    permission: Mapped["Permission"] = relationship(
        "Permission", back_populates="role_permissions"
    )
