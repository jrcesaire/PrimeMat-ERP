"""
Point d'entrée de l'application FastAPI.

Configure :
- le routeur API (`/api/v1`)
- l'authentification / ouverture de session
- Sentry
- Prometheus
- l'événement de démarrage / arrêt (init DB, modules)
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

import sentry_sdk
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.api import api_router
from app.core.config import settings
from app.core.database import close_db, init_db
from app.core.modules import ModuleRegistry

logging.basicConfig(
    level=logging.INFO if settings.debug else logging.WARNING,
    format="%(asctime)s | %(name)s | %(levelname)s | %(message)s",
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------------------ #
# Lifespan — initialise les composants au démarrage
# ------------------------------------------------------------------ #
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("🚀 Démarrage de %s v%s", settings.app_name, settings.app_version)
    logger.info("Environnement : %s", settings.environment)

    # Initialise la base de données (création des tables en dev)
    if settings.debug:
        logger.info("Création des tables — mode développement")
        await init_db()
        # Bootstrap du premier compte admin (idempotent, dev)
        from app.core.services.seed_service import run_bootstrap_if_needed

        await run_bootstrap_if_needed()

    # Charge les modules activés
    registry = ModuleRegistry()
    await registry.load_modules()
    app.state.module_registry = registry
    logger.info("Modules chargés : %s", registry.list_active_modules())

    yield

    # Cleanup
    await close_db()
    await registry.shutdown()
    logger.info("👋 Arrêt de l'application")


# ------------------------------------------------------------------ #
# Application
# ------------------------------------------------------------------ #
if settings.sentry_dsn:
    sentry_sdk.init(
        dsn=settings.sentry_dsn,
        traces_sample_rate=0.2,
        profiles_sample_rate=0.1,
    )

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    docs_url="/docs" if settings.docs_enabled else None,
    redoc_url="/redoc" if settings.docs_enabled else None,
    # Le schéma OpenAPI n'est pas exposé si la doc est désactivée
    openapi_url=(
        f"{settings.api_v1_prefix}/openapi.json" if settings.docs_enabled else None
    ),
    lifespan=lifespan,
)

# CORS — origines explicites (jamais `*` avec allow_credentials)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routes
app.include_router(api_router, prefix=settings.api_v1_prefix)


@app.get("/health")
async def health_check() -> dict[str, str]:
    """Endpoint de santé."""
    return {"status": "healthy", "app": settings.app_name}


@app.get("/")
async def root() -> dict[str, str]:
    """Point d'accueil."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "docs": "/docs",
        "health": "/health",
    }
