"""
Registre des modules — charge et suit l'état des modules métier.

Le Core est toujours actif. Les modules métier peuvent être installés,
activés, désactivés ou désinstallés indépendamment.
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.core.models.module_info import ModuleInfo

logger = logging.getLogger(__name__)

CORE_MODULE = "core"

AVAILABLE_MODULES: dict[str, str] = {
    "catalogue": "app.modules.catalogue",
    "crm": "app.modules.crm",
    "sales": "app.modules.sales",
    "stock": "app.modules.stock",
    "purchases": "app.modules.purchases",
    "delivery": "app.modules.delivery",
    "invoicing": "app.modules.invoicing",
    "payments": "app.modules.payments",
    "finance": "app.modules.finance",
    "reporting": "app.modules.reporting",
    "accounting": "app.modules.accounting",
}


class ModuleRegistry:
    """Gère le cycle de vie et l'état des modules du système."""

    def __init__(self):
        self.modules: dict[str, ModuleInfo] = {}
        self._initialized = False

    async def load_modules(self) -> None:
        """Charge l'état des modules depuis la base de données.

        Les modules par défaut (config ``default_modules``) sont persistés
        dans ``module_infos`` s'ils n'existent pas encore, afin que l'état
        soit lisible via la base (et l'API de gestion des modules).
        """
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import select

        async with AsyncSessionLocal() as session:
            result = await session.execute(select(ModuleInfo))
            for module in result.scalars().all():
                self.modules[module.name] = module

            # Core toujours actif — persiste s'il manque
            if CORE_MODULE not in self.modules:
                core = ModuleInfo(
                    name=CORE_MODULE, version=settings.app_version,
                    status="active", is_active=True,
                )
                session.add(core)
                self.modules[CORE_MODULE] = core

            # Modules par défaut — persiste ceux qui manquent
            for name in settings.default_modules:
                if name not in self.modules:
                    info = ModuleInfo(
                        name=name, version="0.1.0",
                        status="installed", is_active=True,
                    )
                    session.add(info)
                    self.modules[name] = info

            await session.commit()

        self._initialized = True
        logger.info("Modules chargés : %s", self.list_active_modules())

    async def shutdown(self) -> None:
        """Nettoie les ressources à l'arrêt."""
        pass

    def is_module_active(self, module_name: str) -> bool:
        """Vérifie si un module est actif."""
        info = self.modules.get(module_name)
        return info is not None and info.is_active and info.status == "active"

    def list_active_modules(self) -> list[str]:
        """Liste les modules actifs."""
        return [
            name for name, info in self.modules.items()
            if info.is_active and info.status == "active"
        ]

    def get_module_info(self, module_name: str) -> ModuleInfo | None:
        return self.modules.get(module_name)

    def get_module_config(self, module_name: str) -> dict[str, Any]:
        info = self.modules.get(module_name)
        return info.config or {} if info else {}

    def set_module_config(
        self, module_name: str, config: dict[str, Any]
    ) -> None:
        info = self.modules.get(module_name)
        if info is None:
            raise ValueError(f"Module '{module_name}' inconnu")
        info.config = config
