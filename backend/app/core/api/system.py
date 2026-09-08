"""
Endpoints système — modules, devises, taxes, séquences, santé.

- GET  /modules                — état des modules
- POST /modules/{name}/install  — installation
- POST /modules/{name}/activate — activation
- POST /modules/{name}/deactivate — désactivation
- GET  /currencies             — devises
- GET  /taxes                  — taxes
- GET  /sequences              — séquences
- GET  /info                   — infos de l'application
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select

from app.api.deps import SessionDep
from app.core.config import settings as app_settings
from app.core.dependencies.auth import get_current_active_user
from app.core.dependencies.permissions import require_superuser
from app.core.models.currency import Currency
from app.core.models.module_info import ModuleInfo
from app.core.models.tax import Tax
from app.core.schemas.auth import Token
from app.core.services.module_service import ModuleService

router = APIRouter()


@router.get("/modules")
async def list_modules(
    session: SessionDep,
    _: User = Depends(require_superuser),
):
    """Liste tous les modules avec leur statut."""
    svc = ModuleService(session)
    modules = await svc.list_all()
    return [
        {
            "name": m.name,
            "version": m.version,
            "status": m.status,
            "is_active": m.is_active,
            "config": m.config,
            "installed_at": m.installed_at,
            "activated_at": m.activated_at,
        }
        for m in modules
    ]


@router.get("/modules/active")
async def list_modules_public(
    session: SessionDep,
    _: User = Depends(get_current_active_user),
):
    """État simplifié des modules — accessible à tout utilisateur authentifié.

    Utilisé par le lanceur d'applications du tableau de bord : la grille
    n'affiche que les modules actifs, la section « autres applications »
    liste les modules installés mais désactivés.
    """
    svc = ModuleService(session)
    modules = await svc.list_all()
    return [
        {"name": m.name, "status": m.status, "is_active": m.is_active}
        for m in modules
    ]


@router.post("/modules/{module_name}/install", status_code=status.HTTP_201_CREATED)
async def install_module(
    session: SessionDep,
    module_name: str,
    _: User = Depends(require_superuser),
):
    """Installe un module."""
    svc = ModuleService(session)
    try:
        info = await svc.install_module(module_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    return {"name": info.name, "status": info.status, "is_active": info.is_active}


@router.post("/modules/{module_name}/activate")
async def activate_module(
    session: SessionDep,
    module_name: str,
    _: User = Depends(require_superuser),
):
    """Active un module installé."""
    svc = ModuleService(session)
    try:
        info = await svc.activate_module(module_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await session.commit()
    return {"name": info.name, "status": info.status, "is_active": info.is_active}


@router.post("/modules/{module_name}/deactivate")
async def deactivate_module(
    session: SessionDep,
    module_name: str,
    _: User = Depends(require_superuser),
):
    """Désactive un module."""
    svc = ModuleService(session)
    try:
        info = await svc.deactivate_module(module_name)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    await session.commit()
    return {"name": info.name, "status": info.status, "is_active": info.is_active}


@router.get("/currencies")
async def list_currencies(
    session: SessionDep,
    _: User = Depends(get_current_active_user),
):
    """Liste les devises disponibles."""
    result = await session.execute(select(Currency).where(Currency.is_active.is_(True)))
    return list(result.scalars().all())


@router.get("/taxes")
async def list_taxes(
    session: SessionDep,
    _: User = Depends(get_current_active_user),
):
    """Liste les taxes configurées."""
    result = await session.execute(select(Tax).where(Tax.is_active.is_(True)))
    return list(result.scalars().all())


@router.get("/info")
async def app_info():
    """Retourne les informations de l'application."""
    return {
        "name": app_settings.app_name,
        "version": app_settings.app_version,
        "environment": app_settings.environment,
        "debug": app_settings.debug,
    }


# Imports circulaires résolus en bas du fichier
from app.core.models.user import User  # noqa: E402

