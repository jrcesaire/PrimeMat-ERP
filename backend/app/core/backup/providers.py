"""
Fournisseurs de sauvegarde cloud — S3/MinIO, Google Drive, Dropbox, OneDrive.

L'ajout d'un fournisseur ne modifie aucun module métier.
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.backup.base import BackupProvider

logger = logging.getLogger(__name__)


class S3BackupProvider(BackupProvider):
    """Sauvegarde vers S3 / MinIO compatible."""

    name = "s3"

    async def upload_backup(self, file_path: str, remote_name: str) -> str:
        from app.core.storage.s3 import S3Storage
        bucket = self.config.get("bucket", "erp-backups")
        storage = S3Storage(bucket=bucket)
        with open(file_path, "rb") as f:
            data = f.read()
        return await storage.upload(data, remote_name)

    async def download_backup(self, remote_id: str, dest_path: str) -> str:
        from app.core.storage.s3 import S3Storage
        bucket = self.config.get("bucket", "erp-backups")
        storage = S3Storage(bucket=bucket)
        data = await storage.download(remote_id)
        with open(dest_path, "wb") as f:
            f.write(data)
        return dest_path

    async def list_backups(self) -> list[dict[str, Any]]:
        from app.core.storage.s3 import S3Storage
        bucket = self.config.get("bucket", "erp-backups")
        storage = S3Storage(bucket=bucket)
        keys = await storage.list_files()
        return [{"id": k, "name": k} for k in keys]

    async def delete_backup(self, remote_id: str) -> bool:
        from app.core.storage.s3 import S3Storage
        bucket = self.config.get("bucket", "erp-backups")
        storage = S3Storage(bucket=bucket)
        return await storage.delete(remote_id)

    async def test_connection(self) -> bool:
        from app.core.storage.s3 import S3Storage
        bucket = self.config.get("bucket", "erp-backups")
        storage = S3Storage(bucket=bucket)
        try:
            return await storage.get_url("test") is not None
        except Exception:
            return False


class GoogleDriveProvider(BackupProvider):
    """Sauvegarde vers Google Drive (via API OAuth2 service account)."""

    name = "google_drive"

    @property
    def folder_id(self) -> str | None:
        return self.config.get("folder_id")

    async def upload_backup(self, file_path: str, remote_name: str) -> str:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaFileUpload

        creds = Credentials.from_service_account_info(
            self.config.get("credentials", {})
        )
        service = build("drive", "v3", credentials=creds)
        media = MediaFileUpload(file_path, resumable=True)
        parents = [self.folder_id] if self.folder_id else []
        file = service.files().create(
            body={"name": remote_name, "parents": parents},
            media_body=media, fields="id,name",
        ).execute()
        return file.get("id")

    async def download_backup(self, remote_id: str, dest_path: str) -> str:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
        import io

        creds = Credentials.from_service_account_info(
            self.config.get("credentials", {})
        )
        service = build("drive", "v3", credentials=creds)
        request = service.files().get_media(fileId=remote_id)
        fh = io.FileIO(dest_path, "wb")
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.close()
        return dest_path

    async def list_backups(self) -> list[dict[str, Any]]:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_service_account_info(
            self.config.get("credentials", {})
        )
        service = build("drive", "v3", credentials=creds)
        query = (
            f"'{self.folder_id}' in parents and trashed=false"
            if self.folder_id else "trashed=false"
        )
        results = service.files().list(
            q=query, fields="files(id,name,createdTime)"
        ).execute()
        return [
            {"id": f["id"], "name": f["name"], "created": f.get("createdTime")}
            for f in results.get("files", [])
        ]

    async def delete_backup(self, remote_id: str) -> bool:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_service_account_info(
            self.config.get("credentials", {})
        )
        service = build("drive", "v3", credentials=creds)
        service.files().delete(fileId=remote_id).execute()
        return True

    async def test_connection(self) -> bool:
        try:
            result = await self.list_backups()
            return result is not None
        except Exception:
            return False


# Registry — register all available providers
from app.core.backup.cloud_providers import DropboxProvider, OneDriveProvider  # noqa: E402

PROVIDERS: dict[str, type[BackupProvider]] = {
    "s3": S3BackupProvider,
    "google_drive": GoogleDriveProvider,
    "dropbox": DropboxProvider,
    "onedrive": OneDriveProvider,
}


def register_provider(name: str, cls: type[BackupProvider]) -> None:
    """Enregistre un nouveau fournisseur."""
    PROVIDERS[name] = cls


def create_provider(name: str, config: dict[str, Any] | None = None) -> BackupProvider:
    """Factory — crée un fournisseur de sauvegarde par nom."""
    if name not in PROVIDERS:
        raise ValueError(f"Fournisseur inconnu : {name}")
    return PROVIDERS[name](config)
