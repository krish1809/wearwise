import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Item, User
from app.services.demo import NotADemoAccount, load_demo
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
    assert sam.get("/api/v1/auth/me").json()["is_demo"] is False
