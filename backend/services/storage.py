"""
Storage Abstraction Layer — Cloudflare R2 / S3 compatible storage.
Supports local filesystem fallback for development.
"""
import os
import io
import structlog
from typing import Optional, BinaryIO, Dict, Any
from datetime import datetime
from urllib.parse import urljoin

log = structlog.get_logger()


class StorageBackend:
    """Abstract storage backend."""

    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        raise NotImplementedError

    async def download(self, key: str) -> Optional[bytes]:
        raise NotImplementedError

    async def delete(self, key: str) -> bool:
        raise NotImplementedError

    async def exists(self, key: str) -> bool:
        raise NotImplementedError

    def get_url(self, key: str) -> str:
        raise NotImplementedError


class LocalStorageBackend(StorageBackend):
    """Local filesystem storage for development."""

    def __init__(self, base_path: str = "/tmp/ai-architect-artifacts"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)
        log.info("local_storage_initialized", path=base_path)

    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        filepath = os.path.join(self.base_path, key)
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "wb") as f:
            f.write(data)
        log.info("storage_uploaded", key=key, size=len(data))
        return self.get_url(key)

    async def download(self, key: str) -> Optional[bytes]:
        filepath = os.path.join(self.base_path, key)
        if not os.path.exists(filepath):
            return None
        with open(filepath, "rb") as f:
            return f.read()

    async def delete(self, key: str) -> bool:
        filepath = os.path.join(self.base_path, key)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

    async def exists(self, key: str) -> bool:
        return os.path.exists(os.path.join(self.base_path, key))

    def get_url(self, key: str) -> str:
        return f"file://{os.path.join(self.base_path, key)}"


class R2StorageBackend(StorageBackend):
    """Cloudflare R2 (S3-compatible) storage for production."""

    def __init__(
        self,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        public_url_base: Optional[str] = None,
    ):
        import boto3
        self.client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
        )
        self.bucket = bucket
        self.public_url_base = public_url_base or f"{endpoint_url}/{bucket}"
        self._ensure_bucket()
        log.info("r2_storage_initialized", bucket=bucket)

    def _ensure_bucket(self):
        try:
            self.client.head_bucket(Bucket=self.bucket)
        except Exception:
            self.client.create_bucket(Bucket=self.bucket)
            log.info("r2_bucket_created", bucket=self.bucket)

    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        self.client.put_object(
            Bucket=self.bucket,
            Key=key,
            Body=data,
            ContentType=content_type,
        )
        log.info("r2_uploaded", key=key, size=len(data))
        return self.get_url(key)

    async def download(self, key: str) -> Optional[bytes]:
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except Exception:
            return None

    async def delete(self, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    async def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
            return True
        except Exception:
            return False

    def get_url(self, key: str) -> str:
        return f"{self.public_url_base}/{key}"


class StorageManager:
    """Singleton storage manager with backend auto-selection."""

    def __init__(self):
        self._backend: Optional[StorageBackend] = None
        self._initialized = False

    def initialize(self, settings: Any = None):
        if self._initialized:
            return
        if settings and getattr(settings, "cloudflare_r2_endpoint", None):
            self._backend = R2StorageBackend(
                endpoint_url=settings.cloudflare_r2_endpoint,
                access_key=settings.cloudflare_r2_access_key,
                secret_key=settings.cloudflare_r2_secret_key,
                bucket=getattr(settings, "cloudflare_r2_bucket", "ai-architect-artifacts"),
                public_url_base=getattr(settings, "cloudflare_r2_public_url", None),
            )
            log.info("storage_manager_using_r2")
        else:
            self._backend = LocalStorageBackend(
                base_path=os.environ.get("ARTIFACT_STORAGE_PATH", "/tmp/ai-architect-artifacts")
            )
            log.info("storage_manager_using_local")
        self._initialized = True

    @property
    def backend(self) -> StorageBackend:
        if not self._backend:
            self.initialize()
        return self._backend

    async def upload(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> str:
        return await self.backend.upload(key, data, content_type)

    async def download(self, key: str) -> Optional[bytes]:
        return await self.backend.download(key)

    async def delete(self, key: str) -> bool:
        return await self.backend.delete(key)

    def get_url(self, key: str) -> str:
        return self.backend.get_url(key)


storage_manager = StorageManager()
