"""
Endpoints de gestion des paramètres.

- GET  /settings              — liste (avec filtres)
- GET  /settings/{key}        — valeur par clé
- POST /settings              — création / mise à jour (body JSON)
- PUT  /settings/{key}        — mise à jour (body JSON partiel)
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select

from app.api.deps import SessionDep
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_permission
from app.core.models.setting import Setting
from app.core.models.user import User

router = APIRouter()


class SettingUpsert(BaseModel):
    """Corps JSON pour la création / mise à jour d'un paramètre."""

    key: str | None = Field(default=None, description="Clé (optionnelle pour PUT dédié)")
    value: str = Field(default="")
    type: str = "string"
    is_public: bool = False
    description: str | None = None
    company_id: int | None = None


@router.get("/")
async def list_settings(
    session: SessionDep,
    skip: int = 0,
    limit: int = 100,
    public_only: bool = False,
    _: User = Depends(get_current_active_user),
):
    """Liste les paramètres."""
    stmt = select(Setting).order_by(Setting.key)
    if public_only:
        stmt = stmt.where(Setting.is_public.is_(True))
    stmt = stmt.offset(skip).limit(limit)
    result = await session.execute(stmt)
    settings_list = result.scalars().all()
    return [
        {
            "key": s.key,
            "value": s.value,
            "type": s.type,
            "is_public": s.is_public,
            "description": s.description,
            "company_id": s.company_id,
        }
        for s in settings_list
    ]


@router.get("/{key}")
async def get_setting(
    session: SessionDep,
    key: str,
    _: User = Depends(get_current_active_user),
):
    """Retourne la valeur d'un paramètre par clé."""
    from app.core.services.setting_service import SettingService
    svc = SettingService(session)
    value = await svc.get(key)
    if value is None:
        raise HTTPException(status_code=404, detail=f"Paramètre '{key}' introuvable")
    return {"key": key, "value": value}


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_setting(
    session: SessionDep,
    body: SettingUpsert,
    _: User = Depends(require_permission("setting", "create")),
):
    """Crée ou met à jour un paramètre (body JSON — compatible longues valeurs)."""
    from app.core.services.setting_service import SettingService
    svc = SettingService(session)
    setting = await svc.set(
        body.key or "setting",
        body.value,
        body.type,
        body.is_public,
        body.description,
        body.company_id,
    )
    return setting


@router.put("/{key}")
async def update_setting(
    session: SessionDep,
    key: str,
    body: SettingUpsert,
    _: User = Depends(require_permission("setting", "edit")),
):
    """Met à jour un paramètre existant (body JSON partiel)."""
    from app.core.services.setting_service import SettingService
    svc = SettingService(session)
    setting = await svc.update(
        key, body.value, body.type, body.is_public, body.description
    )
    if setting is None:
        raise HTTPException(status_code=404, detail=f"Paramètre '{key}' introuvable")
    return setting
