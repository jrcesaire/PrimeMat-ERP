"""
Stockage S3 / MinIO — implémentation asynchrone via ``aioboto3``.
"""
from __future__ import annotations

import logging
from typing import Any

from app.core.config import settings
from app.core.storage import StorageInterface

logger = logging.getLogger(__name__)


def _s3_session_kwargs() -> dict[str, Any]:
    """Construit les kwargs pour la session aioboto3."""
    kwargs: dict[str, Any] = {}
    if settings.s3_access_key:
        kwargs["aws_access_key_id"] = settings.s3_access_key
    if settings.s3_secret_key:
        kwargs["aws_secret_access_key"] = settings.s3_secret_key
    if settings.s3_endpoint_url:
        kwargs["endpoint_url"] = settings.s3_endpoint_url
    if settings.s3_region:
        kwargs["region_name"] = settings.s3_region
    return kwargs


class S3Storage(StorageInterface):
    """Stockage sur cluster S3 / MinIO compatible."""

    def __init__(self, bucket: str | None = None):
        self.bucket = bucket or settings.s3_bucket_name

    async def _client(self):
        import aioboto3
        return aioboto3.Session(**_s3_session_kwargs())

    async def upload(self, file_data: bytes, key: str, **kwargs: Any) -> str:
        session = await self._client()
        async with session.client("s3") as client:
            await client.put_object(
                Bucket=self.bucket, Key=key, Body=file_data, **kwargs
            )
            logger.info("Uploaded: s3://%s/%s", self.bucket, key)
            return f"s3://{self.bucket}/{key}"

    async def download(self, key: str) -> bytes:
        session = await self._client()
        async with session.client("s3") as client:
            response = await client.get_object(Bucket=self.bucket, Key=key)
            async with response["Body"] as body:
                return await body.read()

    async def delete(self, key: str) -> bool:
        session = await self._client()
        async with session.client("s3") as client:
            await client.delete_object(Bucket=self.bucket, Key=key)
            return True

    async def exists(self, key: str) -> bool:
        session = await self._client()
        async with session.client("s3") as client:
            try:
                await client.head_object(Bucket=self.bucket, Key=key)
                return True
            except Exception:
                return False

    async def list_files(self, prefix: str = "") -> list[str]:
        session = await self._client()
        async with session.client("s3") as client:
            paginator = client.get_paginator("list_objects_v2")
            keys: list[str] = []
            async for page in paginator.paginate(
                Bucket=self.bucket, Prefix=prefix
            ):
                for obj in page.get("Contents", []):
                    keys.append(obj["Key"])
            return keys

    async def get_url(self, key: str, expires_in: int = 3600) -> str:
        session = await self._client()
        async with session.client("s3") as client:
            return await client.generate_presigned_url(
                "get_object",
                Params={"Bucket": self.bucket, "Key": key},
                ExpiresIn=expires_in,
            )
