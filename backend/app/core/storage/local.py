"""
Stockage local — pour le développement et les tests.

Permet de tester l'application sans serveur S3/MinIO.
"""
from __future__ import annotations

import logging
import os
from typing import Any

from app.core.storage import StorageInterface

logger = logging.getLogger(__name__)


class LocalStorage(StorageInterface):
    """
    Stockage sur le système de fichiers local.

    Les fichiers sont stockés dans ``BASE_DIR/storage/uploads``.
    """

    def __init__(self, base_path: str | None = None):
        self.base_path = base_path or os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
            ))),
            "storage",
            "uploads",
        )
        os.makedirs(self.base_path, exist_ok=True)

    def _full_path(self, key: str) -> str:
        """Convertit une clé en chemin de fichier local (sécurisé)."""
        safe_key = key.lstrip("/").replace("..", "_").replace("\\", "/")
        return os.path.join(self.base_path, safe_key)

    async def upload(self, file_data: bytes, key: str, **kwargs: Any) -> str:
        path = self._full_path(key)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "wb") as f:
            f.write(file_data)
        return f"local://{key}"

    async def download(self, key: str) -> bytes:
        path = self._full_path(key)
        with open(path, "rb") as f:
            return f.read()

    async def delete(self, key: str) -> bool:
        path = self._full_path(key)
        if os.path.exists(path):
            os.remove(path)
            return True
        return False

    async def exists(self, key: str) -> bool:
        return os.path.exists(self._full_path(key))

    async def list_files(self, prefix: str = "") -> list[str]:
        prefix_path = os.path.join(self.base_path, prefix)
        keys: list[str] = []
        if os.path.exists(prefix_path):
            for root, _, files in os.walk(prefix_path):
                for f in files:
                    full = os.path.join(root, f)
                    rel = os.path.relpath(full, self.base_path)
                    keys.append(rel.replace("\\", "/"))
        return keys

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        return f"/files/{key}"
