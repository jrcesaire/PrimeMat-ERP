"""
Routeur API principal.

Inclut les routeurs de chaque module.  Le Core est toujours chargé ;
les modules métier sont inclus dynamiquement si activés.
"""
from __future__ import annotations

import logging

from fastapi import APIRouter

from app.core.api import router as core_router

logger = logging.getLogger(__name__)

api_router = APIRouter()

# Core — toujours disponible
api_router.include_router(core_router, prefix="/core")

# Mapping module -> préfixe API
MODULE_ROUTES: dict[str, tuple[str, str]] = {
    "catalogue": ("/catalogue", "app.modules.catalogue.api"),
    "crm": ("/crm", "app.modules.crm.api"),
    "sales": ("/sales", "app.modules.sales.api"),
    "stock": ("/stock", "app.modules.stock.api"),
    "purchases": ("/purchases", "app.modules.purchases.api"),
    "delivery": ("/delivery", "app.modules.delivery.api"),
    "invoicing": ("/invoicing", "app.modules.invoicing.api"),
    "payments": ("/payments", "app.modules.payments.api"),
    "finance": ("/finance", "app.modules.finance.api"),
    "reporting": ("/reporting", "app.modules.reporting.api"),
    "accounting": ("/accounting", "app.modules.accounting.api"),
}

# Catalogue chargé par défaut (socle réutilisable)
try:
    from app.modules.catalogue.api import routers as catalogue_routers

    for r in catalogue_routers:
        api_router.include_router(r, prefix="/catalogue", tags=["catalogue"])
except Exception:  # noqa: BLE001
    logger.exception("Erreur lors du chargement du module catalogue")


# Modules métier — chargés dynamiquement si disponibles
for _module_name, (_prefix, _api_path) in MODULE_ROUTES.items():
    if _module_name == "catalogue":
        continue  # déjà chargé
    try:
        _mod = __import__(_api_path, fromlist=["routers"])
        for _r in getattr(_mod, "routers", []):
            api_router.include_router(_r, prefix=_prefix, tags=[_module_name])
    except Exception:  # noqa: BLE001
        logger.info("Module %s non chargé (non installé ou incomplet)", _module_name)


def include_module_routers(active_modules: list[str]) -> None:
    """Inclut les routeurs des modules actifs (extension runtime)."""
    for module_name in active_modules:
        if module_name not in MODULE_ROUTES or module_name == "catalogue":
            continue
        prefix, module_api_path = MODULE_ROUTES[module_name]
        try:
            module = __import__(module_api_path, fromlist=["routers"])
            module_routers = getattr(module, "routers", [])
            for r in module_routers:
                api_router.include_router(r, prefix=prefix, tags=[module_name])
        except Exception:  # noqa: BLE001
            logger.exception("Erreur lors du chargement du module %s", module_name)
