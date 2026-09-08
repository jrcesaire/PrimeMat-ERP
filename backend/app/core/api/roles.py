"""
Endpoints de gestion des rôles et permissions.

- GET  /roles          — liste
- POST /roles          — création
- GET  /roles/{id}     — détail
- PUT  /roles/{id}     — mise à jour
- DELETE /roles/{id}   — suppression
- GET  /permissions    — liste des permissions disponibles
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_permission
from app.core.models.role import Permission, Role, RolePermission
from app.core.models.user import User, UserRole
from app.core.models.user import User
from app.core.schemas.role import (
    PermissionBase,
    PermissionCreate,
    PermissionRead,
    RoleCreate,
    RoleRead,
    RoleUpdate,
)

router = APIRouter()


@router.get("/", response_model=list[RoleRead])
async def list_roles(
    session: SessionDep,
    _: User = Depends(require_permission("role", "view")),
):
    """Liste les rôles."""
    result = await session.execute(select(Role).order_by(Role.id))
    return list(result.scalars().all())


@router.post("/", response_model=RoleRead, status_code=status.HTTP_201_CREATED)
async def create_role(
    session: SessionDep,
    body: RoleCreate,
    _: User = Depends(require_permission("role", "create")),
):
    """Crée un nouveau rôle avec des permissions."""
    role = Role(
        name=body.name,
        code=body.code,
        description=body.description,
        is_system=body.is_system,
        is_global=body.is_global,
        company_id=1,  # will be overridden by tenant context
    )
    session.add(role)
    await session.flush()

    # Attribue les permissions
    if body.permission_ids:
        for perm_id in body.permission_ids:
            session.add(RolePermission(role_id=role.id, permission_id=perm_id))

    await session.commit()
    await session.refresh(role)
    return role


@router.get("/{role_id}", response_model=RoleRead)
async def get_role(
    session: SessionDep,
    role_id: int,
    _: User = Depends(require_permission("role", "view")),
):
    """Retourne un rôle par ID."""
    role = await session.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Rôle introuvable")
    return role


@router.put("/{role_id}", response_model=RoleRead)
async def update_role(
    session: SessionDep,
    role_id: int,
    body: RoleUpdate,
    _: User = Depends(require_permission("role", "edit")),
):
    """Met à jour un rôle."""
    role = await session.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Rôle introuvable")
    if role.is_system:
        raise HTTPException(status_code=400, detail="Rôle système non modifiable")

    update_data = body.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if field != "permission_ids" and hasattr(role, field):
            setattr(role, field, value)

    await session.commit()
    await session.refresh(role)
    return role


@router.delete("/{role_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_role(
    session: SessionDep,
    role_id: int,
    _: User = Depends(require_permission("role", "delete")),
):
    """Supprime un rôle (sauf les rôles système)."""
    role = await session.get(Role, role_id)
    if not role:
        raise HTTPException(status_code=404, detail="Rôle introuvable")
    if role.is_system:
        raise HTTPException(status_code=400, detail="Rôle système non supprimable")

    await session.delete(role)
    await session.commit()
    return None


@router.get("/permissions", response_model=list[PermissionRead])
async def list_permissions(
    session: SessionDep,
    _: User = Depends(get_current_active_user),
):
    """Liste toutes les permissions disponibles."""
    result = await session.execute(select(Permission).order_by(Permission.id))
    return list(result.scalars().all())


@router.post("/permissions", response_model=PermissionRead)
async def create_permission(
    session: SessionDep,
    body: PermissionCreate,
    _: User = Depends(require_permission("permission", "create")),
):
    """Crée une nouvelle permission."""
    perm = Permission(
        resource=body.resource,
        action=body.action,
        description=body.description,
        company_id=1,
    )
    session.add(perm)
    await session.commit()
    await session.refresh(perm)
    return perm
