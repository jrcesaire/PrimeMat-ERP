"""Fournisseurs Dropbox et OneDrive pour la sauvegarde cloud."""
from __future__ import annotations

import logging
from typing import Any

from app.core.backup.base import BackupProvider

logger = logging.getLogger(__name__)


class DropboxProvider(BackupProvider):
    """Sauvegarde vers Dropbox."""

    name = "dropbox"
    base_path: str = "/ERP Backups"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.base_path = self.config.get("base_path", self.base_path)

    async def upload_backup(self, file_path: str, remote_name: str) -> str:
        import dropbox
        dbx = dropbox.Dropbox(self.config.get("access_token"))
        remote_path = f"{self.base_path}/{remote_name}"
        with open(file_path, "rb") as f:
            dbx.files_upload(f.read(), remote_path)
        return remote_path

    async def download_backup(self, remote_id: str, dest_path: str) -> str:
        import dropbox
        dbx = dropbox.Dropbox(self.config.get("access_token"))
        dbx.files_download_to_file(dest_path, remote_id)
        return dest_path

    async def list_backups(self) -> list[dict[str, Any]]:
        import dropbox
        dbx = dropbox.Dropbox(self.config.get("access_token"))
        try:
            result = dbx.files_list_folder(self.base_path)
            return [
                {"id": entry.id, "name": entry.name}
                for entry in result.entries
            ]
        except Exception:
            return []

    async def delete_backup(self, remote_id: str) -> bool:
        import dropbox
        dbx = dropbox.Dropbox(self.config.get("access_token"))
        dbx.files_delete_v2(remote_id)
        return True

    async def test_connection(self) -> bool:
        import dropbox
        try:
            dbx = dropbox.Dropbox(self.config.get("access_token"))
            dbx.users_get_current_account()
            return True
        except Exception:
            return False


class OneDriveProvider(BackupProvider):
    """Sauvegarde vers Microsoft OneDrive (via Microsoft Graph API)."""

    name = "onedrive"
    base_path: str = "/ERP Backups"

    def __init__(self, config: dict[str, Any] | None = None):
        super().__init__(config)
        self.base_path = self.config.get("base_path", self.base_path)

    async def upload_backup(self, file_path: str, remote_name: str) -> str:
        import httpx
        token = self.config.get("access_token")
        url = (
            f"https://graph.microsoft.com/v1.0/me/drive/root:"
            f"{self.base_path}/{remote_name}:/content"
        )
        with open(file_path, "rb") as f:
            resp = httpx.put(
                url,
                headers={"Authorization": f"Bearer {token}"},
                files={"file": f},
            )
        resp.raise_for_status()
        return resp.json().get("id", remote_name)

    async def download_backup(self, remote_id: str, dest_path: str) -> str:
        import httpx
        token = self.config.get("access_token")
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{remote_id}/content"
        resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"})
        resp.raise_for_status()
        with open(dest_path, "wb") as f:
            f.write(resp.content)
        return dest_path

    async def list_backups(self) -> list[dict[str, Any]]:
        import httpx
        token = self.config.get("access_token")
        url = f"https://graph.microsoft.com/v1.0/me/drive/root:{self.base_path}:/children"
        resp = httpx.get(url, headers={"Authorization": f"Bearer {token}"})
        if resp.status_code != 200:
            return []
        return [
            {"id": item["id"], "name": item["name"]}
            for item in resp.json().get("value", [])
        ]

    async def delete_backup(self, remote_id: str) -> bool:
        import httpx
        token = self.config.get("access_token")
        url = f"https://graph.microsoft.com/v1.0/me/drive/items/{remote_id}"
        httpx.delete(url, headers={"Authorization": f"Bearer {token}"})
        return True

    async def test_connection(self) -> bool:
        try:
            return await self.list_backups() is not None
        except Exception:
            return False
