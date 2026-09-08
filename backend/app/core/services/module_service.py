"""
Service de gestion des modules — installation, activation, désactivation.
"""
from __future__ import annotations

import importlib
import logging

from app.core.models.module_info import ModuleInfo
from app.core.modules import AVAILABLE_MODULES, CORE_MODULE

logger = logging.getLogger(__name__)


class ModuleService:
    """Service pour installer, activer et désactiver les modules."""

    def __init__(self, session):
        self.session = session

    async def install_module(self, module_name: str) -> ModuleInfo:
        """Installe un module (crée les tables et enregistre le module)."""
        if module_name in AVAILABLE_MODULES.values():
            raise ValueError(f"Module '{module_name}' déjà enregistré")

        if module_name not in AVAILABLE_MODULES:
            raise ValueError(f"Module '{module_name}' non disponible")

        # Importe le module pour que ses modèles soient enregistrés dans Base.metadata
        module_path = AVAILABLE_MODULES[module_name]
        try:
            importlib.import_module(f"{module_path}.models")
        except ImportError:
            pass

        info = ModuleInfo(
            name=module_name, version="0.1.0",
            status="installed", is_active=False, config={},
        )
        self.session.add(info)
        await self.session.commit()
        await self.session.refresh(info)
        logger.info("Module '%s' installé", module_name)
        return info

    async def activate_module(self, module_name: str) -> ModuleInfo:
        """Active un module installé."""
        info = await self._get(module_name)
        if info is None:
            raise ValueError(f"Module '{module_name}' non installé")
        if info.status not in ("installed", "inactive"):
            raise ValueError(
                f"Module '{module_name}' doit être installé (status={info.status})"
            )
        info.status = "active"
        info.is_active = True
        await self.session.commit()
        await self.session.refresh(info)
        logger.info("Module '%s' activé", module_name)
        return info

    async def deactivate_module(self, module_name: str) -> ModuleInfo:
        """Désactive un module (les routes deviennent inaccessibles)."""
        if module_name == CORE_MODULE:
            raise ValueError("Le module Core ne peut pas être désactivé")

        info = await self._get(module_name)
        if info is None:
            raise ValueError(f"Module '{module_name}' inconnu")

        info.is_active = False
        # On garde le statut « installed » pour qu'une réactivation reste possible.
        info.status = "installed"
        await self.session.commit()
        await self.session.refresh(info)
        logger.info("Module '%s' désactivé", module_name)
        return info

    async def _get(self, module_name: str) -> ModuleInfo | None:
        from sqlalchemy import select
        result = await self.session.execute(
            select(ModuleInfo).where(ModuleInfo.name == module_name)
        )
        return result.scalar_one_or_none()

    async def list_all(self) -> list[ModuleInfo]:
        """Liste tous les modules enregistrés."""
        from sqlalchemy import select
        result = await self.session.execute(select(ModuleInfo))
        return list(result.scalars().all())
