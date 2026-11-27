"""Where photos are kept. One interface, three implementations:

- LocalStorage: a folder, for development.
- S3Storage: a private S3-compatible bucket (Backblaze B2) in production.
- MemoryStorage: a dictionary, for tests.

The API streams every photo itself after checking who owns it. Keys are paths such as
"users/<user id>/<photo id>/full.webp", never reused, so a stored file never changes and
browsers can cache it for a year.
"""

import logging
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from functools import lru_cache
from pathlib import Path
from typing import TYPE_CHECKING, Protocol

import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import ConfigError, Settings, get_settings

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


# Deletes run this many at a time, each on its own connection.
DELETE_THREADS = 8


class S3Storage:
    def __init__(self, settings: Settings) -> None:
        self.bucket = settings.s3_bucket or ""
        self.client: S3Client = boto3.client(
            "s3",
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key,
            # Part of every request's signature; Backblaze refuses one signed for another region.
            region_name=settings.s3_region,
            config=Config(
                connect_timeout=5,
                read_timeout=15,
                # One retry at most, as for every external call.
                retries={"max_attempts": 2, "mode": "standard"},
                signature_version="s3v4",
                # Newer boto3 adds checksum headers to every request by default, and Backblaze
                # has refused some of them. Send them only where the S3 protocol requires one.
                request_checksum_calculation="when_required",
                response_checksum_validation="when_required",
                # A page of thumbnails asks for many photos at once; keep the connections open.
                max_pool_connections=20,
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
        # One request per file rather than the bulk delete: the bulk delete must carry a
        # checksum, and boto3 now sends a kind Backblaze has refused. A few at a time, so
        # deleting an account with hundreds of photos takes seconds, not minutes.
        if not keys:
            return
        with ThreadPoolExecutor(max_workers=DELETE_THREADS) as pool:
            failed = sum(not done for done in pool.map(self._delete_one, keys))
        if failed:
            log.warning("Couldn't delete %d of %d stored files", failed, len(keys))

    def _delete_one(self, key: str) -> bool:
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except BotoCoreError, ClientError:
            log.warning("Couldn't delete stored file %s", key, exc_info=True)
            return False
        return True


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


@lru_cache
def get_storage() -> Storage:
    settings = get_settings()
    if settings.storage_backend == "s3":
        return S3Storage(settings)
    if settings.storage_backend == "none":
        # The scheduled jobs never touch photos; anything that tries is a mistake.
        raise ConfigError("STORAGE_BACKEND=none: this process doesn't store photos")
    return LocalStorage(settings.storage_local_dir)
