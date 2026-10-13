"""
Routeurs API du Core.

Regroupe tous les routeurs du module Core, chacun sous son propre
sous-préfixe pour éviter les conflits de routes dynamiques.
"""
from __future__ import annotations

from fastapi import APIRouter

from app.core.api.auth import router as auth_router
from app.core.api.setup import router as setup_router
from app.core.api.users import router as users_router
from app.core.api.companies import router as companies_router
from app.core.api.roles import router as roles_router
from app.core.api.settings import router as settings_router
from app.core.api.system import router as system_router

router = APIRouter()

# Auth (préfixe /auth — correspond au frontend: /auth/login, /auth/me, ...)
router.include_router(auth_router, prefix="/auth", tags=["auth"])

# Sous-ressources du Core
router.include_router(users_router, prefix="/users", tags=["users"])
router.include_router(companies_router, prefix="/companies", tags=["companies"])
router.include_router(roles_router, prefix="/roles", tags=["roles"])
router.include_router(settings_router, prefix="/settings", tags=["settings"])
# System (préfixe "/system" — /modules, /currencies, /taxes)
router.include_router(system_router, prefix="/system", tags=["system"])
# Setup — configuration initiale (premier lancement, endpoints publics)
router.include_router(setup_router, prefix="/setup", tags=["setup"])
