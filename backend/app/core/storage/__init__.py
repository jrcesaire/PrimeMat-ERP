"""
Abstraction du stockage de fichiers — interface et factory.

Fournit une interface unifiée pour stocker et récupérer des fichiers
peu importe le backend (S3/MinIO, local, etc.).

Indépendant des modules métier : le stockage cloud ne dépend pas des Ventes.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class StorageInterface:
    """Interface abstraite pour le stockage de fichiers."""

    async def upload(self, file_data: bytes, key: str, **kwargs: Any) -> str:
        """Téléverse un fichier. Retourne l'URL/le chemin."""
        raise NotImplementedError

    async def download(self, key: str) -> bytes:
        """Télécharge un fichier."""
        raise NotImplementedError

    async def delete(self, key: str) -> bool:
        """Supprime un fichier."""
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        """Vérifie si un fichier existe."""
        raise NotImplementedError

    async def list_files(self, prefix: str = "") -> list[str]:
        """Liste les fichiers avec un préfixe."""
        raise NotImplementedError

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        """Génère une URL signée pour télécharger le fichier."""
        raise NotImplementedError


def get_storage() -> StorageInterface:
    """Retourne l'instance de stockage appropriée selon la configuration."""
    if settings.s3_access_key and settings.s3_secret_key:
        from app.core.storage.s3 import S3Storage
        logger.info("Utilisation du stockage S3/MinIO")
        return S3Storage()

    from app.core.storage.local import LocalStorage
    logger.info("Utilisation du stockage local")
    return LocalStorage()


# Instance singleton
storage: StorageInterface = get_storage()
