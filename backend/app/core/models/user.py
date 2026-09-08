"""Modèle User — authentification et identité."""
from __future__ import annotations

from typing import Any

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, MappedColumn, relationship

from app.core.database import Base, TenantMixin


class User(Base, TenantMixin):
    """
    Un utilisateur appartient à une entreprise et éventuellement à une agence.

    - ``is_superuser`` : accès complet à toutes les entreprises
    - ``is_active`` : peut se connecter
    - ``roles`` : rôles attribués (via UserRole)
    """

    email: Mapped[str] = MappedColumn(String(255), unique=True, nullable=False, index=True)
    phone: Mapped[str | None] = MappedColumn(String(50))
    first_name: Mapped[str] = MappedColumn(String(100), nullable=False)
    last_name: Mapped[str] = MappedColumn(String(100), nullable=False)
    password_hash: Mapped[str] = MappedColumn(String(255), nullable=False)

    is_active: Mapped[bool] = MappedColumn(Boolean, default=True)
    is_superuser: Mapped[bool] = MappedColumn(Boolean, default=False)
    is_verified: Mapped[bool] = MappedColumn(Boolean, default=False)

    # Relations
    agency_id: Mapped[int | None] = MappedColumn(
        ForeignKey("agencies.id", ondelete="SET NULL"), nullable=True
    )
    agency: Mapped["Agency | None"] = relationship("Agency", back_populates="users")

    user_roles: Mapped[list["UserRole"]] = relationship(
        "UserRole",
        back_populates="user",
        cascade="all, delete-orphan",
        lazy="selectin",
    )

    # On ne redéfinit pas company_id ici car TenantMixin le fournit,
    # mais on a besoin de la relation company -> users
    company: Mapped["Company"] = relationship("Company", back_populates="users")

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()

    def __repr__(self) -> str:
        return f"<User {self.email}>"


class UserRole(Base):
    """Table d'association many-to-many User <-> Role."""

    __tablename__ = "users_roles"

    user_id: Mapped[int] = MappedColumn(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    role_id: Mapped[int] = MappedColumn(
        Integer, ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True
    )

    user: Mapped["User"] = relationship("User", back_populates="user_roles")
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles")
