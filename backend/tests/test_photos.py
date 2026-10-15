import io
from datetime import UTC, datetime, timedelta

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from photo_support import photo_bytes
from PIL import Image
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.adapters.storage import MemoryStorage, StorageError
from app.core.config import Settings, get_settings
from app.models import ItemImage

PHOTOS = "/api/v1/photos"


def upload(client: TestClient, data: bytes, name: str = "shirt.png", kind: str = "image/png"):  # type: ignore[no-untyped-def]
    return client.post(PHOTOS, files={"file": (name, data, kind)})


def test_an_upload_is_resized_stored_and_given_a_colour(
    sam: TestClient, storage: MemoryStorage
) -> None:
    response = upload(sam, photo_bytes(size=(3000, 4000)))

    assert response.status_code == 201
    photo = response.json()
    assert photo["suggested_color"] == "navy"
    assert (photo["width"], photo["height"]) == (1200, 1600)
    assert len(storage.files) == 2
    thumb = Image.open(io.BytesIO(sam.get(photo["thumb_url"]).content))
    assert thumb.format == "WEBP"
    assert max(thumb.size) == 400


def test_location_and_other_metadata_are_removed(sam: TestClient, storage: MemoryStorage) -> None:
    exif = Image.Exif()
    exif[0x010F] = "PhoneMaker"  # camera make
    exif[0x8825] = {1: "N", 2: (12.0, 58.0, 0.0)}  # GPS position
    response = upload(sam, photo_bytes(fmt="JPEG", exif=exif), "shirt.jpg", "image/jpeg")

    assert response.status_code == 201
    for data in storage.files.values():
        stored = Image.open(io.BytesIO(data))
        assert not stored.getexif()
        assert b"PhoneMaker" not in data


def test_a_sideways_phone_photo_is_turned_upright(sam: TestClient) -> None:
    exif = Image.Exif()
    exif[0x0112] = 6  # orientation: rotate 90 degrees to display
    response = upload(
        sam, photo_bytes(size=(400, 300), fmt="JPEG", exif=exif), "a.jpg", "image/jpeg"
    )

    assert (response.json()["width"], response.json()["height"]) == (300, 400)


def test_a_file_that_isnt_a_photo_is_refused_with_a_reason(
    sam: TestClient, storage: MemoryStorage
) -> None:
    response = upload(sam, b"%PDF-1.7 not a photo", "receipt.png", "image/png")

    assert response.status_code == 422
    assert response.json()["error"]["fields"]["file"] == (
        "That file isn't a photo WearWise can read. Use a JPEG, PNG, or WebP image."
    )
    assert storage.files == {}


def test_a_gif_is_refused_even_though_it_is_an_image(sam: TestClient) -> None:
    buffer = io.BytesIO()
    Image.new("RGB", (10, 10)).save(buffer, format="GIF")

    assert upload(sam, buffer.getvalue(), "a.gif", "image/gif").status_code == 422


def test_an_oversized_file_is_refused_with_its_size(app: FastAPI, sam: TestClient) -> None:
    app.dependency_overrides[get_settings] = lambda: Settings(
        _env_file=None, database_url="postgresql://unused", max_upload_mb=1
    )

    response = upload(sam, b"\0" * (1024 * 1024 * 3 // 2))

    assert response.status_code == 413
    assert response.json()["error"]["message"] == ("That file is 1.5 MB. Photos can be up to 1 MB.")


def test_a_photo_is_visible_only_to_its_owner(sam: TestClient, ana: TestClient) -> None:
    photo = upload(sam, photo_bytes()).json()

    assert sam.get(photo["url"]).headers["content-type"] == "image/webp"
    assert ana.get(photo["url"]).status_code == 404
    assert ana.get(photo["thumb_url"]).status_code == 404


def test_the_browser_keeps_a_photo_for_a_year(sam: TestClient) -> None:
    # A stored file never changes, and each download from the bucket counts against its
    # free allowance, so the browser shouldn't ask twice.
    photo = upload(sam, photo_bytes()).json()

    for url in (photo["url"], photo["thumb_url"]):
        cache = sam.get(url).headers["cache-control"]
        assert cache == "private, max-age=31536000, immutable"


def test_a_photo_when_storage_is_down_is_a_503_with_a_reason(
    sam: TestClient, storage: MemoryStorage, monkeypatch: pytest.MonkeyPatch
) -> None:
    photo = upload(sam, photo_bytes()).json()

    def unreachable(key: str) -> bytes | None:
        raise StorageError("timed out")

    monkeypatch.setattr(storage, "get", unreachable)
    response = sam.get(photo["thumb_url"])

    assert response.status_code == 503
    assert response.json()["error"]["code"] == "storage_unavailable"


def test_photos_need_a_login(client: TestClient) -> None:
    assert upload(client, photo_bytes()).status_code == 401


def test_photos_never_saved_with_an_item_are_cleaned_up(
    sam: TestClient, db: Session, storage: MemoryStorage
) -> None:
    old = upload(sam, photo_bytes()).json()
    db.execute(update(ItemImage).values(created_at=datetime.now(UTC) - timedelta(days=2)))

    upload(sam, photo_bytes())

    assert db.get(ItemImage, old["id"]) is None
    assert len(storage.files) == 2
    assert len(list(db.scalars(select(ItemImage)))) == 1
