"""
Endpoints de gestion des utilisateurs.

- GET    /users         — liste paginée
- POST   /users         — création
- GET    /users/{id}    — détail
- PUT    /users/{id}    — mise à jour
- DELETE /users/{id}    — suppression
- GET    /users/{id}/roles — rôles de l'utilisateur
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_permission
from app.core.models.role import Role
from app.core.models.user import User, UserRole
from app.core.models.user import User
from app.core.schemas.common import PaginatedResponse
from app.core.schemas.role import RoleRead
from app.core.schemas.user import UserCreate, UserRead, UserUpdate
from app.core.services.user_service import UserService

router = APIRouter()


@router.get("/", response_model=PaginatedResponse[UserRead])
async def list_users(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    _: User = Depends(require_permission("user", "view")),
):
    """Liste paginée des utilisateurs."""
    result = await session.execute(
        select(User).offset(skip).limit(limit).order_by(User.id)
    )
    users = list(result.scalars().all())

    count_result = await session.execute(select(User))
    total = len(count_result.scalars().unique().all())

    return PaginatedResponse(
        items=users, total=total, skip=skip, limit=limit,
        has_more=(skip + len(users)) < total,
    )


@router.post("/", response_model=UserRead, status_code=status.HTTP_201_CREATED)
async def create_user(
    session: SessionDep,
    body: UserCreate,
    _: User = Depends(require_permission("user", "create")),
):
    """Crée un nouvel utilisateur."""
    svc = UserService(session)
    try:
        user = await svc.create(body)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail=str(exc)
        )
    return user


@router.get("/{user_id}", response_model=UserRead)
async def get_user(
    session: SessionDep,
    user_id: int,
    _: User = Depends(require_permission("user", "view")),
):
    """Retourne un utilisateur par ID."""
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    return user


@router.put("/{user_id}", response_model=UserRead)
async def update_user(
    session: SessionDep,
    user_id: int,
    body: UserUpdate,
    _: User = Depends(require_permission("user", "edit")),
):
    """Met à jour un utilisateur."""
    svc = UserService(session)
    try:
        return await svc.update(user_id, body)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    session: SessionDep,
    user_id: int,
    _: User = Depends(require_permission("user", "delete")),
):
    """Supprime un utilisateur."""
    svc = UserService(session)
    user = await session.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    await svc.delete(user_id)
    return None


@router.get("/{user_id}/roles", response_model=list[RoleRead])
async def get_user_roles(
    session: SessionDep,
    user_id: int,
    current_user: User = Depends(require_permission("user", "view")),
):
    """Retourne les rôles d'un utilisateur (même entreprise uniquement)."""
    target = await session.get(User, user_id)
    if not target:
        raise HTTPException(status_code=404, detail="Utilisateur introuvable")
    if not current_user.is_superuser and target.company_id != current_user.company_id:
        raise HTTPException(status_code=403, detail="Accès restreint")
    result = await session.execute(
        select(Role)
        .join(UserRole, Role.id == UserRole.role_id)
        .where(UserRole.user_id == user_id)
        .order_by(Role.id)
    )
    return list(result.scalars().all())
