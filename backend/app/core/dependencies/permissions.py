"""
Dépendances de contrôle d'accès (RBAC).

Utilisation ::

    @router.get("/products")
    async def list_products(
        _: User = Depends(require_permission("product", "view")),
    ):
        ...
"""
from __future__ import annotations

from typing import Any

from fastapi import Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_session
from app.core.dependencies.auth import get_current_active_user
from app.core.models.role import Permission, RolePermission
from app.core.models.user import User


async def get_user_permissions(
    user: User,
    session: AsyncSession,
) -> list[str]:
    """
    Récupère la liste des permissions (codes) pour un utilisateur.

    Format : ``["product:view", "order:create", ...]``
    Le wildcard ``*`` signifie toutes les permissions.
    """
    if user.is_superuser:
        return ["*"]

    role_ids: list[int] = []
    if user.user_roles:
        role_ids = [ur.role_id for ur in user.user_roles]

    if not role_ids:
        return []

    result = await session.execute(
        select(Permission.resource, Permission.action)
        .join(RolePermission, Permission.id == RolePermission.permission_id)
        .where(RolePermission.role_id.in_(role_ids))
    )
    return [f"{row[0]}:{row[1]}" for row in result.fetchall()]


def require_permission(resource: str, action: str):
    """
    Factory de dépendance FastAPI exigeant une permission.

    Usage ::

        from app.core.dependencies.permissions import require_permission

        @router.get("/products")
        async def list_products(
            user: User = Depends(require_permission("product", "view")),
        ):
            ...
    """

    async def _check(
        current_user: User = Depends(get_current_active_user),
        session: AsyncSession = Depends(get_session),
    ) -> User:
        if current_user.is_superuser:
            return current_user

        perms = await get_user_permissions(current_user, session)
        required = f"{resource}:{action}"

        if "*" not in perms and required not in perms:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Permission requise : {required}",
            )
        return current_user

    return _check


# Alias pratique pour super-user only
def require_superuser(
    current_user: User = Depends(get_current_active_user),
) -> User:
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Privilèges administrateur requis",
        )
    return current_user
