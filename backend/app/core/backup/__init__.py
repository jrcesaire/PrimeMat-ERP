"""
Sauvegarde cloud — moteur et fournisseurs.

Regroupe le moteur de sauvegarde, les fournisseurs (S3, Google Drive,
Dropbox, OneDrive) et la création d'archives locales.
"""
from app.core.backup.base import BackupProvider
from app.core.backup.providers import PROVIDERS, create_provider
from app.core.backup.cloud_providers import DropboxProvider, OneDriveProvider
from app.core.backup.providers import S3BackupProvider, GoogleDriveProvider
from app.core.backup.engine import BackupEngine
from app.core.backup.local_backup import create_local_backup

__all__ = [
    "BackupProvider",
    "S3BackupProvider",
    "GoogleDriveProvider",
    "DropboxProvider",
    "OneDriveProvider",
    "PROVIDERS",
    "create_provider",
    "BackupEngine",
    "create_local_backup",
]
