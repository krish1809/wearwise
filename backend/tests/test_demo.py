import json
from datetime import UTC, datetime, timedelta

import pytest
from conftest import CSRF_HEADER
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from app.adapters.storage import MemoryStorage
from app.models import ErrorEvent, Item, RateLimitHit, User, UserSession
from app.services.demo import NotADemoAccount, load_demo, remove_expired, start_demo
from app.services.reference_seed import SEED_DIR


def test_the_demo_account_gets_every_staple_and_is_marked(db: Session) -> None:
    loaded = load_demo(db, "Demo@Example.com")

    staples = json.loads((SEED_DIR / "archetypes.json").read_text())["archetypes"]
    user = db.scalars(select(User).where(User.email == "demo@example.com")).one()
    assert user.is_demo
    assert loaded.items == len(staples)
    assert loaded.password
    assert db.scalar(select(func.count()).where(Item.user_id == user.id)) == len(staples)
    assert db.scalar(select(func.count()).where(Item.price.is_not(None))) == 0


def test_loading_again_replaces_the_demo_wardrobe(db: Session) -> None:
    load_demo(db, "demo@example.com")

    again = load_demo(db, "demo@example.com", section="menswear")

    assert again.password is None
    assert db.scalar(select(func.count()).select_from(Item)) == again.items


def test_a_real_account_is_never_touched(db: Session, sam: TestClient) -> None:
    sam.post("/api/v1/items", json={"category_id": "tshirt", "color_primary": "navy"})

    with pytest.raises(NotADemoAccount):
        load_demo(db, "sam@example.com")

    assert db.scalar(select(func.count()).select_from(Item)) == 1


def test_a_real_account_is_not_labelled_a_demo(sam: TestClient) -> None:
    me = sam.get("/api/v1/auth/me").json()
    assert (me["is_demo"], me["demo_ends_at"]) == (False, None)


DEMO = "/api/v1/auth/demo"


def staples(section: str) -> int:
    found = json.loads((SEED_DIR / "archetypes.json").read_text())["archetypes"]
    return sum(1 for staple in found if section in staple["sections"])


def test_try_the_demo_gives_a_fresh_logged_in_wardrobe(client: TestClient) -> None:
    started = client.post(DEMO, json={"section": "womenswear"})

    assert started.status_code == 201
    me = client.get("/api/v1/auth/me").json()
    assert me["is_demo"] is True and me["onboarding_completed"] is True
    assert me["email"].endswith("@demo.wearwise.invalid")
    ends = datetime.fromisoformat(me["demo_ends_at"]) - datetime.fromisoformat(me["created_at"])
    assert ends == timedelta(days=1)
    assert client.get("/api/v1/items").json()["total"] == staples("womenswear")
    setup = json.loads((SEED_DIR / "demo.json").read_text())
    profile = client.get("/api/v1/profile").json()
    assert profile["occasion_ids"] == setup["occasion_ids"]
    assert profile["sections"] == ["womenswear"]
    # The wardrobe is ready to use at once.
    found = client.post("/api/v1/outfits/suggest", json={"occasion_id": "work"}).json()
    assert found["suggestions"]


def test_each_visitor_gets_their_own_copy(app: FastAPI) -> None:
    with TestClient(app, headers=CSRF_HEADER) as one, TestClient(app, headers=CSRF_HEADER) as two:
        first = one.post(DEMO, json={}).json()
        second = two.post(DEMO, json={}).json()
        item = one.get("/api/v1/items").json()["items"][0]

        assert first["id"] != second["id"]
        assert two.get(f"/api/v1/items/{item['id']}").status_code == 404
        assert one.get("/api/v1/items").json()["total"] == staples("menswear")


def test_demos_are_limited_per_address(client: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.api import auth as auth_api
    from app.services import rate_limit

    monkeypatch.setattr(auth_api, "DEMO_PER_IP", rate_limit.Limit(2, timedelta(hours=1)))

    statuses = [client.post(DEMO, json={}).status_code for _ in range(3)]

    assert statuses == [201, 201, 429]


def test_a_visitors_demo_goes_after_a_day_with_everything_in_it(
    db: Session, sam: TestClient
) -> None:
    now = datetime.now(UTC)
    old, _ = start_demo(db, "menswear", now)
    db.execute(
        update(User).where(User.id == old.id).values(created_at=now - timedelta(days=1, minutes=1))
    )
    load_demo(db, "named-demo@example.com")
    db.flush()

    removed, _ = remove_expired(db, now)
    # Starting a demo makes room first, and a fresh one stays.
    fresh, _ = start_demo(db, "menswear", now)
    again, _ = remove_expired(db, now)

    assert (removed, again) == (1, 0)
    left = set(db.scalars(select(User.email)))
    assert old.email not in left
    assert {fresh.email, "named-demo@example.com", "sam@example.com"} <= left
    assert db.scalar(select(func.count()).select_from(Item).where(Item.user_id == old.id)) == 0


def test_only_so_many_demos_run_at_once(db: Session, monkeypatch: pytest.MonkeyPatch) -> None:
    from app.services import demo

    monkeypatch.setattr(demo, "MAX_LIVE", 2)
    now = datetime.now(UTC)
    first, _ = start_demo(db, "menswear", now)
    db.execute(update(User).where(User.id == first.id).values(created_at=now - timedelta(hours=2)))
    second, _ = start_demo(db, "menswear", now)
    third, _ = start_demo(db, "menswear", now)

    live = set(db.scalars(select(User.id).where(User.is_demo)))
    assert live == {second.id, third.id}


def test_housekeeping_removes_only_what_has_expired(
    db: Session, sam: TestClient, storage: MemoryStorage
) -> None:
    from app.services.housekeeping import tidy

    now = datetime.now(UTC)
    old, _ = start_demo(db, "menswear", now)
    db.execute(update(User).where(User.id == old.id).values(created_at=now - timedelta(days=2)))
    db.add(ErrorEvent(source="server", kind="RuntimeError", message="old"))
    db.add(ErrorEvent(source="server", kind="RuntimeError", message="new"))
    db.flush()
    db.execute(
        update(ErrorEvent)
        .where(ErrorEvent.message == "old")
        .values(created_at=now - timedelta(days=31))
    )
    db.add(RateLimitHit(bucket="login:ip:203.0.113.5", window_start=now - timedelta(days=2)))
    db.execute(update(UserSession).values(expires_at=now - timedelta(minutes=1)))
    db.flush()

    counts, _ = tidy(db, now)

    assert counts["demo accounts"] == 1
    assert counts["error reports"] >= 1 and counts["rate-limit counts"] >= 1
    assert counts["ended sessions"] >= 1
    messages = set(db.scalars(select(ErrorEvent.message)))
    assert "old" not in messages and "new" in messages
    assert sam.get("/api/v1/auth/me").status_code == 401
