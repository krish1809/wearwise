"""Download my data and delete my account: every table that holds a person's data is in the
export, and nothing of theirs is left after deletion."""

import io
import json
import uuid
import zipfile
from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient
from photo_support import photo_bytes
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from wardrobe_support import add_item, save_outfit

from app.adapters.storage import MemoryStorage
from app.models import Base, User
from app.services import export
from app.services.wear import today

EXPORT = "/api/v1/account/export"


def test_every_table_is_someones_or_shared() -> None:
    """A new table must be one or the other, so it's never left out of an export or a
    deletion by accident."""
    owned = {entry.table.name for entry in export.owned_tables()}
    every = set(Base.metadata.tables)

    assert owned & export.SHARED == set()
    assert every - owned - export.SHARED == {"users"}


def test_everything_that_points_at_a_person_goes_with_them() -> None:
    to_users = [
        (table.name, fk.ondelete)
        for table in Base.metadata.sorted_tables
        for fk in table.foreign_keys
        if fk.column.table.name == "users"
    ]

    assert to_users and all(ondelete == "CASCADE" for _, ondelete in to_users)


def fill(client: TestClient) -> None:
    """A little of everything, through the API."""
    client.patch(
        "/api/v1/profile",
        json={"occasion_ids": ["college"], "weekday_occasions": {"0": "college"}},
    )
    client.post("/api/v1/brand-notes", json={"brand": "Levi's", "size_notes": "32 waist"})
    photo = client.post(
        "/api/v1/photos", files={"file": ("shirt.png", photo_bytes(), "image/png")}
    ).json()
    shirt = add_item(client, "casual_shirt", "white", fabric="cotton", photo_id=photo["id"])
    chinos = add_item(client, "chinos", "navy", fabric="cotton")
    loafers = add_item(client, "loafers", "brown", fabric="leather")
    # A second top, clean for the trip once the shirt is worn.
    add_item(client, "casual_shirt", "navy", fabric="cotton")
    outfit = save_outfit(client, shirt, chinos, loafers)
    found = client.post("/api/v1/outfits/suggest", json={"occasion_id": "college"}).json()
    suggestion = found["suggestions"][0]
    client.post(f"/api/v1/suggestions/{suggestion['id']}/feedback", json={"verdict": "like"})
    # Logged after asking: worn pieces wait for a wash before they're suggested again.
    client.post(
        "/api/v1/wear-logs", json={"outfit_id": outfit["id"], "worn_on": today().isoformat()}
    )
    day = (today() + timedelta(days=2)).isoformat()
    client.post("/api/v1/events", json={"day": day, "title": "Seminar", "occasion_id": "college"})
    client.post("/api/v1/plan/generate", json={})
    start = today() + timedelta(days=10)
    client.post(
        "/api/v1/trips",
        json={
            "destination": "Jaipur",
            "latitude": 26.91,
            "longitude": 75.79,
            "start_date": start.isoformat(),
            "end_date": (start + timedelta(days=1)).isoformat(),
            "occasion_id": "college",
        },
    )
    client.post("/api/v1/candidates", json={"category_id": "chinos", "color_primary": "olive"})
    client.post("/api/v1/chat/messages", json={"text": "What do I own?"})


def tables_in(zipped: bytes) -> tuple[dict[str, list[dict[str, Any]]], list[str]]:
    with zipfile.ZipFile(io.BytesIO(zipped)) as archive:
        names = archive.namelist()
        data = json.loads(archive.read("data.json"))["tables"]
    return data, names


def test_download_holds_every_row_and_photo_of_yours_and_nothing_else(
    sam: TestClient, ana: TestClient
) -> None:
    fill(sam)
    add_item(ana, "kurta", "cream")

    response = sam.get(EXPORT)

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/zip"
    assert response.headers["content-disposition"].startswith('attachment; filename="wearwise-')
    data, names = tables_in(response.content)
    filled = {name for name, rows in data.items() if rows}
    # Every kind of thing made above is there.
    assert {
        "users",
        "profiles",
        "brand_notes",
        "items",
        "item_images",
        "outfits",
        "outfit_items",
        "wear_logs",
        "wear_log_items",
        "suggestions",
        "suggestion_feedback",
        "events",
        "plan_days",
        "trips",
        "trip_items",
        "candidates",
        "chat_threads",
        "chat_messages",
        "ai_usage",
    } <= filled
    assert [user["email"] for user in data["users"]] == ["sam@example.com"]
    assert "password_hash" not in data["users"][0] and "sessions" not in data
    assert sorted(item["category_id"] for item in data["items"]) == [
        "casual_shirt",
        "casual_shirt",
        "chinos",
        "loafers",
    ]
    assert [f"photos/{image['id']}.webp" for image in data["item_images"]] == [
        name for name in names if name.startswith("photos/")
    ]
    assert "README.txt" in names


def test_downloads_are_limited(sam: TestClient) -> None:
    statuses = [sam.get(EXPORT).status_code for _ in range(6)]

    assert statuses == [200] * 5 + [429]


def test_deleting_the_account_leaves_nothing_behind(
    sam: TestClient, ana: TestClient, db: Session, storage: MemoryStorage
) -> None:
    fill(sam)
    fill(ana)
    user = db.scalar(select(User).where(User.email == "sam@example.com"))
    assert user is not None
    theirs = {
        name: [row["id"] for row in rows]
        for name, rows in export.rows_for(db, user).items()
        if rows and "id" in rows[0]
    }
    photos = set(storage.files)
    anas = db.scalar(select(User).where(User.email == "ana@example.com"))
    assert anas is not None
    anas_rows = {name: len(rows) for name, rows in export.rows_for(db, anas).items()}

    deleted = sam.post("/api/v1/account/delete", json={"confirm_email": "sam@example.com"})

    assert deleted.status_code == 204
    left = {
        name: db.scalar(
            select(func.count())
            .select_from(Base.metadata.tables[name])
            .where(Base.metadata.tables[name].c.id.in_([uuid.UUID(i) for i in ids]))
        )
        for name, ids in theirs.items()
    }
    assert set(left.values()) == {0}, left
    # Only Ana's photos are left, and her rows are untouched.
    assert len(storage.files) < len(photos) and storage.files
    assert {name: len(rows) for name, rows in export.rows_for(db, anas).items()} == anas_rows


def test_rate_limit_counts_naming_an_ip_are_gone_within_a_day(db: Session) -> None:
    from datetime import UTC, datetime

    from app.models import RateLimitHit
    from app.services import rate_limit

    now = datetime.now(UTC)
    db.add(RateLimitHit(bucket="login:ip:203.0.113.9", window_start=now - timedelta(days=2)))
    db.add(RateLimitHit(bucket="login:ip:203.0.113.8", window_start=now - timedelta(hours=2)))
    db.flush()

    rate_limit.hit(db, "login:ip:198.51.100.1", rate_limit.Limit(5, timedelta(minutes=15)), now)

    left = set(db.scalars(select(RateLimitHit.bucket)))
    assert "login:ip:203.0.113.9" not in left
    # Someone else's recent count stays; it's still under a day old.
    assert {"login:ip:203.0.113.8", "login:ip:198.51.100.1"} <= left
