"""
Endpoints d'authentification.

- POST /login   — connexion, retourne access + refresh tokens
- POST /refresh — rafraîchit le token d'accès
- POST /logout  — déconnexion (révoque côté client)
- GET  /me     — profil de l'utilisateur courant
"""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select

from app.core.config import settings
from app.core.database import AsyncSession, get_session
from app.core.dependencies.auth import get_current_active_user
from app.core.models.role import Permission, Role, RolePermission
from app.core.models.user import User, UserRole
from app.core.models.user import User
from app.core.schemas.auth import LoginRequest, RefreshRequest, Token
from app.core.schemas.user import UserReadWithRoles
from app.core.services.auth_service import AuthService

logger = logging.getLogger(__name__)

router = APIRouter()

# ------------------------------------------------------------------ #
# Anti brute-force — limiteur (IP + email).
# Redis si disponible (partagé entre workers/processus), sinon
# repli automatique en mémoire (mono-process, dev).
# ------------------------------------------------------------------ #
_MAX_ATTEMPTS = 10          # tentatives
_WINDOW_SECONDS = 300       # fenêtre glissante de 5 minutes
_attempts: dict[str, list[float]] = {}   # repli mémoire
_redis: object | None = None
_redis_tried = False


def _get_redis() -> object | None:
    """Connexion Redis paresseuse (None si indisponible)."""
    global _redis, _redis_tried
    if not _redis_tried:
        _redis_tried = True
        try:
            import redis as redis_lib

            client = redis_lib.Redis.from_url(
                settings.redis_url, socket_connect_timeout=1,
                socket_timeout=1, decode_responses=True,
            )
            client.ping()
            _redis = client
            logger.info("Rate-limit : Redis connecté (%s)", settings.redis_url)
        except Exception:  # noqa: BLE001 — repli mémoire assumé
            logger.warning(
                "Rate-limit : Redis indisponible, repli en mémoire "
                "(mono-process uniquement)"
            )
            _redis = None
    return _redis


def _client_ip(request: Request) -> str:
    fwd = request.headers.get("x-forwarded-for")
    return fwd.split(",")[0].strip() if fwd else (request.client.host if request.client else "?")


def _rate_limit_check(key: str) -> None:
    import time

    client = _get_redis()
    if client is not None:
        try:
            # INCR + EXPIRE : compteur glissant par fenêtre fixe
            redis_key = f"rl:{key}"
            count = client.incr(redis_key)
            if count == 1:
                client.expire(redis_key, _WINDOW_SECONDS)
            if int(count) > _MAX_ATTEMPTS:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail="Trop de tentatives. Réessayez dans quelques minutes.",
                )
            return
        except HTTPException:
            raise
        except Exception:  # noqa: BLE001 — Redis tombé → repli mémoire
            logger.warning("Rate-limit : Redis en erreur, repli mémoire")
    # --- Repli mémoire (fenêtre glissante) ---
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

    if body.company_code and (
        user.company is None or user.company.code != body.company_code
    ):
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
