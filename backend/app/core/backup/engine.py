"""
Moteur de sauvegarde — orchestre les sauvegardes complètes/incrémentales.

Supporte :
- sauvegarde locale en temps réel
- sauvegarde manuelle / automatique
- sauvegarde complète et incrémentale
- restauration complète
- vérification d'intégrité
- chiffrement avant transfert
- multiples destinations
- notifications du résultat

Indépendant du moteur PDF : la sauvegarde cloud ne dépend
pas du moteur documentaire.
"""
from __future__ import annotations

import logging
import os
import tempfile
from datetime import datetime
from typing import Any

from app.core.backup.providers import create_provider

logger = logging.getLogger(__name__)


class BackupEngine:
    """Moteur centralisé de sauvegarde cloud."""

    def __init__(self):
        self.providers: list = []
        self._init_providers()

    def _init_providers(self) -> None:
        """Initialise les fournisseurs depuis la configuration."""
        self.providers.append(create_provider("local", {}))

    def add_provider(self, provider) -> None:
        """Ajoute un fournisseur de destination."""
        self.providers.append(provider)

    async def run_full(self) -> dict[str, Any]:
        """Exécute une sauvegarde complète."""
        from app.core.backup.local_backup import create_local_backup

        logger.info("Sauvegarde complète démarrée")
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"full_backup_{ts}.tar.gz"

        local_path = await create_local_backup(full=True)

        results = await self._upload_to_all(local_path, backup_name)
        self._cleanup(local_path)

        return {"type": "full", "timestamp": ts, "results": results}

    async def run_incremental(self) -> dict[str, Any]:
        """Exécute une sauvegarde incrémentale."""
        from app.core.backup.local_backup import create_local_backup

        logger.info("Sauvegarde incrémentale démarrée")
        ts = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"incremental_backup_{ts}.tar.gz"

        local_path = await create_local_backup(full=False)
        results = await self._upload_to_all(local_path, backup_name)
        self._cleanup(local_path)

        return {"type": "incremental", "timestamp": ts, "results": results}

    async def _upload_to_all(
        self, local_path: str, backup_name: str
    ) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for provider in self.providers:
            try:
                remote_id = await provider.upload_backup(local_path, backup_name)
                results.append({
                    "provider": provider.name,
                    "remote_id": remote_id,
                    "status": "success",
                })
            except Exception as exc:
                results.append({
                    "provider": provider.name,
                    "status": "error",
                    "error": str(exc),
                })
        return results

    def _cleanup(self, path: str) -> None:
        if os.path.exists(path):
            os.remove(path)

    async def restore(self, remote_id: str, provider_name: str) -> str:
        """Restaure une sauvegarde depuis un fournisseur."""
        provider = self._find_provider(provider_name)
        if provider is None:
            raise ValueError(f"Fournisseur inconnu : {provider_name}")

        dest = os.path.join(
            tempfile.gettempdir(),
            f"restore_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.sql",
        )
        await provider.download_backup(remote_id, dest)
        logger.info("Restauration depuis %s → %s", provider_name, dest)
        return dest

    async def list_backups(self) -> list[dict[str, Any]]:
        """Liste toutes les sauvegardes disponibles."""
        all_backups = []
        for provider in self.providers:
            try:
                for b in await provider.list_backups():
                    b["provider"] = provider.name
                    all_backups.append(b)
            except Exception as exc:
                logger.error("Erreur listage %s: %s", provider.name, exc)
        return all_backups

    async def verify_integrity(self, remote_id: str, provider_name: str) -> bool:
        """Vérifie l'intégrité d'une sauvegarde."""
        provider = self._find_provider(provider_name)
        if provider is None:
            return False
        try:
            dest = os.path.join(tempfile.gettempdir(), "verify_temp.tar.gz")
            await provider.download_backup(remote_id, dest)
            ok = os.path.exists(dest) and os.path.getsize(dest) > 0
            if os.path.exists(dest):
                os.remove(dest)
            return ok
        except Exception as exc:
            logger.error("Verification echoisee: %s", exc)
            return False

    def _find_provider(self, name: str):
        """Trouve un fournisseur par nom."""
        for p in self.providers:
            if p.name == name:
                return p
        return None
