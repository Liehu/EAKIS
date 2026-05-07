from __future__ import annotations

import io
from datetime import timedelta
from typing import IO

from minio import Minio
from minio.error import S3Error

from src.core.settings import get_settings
from src.shared.exceptions import StorageError
from src.shared.logger import get_logger

logger = get_logger("storage")


class StorageClient:
    def __init__(self) -> None:
        settings = get_settings()
        self.default_bucket: str = settings.minio_bucket
        self._client = Minio(
            settings.minio_endpoint,
            access_key=settings.minio_access_key,
            secret_key=settings.minio_secret_key,
            secure=settings.minio_secure,
        )

    def _resolve_bucket(self, bucket: str | None) -> str:
        return bucket or self.default_bucket

    def ensure_bucket(self, bucket: str | None = None) -> None:
        bucket = self._resolve_bucket(bucket)
        try:
            if not self._client.bucket_exists(bucket):
                self._client.make_bucket(bucket)
                logger.info("Created bucket: %s", bucket)
        except S3Error as exc:
            raise StorageError(f"Failed to ensure bucket {bucket}: {exc}") from exc

    def upload(
        self,
        key: str,
        data: bytes | IO[bytes],
        content_type: str = "application/octet-stream",
        bucket: str | None = None,
    ) -> str:
        bucket = self._resolve_bucket(bucket)
        try:
            if isinstance(data, bytes):
                data_stream = io.BytesIO(data)
                length = len(data)
            else:
                length = data.seek(0, io.SEEK_END)
                data.seek(0)
                data_stream = data
            self._client.put_object(
                bucket, key, data_stream, length, content_type=content_type
            )
            logger.info("Uploaded %s to %s", key, bucket)
            return key
        except S3Error as exc:
            raise StorageError(f"Failed to upload {key}: {exc}") from exc

    def download(self, key: str, bucket: str | None = None) -> bytes:
        bucket = self._resolve_bucket(bucket)
        try:
            response = self._client.get_object(bucket, key)
            try:
                return response.read()
            finally:
                response.close()
                response.release_conn()
        except S3Error as exc:
            raise StorageError(f"Failed to download {key}: {exc}") from exc

    def get_presigned_url(
        self, key: str, expires: int = 3600, bucket: str | None = None
    ) -> str:
        bucket = self._resolve_bucket(bucket)
        try:
            return self._client.presigned_get_object(
                bucket, key, expires=timedelta(seconds=expires)
            )
        except S3Error as exc:
            raise StorageError(f"Failed to presign {key}: {exc}") from exc

    def delete(self, key: str, bucket: str | None = None) -> bool:
        bucket = self._resolve_bucket(bucket)
        try:
            self._client.remove_object(bucket, key)
            logger.info("Deleted %s from %s", key, bucket)
            return True
        except S3Error as exc:
            raise StorageError(f"Failed to delete {key}: {exc}") from exc

    def list_objects(self, prefix: str = "", bucket: str | None = None) -> list[str]:
        bucket = self._resolve_bucket(bucket)
        try:
            return [obj.object_name for obj in self._client.list_objects(bucket, prefix=prefix)]
        except S3Error as exc:
            raise StorageError(f"Failed to list objects in {bucket}: {exc}") from exc


_client: StorageClient | None = None


def get_storage_client() -> StorageClient:
    global _client
    if _client is None:
        _client = StorageClient()
    return _client
