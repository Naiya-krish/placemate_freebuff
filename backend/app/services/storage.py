"""S3-compatible object storage with a local filesystem fallback for tests/dev."""

from __future__ import annotations

import logging
import time
from functools import lru_cache
from pathlib import Path
from typing import Protocol

from app.core.config import settings

logger = logging.getLogger(__name__)


class ObjectStorage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes: ...

    def delete(self, key: str) -> None: ...


class LocalStorage:
    def __init__(self, base_dir: str) -> None:
        self.base = Path(base_dir).resolve()
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        candidate = (self.base / key).resolve()
        if not str(candidate).startswith(str(self.base)):
            raise ValueError("invalid storage key")
        candidate.parent.mkdir(parents=True, exist_ok=True)
        return candidate

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self._path(key).write_bytes(data)

    def get(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    def delete(self, key: str) -> None:
        path = self._path(key)
        if path.exists():
            path.unlink()


class S3Storage:
    def __init__(self) -> None:
        import boto3
        from botocore.config import Config

        self.bucket = settings.storage_bucket
        self.client = boto3.client(
            "s3",
            endpoint_url=settings.storage_endpoint or None,
            aws_access_key_id=settings.storage_key or None,
            aws_secret_access_key=settings.storage_secret or None,
            region_name=settings.storage_region,
            use_ssl=settings.storage_secure,
            config=Config(signature_version="s3v4", retries={"max_attempts": 3}),
        )
        self._ensure_bucket()

    def _ensure_bucket(self) -> None:
        for attempt in range(5):
            try:
                self.client.head_bucket(Bucket=self.bucket)
                return
            except Exception:
                try:
                    self.client.create_bucket(Bucket=self.bucket)
                    return
                except Exception as exc:  # pragma: no cover - depends on external service
                    logger.warning(
                        "storage bucket not ready (attempt %s): %s", attempt + 1, type(exc).__name__
                    )
                    time.sleep(2)
        logger.error("could not ensure bucket %s", self.bucket)

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
            ServerSideEncryption="AES256",
        )

    def get(self, key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=key)
        body: bytes = response["Body"].read()
        return body

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


@lru_cache
def get_storage() -> ObjectStorage:
    if settings.storage_backend.lower() == "s3":
        return S3Storage()
    return LocalStorage(settings.storage_local_dir)
