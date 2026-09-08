"""
Endpoints d'authentification.

- POST /login   — connexion, retourne access + refresh tokens
- POST /refresh — rafraîchit le token d'accès
- POST /logout  — déconnexion (révoque côté client)
- GET  /me     — profil de l'utilisateur courant
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from app.core.database import AsyncSession, get_session
from app.core.dependencies.auth import get_current_active_user
from app.core.models.role import Permission, Role, RolePermission
from app.core.models.user import User, UserRole
from app.core.models.user import User
from app.core.schemas.auth import LoginRequest, RefreshRequest, Token
from app.core.schemas.user import UserReadWithRoles
from app.core.services.auth_service import AuthService

router = APIRouter()

# ------------------------------------------------------------------ #
# Anti brute-force — limiteur en mémoire (IP + email).
# Suffisant pour un déploiement mono-process ; remplacer par Redis
# (ex. slowapi) en multi-workers.
# ------------------------------------------------------------------ #
_MAX_ATTEMPTS = 10          # tentatives
_WINDOW_SECONDS = 300       # fenêtre glissante de 5 minutes
_attempts: dict[str, list[float]] = {}


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")


def _rate_limit_check(key: str) -> None:
    import time

    now = time.monotonic()
    stamps = [t for t in _attempts.get(key, []) if now - t < _WINDOW_SECONDS]
    if len(stamps) >= _MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Trop de tentatives. Réessayez dans quelques minutes.",
        )
    stamps.append(now)
    _attempts[key] = stamps


@router.post("/login", response_model=Token)
async def login(
    request: Request,
    body: LoginRequest,
    session: AsyncSession = Depends(get_session),
):
    """Connexion — vérifie email/mot de passe/entreprise, retourne tokens."""
    _rate_limit_check(f"{_client_ip(request)}:{body.email.lower()}")
    auth_service = AuthService(session)
    user = await auth_service.authenticate(body.email, body.password)

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Identifiants incorrects",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if body.company_code and user.company.code != body.company_code:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Entreprise invalide pour cet utilisateur",
        )

    return await auth_service.get_tokens(user)


@router.post("/refresh", response_model=Token)
async def refresh(
    body: RefreshRequest,
    session: AsyncSession = Depends(get_session),
):
    """Rafraîchit le token d'accès."""
    auth_service = AuthService(session)
    try:
        return await auth_service.refresh_access_token(body.refresh_token)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=str(exc)
        ) from exc


@router.post("/logout")
async def logout(request: Request):
    """Déconnexion — le token reste valide jusqu'à expiration (côté client)."""
    return {"message": "Déconnexion réussie"}


@router.get("/me", response_model=UserReadWithRoles)
async def me(
    current_user: User = Depends(get_current_active_user),
    session: AsyncSession = Depends(get_session),
):
    """Retourne le profil complet de l'utilisateur courant (avec rôles)."""
    # Charge les rôles
    role_result = await session.execute(
        select(Role)
        .join(UserRole, Role.id == UserRole.role_id)
        .where(UserRole.user_id == current_user.id)
        .order_by(Role.id)
    )
    roles: list[Role] = list(role_result.scalars().all())

    # Charge les permissions pour chaque rôle
    role_ids = [r.id for r in roles]
    permissions_code: list[str] = []
    role_perms_by_role: dict[int, list[dict]] = {r.id: [] for r in roles}

    if role_ids:
        perm_result = await session.execute(
            select(Permission, RolePermission.role_id)
            .join(
                RolePermission,
                Permission.id == RolePermission.permission_id,
            )
            .where(RolePermission.role_id.in_(role_ids))
        )
        for perm, role_id in perm_result.fetchall():
            code = f"{perm.resource}:{perm.action}"
            permissions_code.append(code)
            if role_id in role_perms_by_role:
                role_perms_by_role[role_id].append({
                    "id": perm.id,
                    "resource": perm.resource,
                    "action": perm.action,
                    "description": perm.description,
                    "company_id": perm.company_id,
                })

    role_reads = []
    for role in roles:
        role_reads.append({
            "id": role.id,
            "name": role.name,
            "code": role.code,
            "description": role.description,
            "is_system": role.is_system,
            "is_global": role.is_global,
            "company_id": role.company_id,
            "is_active": role.is_active,
            "created_at": role.created_at,
            "updated_at": role.updated_at,
            "permissions": role_perms_by_role.get(role.id, []),
        })

    return UserReadWithRoles(
        id=current_user.id,
        email=current_user.email,
        phone=current_user.phone,
        first_name=current_user.first_name,
        last_name=current_user.last_name,
        is_active=current_user.is_active,
        is_verified=current_user.is_verified,
        company_id=current_user.company_id,
        agency_id=current_user.agency_id,
        is_superuser=current_user.is_superuser,
        created_at=current_user.created_at,
        updated_at=current_user.updated_at,
        roles=role_reads,
        permissions=permissions_code,
    )
