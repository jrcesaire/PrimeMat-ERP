"""
Interface abstraite pour les fournisseurs de sauvegarde cloud.

Un module métier peut demander une sauvegarde sans connaître le
fournisseur : l'abstraction est assurée par ``BackupProvider``.
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any

logger = logging.getLogger(__name__)


class BackupProvider(ABC):
    """Interface abstraite pour un fournisseur de sauvegarde."""

    name: str = "base"

    def __init__(self, config: dict[str, Any] | None = None):
        self.config = config or {}

    @abstractmethod
    async def upload_backup(self, file_path: str, remote_name: str) -> str:
        """Téléverse un fichier. Retourne l'ID ou chemin distant."""
        raise NotImplementedError

    @abstractmethod
    async def download_backup(self, remote_id: str, dest_path: str) -> str:
        """Télécharge une sauvegarde. Retourne le chemin local."""
        raise NotImplementedError

    @abstractmethod
    async def list_backups(self) -> list[dict[str, Any]]:
        """Liste les sauvegardes disponibles."""
        raise NotImplementedError

    @abstractmethod
    async def delete_backup(self, remote_id: str) -> bool:
        """Supprime une sauvegarde."""
        raise NotImplementedError

    @abstractmethod
    async def test_connection(self) -> bool:
        """Teste la connexion au service."""
        raise NotImplementedError
