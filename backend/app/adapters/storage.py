"""Where photos are kept. One interface, three implementations:

- LocalStorage: a folder, for development. The API streams files after checking who owns them.
- S3Storage: an S3-compatible bucket (Cloudflare R2) in production. The bucket stays private;
  the API hands out links that work for a few minutes.
- MemoryStorage: a dictionary, for tests.

Keys are paths such as "users/<user id>/<photo id>/full.webp", never reused, so a stored file
never changes and browsers can cache it.
"""

import logging
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import Settings, get_settings

if TYPE_CHECKING:
    from types_boto3_s3 import S3Client

log = logging.getLogger(__name__)


class StorageError(Exception):
    """The storage backend couldn't be reached or refused the request."""


class Storage(Protocol):
    def put(self, key: str, data: bytes, content_type: str) -> None: ...

    def get(self, key: str) -> bytes | None:
        """The file's bytes, or None if there is no such file."""
        ...

    def delete(self, keys: Sequence[str]) -> None:
        """Remove files. Missing ones are ignored, and failures are logged rather than raised,
        because this runs after the database change it belongs to has been committed."""
        ...

    def link(self, key: str, seconds: int) -> str | None:
        """A link that works without logging in, for a limited time; None if the API must
        stream the file itself."""
        ...


class LocalStorage:
    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        path = (self.root / key).resolve()
        # Keys are made by the app, but a bad one must never reach outside the folder.
        if not path.is_relative_to(self.root.resolve()):
            raise StorageError(f"Key outside the storage folder: {key}")
        return path

    def put(self, key: str, data: bytes, content_type: str) -> None:
        path = self._path(key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        except OSError as error:
            raise StorageError(str(error)) from error

    def get(self, key: str) -> bytes | None:
        path = self._path(key)
        return path.read_bytes() if path.is_file() else None

    def delete(self, keys: Sequence[str]) -> None:
        for key in keys:
            try:
                self._path(key).unlink(missing_ok=True)
            except OSError:
                log.warning("Couldn't delete stored file %s", key, exc_info=True)

    def link(self, key: str, seconds: int) -> str | None:
        return None


class S3Storage:
    def __init__(self, settings: Settings) -> None:
        self.bucket = settings.s3_bucket or ""
        self.client: S3Client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            # R2 ignores the region, but the signing code needs one.
            region_name="auto",
            config=Config(
                connect_timeout=5,
                read_timeout=15,
                # One retry at most, as for every external call.
                retries={"max_attempts": 2, "mode": "standard"},
                signature_version="s3v4",
            ),
        )

    def put(self, key: str, data: bytes, content_type: str) -> None:
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
                CacheControl="private, max-age=31536000, immutable",
            )
        except (BotoCoreError, ClientError) as error:
            raise StorageError(str(error)) from error

    def get(self, key: str) -> bytes | None:
        try:
            return self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except self.client.exceptions.NoSuchKey:
            return None
        except (BotoCoreError, ClientError) as error:
            raise StorageError(str(error)) from error

    def delete(self, keys: Sequence[str]) -> None:
        # The API deletes up to 1,000 keys per request.
        for start in range(0, len(keys), 1000):
            batch = keys[start : start + 1000]
            try:
                self.client.delete_objects(
                    Bucket=self.bucket,
                    Delete={"Objects": [{"Key": key} for key in batch], "Quiet": True},
                )
            except BotoCoreError, ClientError:
                log.warning("Couldn't delete %d stored files", len(batch), exc_info=True)

    def link(self, key: str, seconds: int) -> str | None:
        return self.client.generate_presigned_url(
            "get_object", Params={"Bucket": self.bucket, "Key": key}, ExpiresIn=seconds
        )


class MemoryStorage:
    """For tests: keeps files in a dictionary."""

    def __init__(self) -> None:
        self.files: dict[str, bytes] = {}

    def put(self, key: str, data: bytes, content_type: str) -> None:
        self.files[key] = data

    def get(self, key: str) -> bytes | None:
        return self.files.get(key)

    def delete(self, keys: Sequence[str]) -> None:
        for key in keys:
            self.files.pop(key, None)

    def link(self, key: str, seconds: int) -> str | None:
        return None


@lru_cache
def get_storage() -> Storage:
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3Storage(settings)
    return LocalStorage(settings.storage_local_dir)
