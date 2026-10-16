"""The S3 adapter, checked against the requests boto3 would send, without a network.

Each request is caught just before it leaves and answered with a canned response, so a test can
see the exact URL and headers Backblaze would receive.
"""

import io
import logging
from collections.abc import Iterator
from typing import Any

import pytest
from botocore.awsrequest import AWSPreparedRequest, AWSResponse
from botocore.compat import HTTPHeaders

from app.adapters.storage import S3Storage, StorageError
from app.core.config import Settings

ENDPOINT = "s3.eu-central-003.backblazeb2.com"


class _Body(io.BytesIO):
    """A response body in the shape botocore reads it."""

    def stream(self, **kwargs: Any) -> Iterator[bytes]:
        yield self.read()


class FakeBucket:
    """Records each request and answers it; keys in `refuse` get 403 Access Denied."""

    def __init__(
        self, files: dict[str, bytes] | None = None, refuse: frozenset[str] = frozenset()
    ) -> None:
        self.files = files or {}
        self.refuse = refuse
        self.requests: list[AWSPreparedRequest] = []

    def answer(self, request: AWSPreparedRequest, **kwargs: Any) -> AWSResponse:
        self.requests.append(request)
        key = request.url.split("?")[0].rsplit("/", 1)[-1]
        if key in self.refuse:
            return self._error(403, "AccessDenied")
        if request.method == "GET":
            if key not in self.files:
                return self._error(404, "NoSuchKey")
            return AWSResponse(request.url, 200, HTTPHeaders(), _Body(self.files[key]))
        status = 204 if request.method == "DELETE" else 200
        return AWSResponse(request.url, status, HTTPHeaders(), _Body())

    def _error(self, status: int, code: str) -> AWSResponse:
        body = f"<Error><Code>{code}</Code><Message>{code}</Message></Error>".encode()
        return AWSResponse("", status, HTTPHeaders(), _Body(body))


def make_storage(bucket: FakeBucket) -> S3Storage:
    settings = Settings(
        _env_file=None,
        database_url="postgresql://u:p@localhost/db",
        storage_backend="s3",
        # Pasted exactly as Backblaze shows it, without https://.
        s3_endpoint_url=ENDPOINT,
        s3_region="eu-central-003",
        s3_bucket="wearwise-photos",
        s3_access_key_id="key-id",
        s3_secret_access_key="secret",
    )
    storage = S3Storage(settings)
    # The stubs say handlers return None, but a before-send handler may return the response.
    storage.client.meta.events.register("before-send.s3", bucket.answer)  # type: ignore[arg-type]
    return storage


def test_requests_go_to_the_endpoint_signed_for_its_region() -> None:
    bucket = FakeBucket()

    make_storage(bucket).put("users/1/full.webp", b"photo", "image/webp")

    (request,) = bucket.requests
    assert request.url.startswith("https://")
    assert ENDPOINT in request.url
    signature = request.headers["Authorization"]
    if isinstance(signature, bytes):
        signature = signature.decode()
    assert "/eu-central-003/s3/aws4_request" in signature


def test_requests_carry_no_checksum_headers() -> None:
    # Backblaze has refused the checksum headers newer boto3 adds by default.
    bucket = FakeBucket(files={"thumb.webp": b"photo"})
    storage = make_storage(bucket)

    storage.put("full.webp", b"photo", "image/webp")
    storage.get("thumb.webp")
    storage.delete(["full.webp", "thumb.webp"])

    for request in bucket.requests:
        names = [name.lower() for name in request.headers]
        assert not [name for name in names if "checksum" in name], request.url


def test_delete_sends_one_request_per_file_instead_of_a_bulk_delete() -> None:
    bucket = FakeBucket()
    keys = [f"users/1/photo-{n}/full.webp" for n in range(20)]

    make_storage(bucket).delete(keys)

    assert {request.method for request in bucket.requests} == {"DELETE"}
    assert not [request for request in bucket.requests if "?delete" in request.url]
    assert sorted(request.url.split(".com/")[-1] for request in bucket.requests) == sorted(
        f"wearwise-photos/{key}" for key in keys
    )


def test_a_failed_delete_is_logged_and_the_rest_still_go(
    caplog: pytest.LogCaptureFixture,
) -> None:
    bucket = FakeBucket(refuse=frozenset({"stuck.webp"}))

    with caplog.at_level(logging.WARNING):
        make_storage(bucket).delete(["one.webp", "stuck.webp", "two.webp"])

    assert len(bucket.requests) == 3
    assert "Couldn't delete 1 of 3 stored files" in caplog.text


def test_get_returns_the_file_or_none_when_it_is_missing() -> None:
    storage = make_storage(FakeBucket(files={"thumb.webp": b"photo"}))

    assert storage.get("thumb.webp") == b"photo"
    assert storage.get("gone.webp") is None


def test_a_refused_upload_raises_a_storage_error() -> None:
    storage = make_storage(FakeBucket(refuse=frozenset({"full.webp"})))

    with pytest.raises(StorageError):
        storage.put("full.webp", b"photo", "image/webp")
