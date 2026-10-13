import json

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Category, Item, User
from app.services.reference_seed import SEED_DIR

CATEGORIES = "/api/v1/categories"
CUSTOM = {"name": "Kurta pyjama set", "group_id": "ethnic", "slot": "top", "formality_default": 4}


def test_every_seeded_category_is_listed_in_order(sam: TestClient) -> None:
    listed = sam.get(CATEGORIES).json()

    seeded = json.loads((SEED_DIR / "taxonomy.json").read_text())["categories"]
    assert [c["id"] for c in listed] == [c["id"] for c in seeded]
    tshirt = listed[0]
    assert tshirt["custom"] is False
    assert tshirt["formality_default"] == 2


def test_a_custom_category_is_added_after_the_seeded_ones(sam: TestClient) -> None:
    created = sam.post(CATEGORIES, json={**CUSTOM, "name": "  Kurta pyjama set "})

    assert created.status_code == 201
    category = created.json()
    assert category["name"] == "Kurta pyjama set"
    assert category["custom"] is True
    assert category["sections"] == []
    assert (category["formality_min"], category["formality_max"]) == (3, 5)
    assert sam.get(CATEGORIES).json()[-1]["id"] == category["id"]


def test_custom_category_names_are_unique_per_person(sam: TestClient, ana: TestClient) -> None:
    sam.post(CATEGORIES, json=CUSTOM)

    again = sam.post(CATEGORIES, json={**CUSTOM, "name": "KURTA PYJAMA SET"})

    assert again.status_code == 409
    assert ana.post(CATEGORIES, json=CUSTOM).status_code == 201


def test_a_custom_category_needs_a_real_group_and_slot(sam: TestClient) -> None:
    response = sam.post(CATEGORIES, json={**CUSTOM, "group_id": "spacesuits", "slot": "tail"})

    assert response.status_code == 422
    assert set(response.json()["error"]["fields"]) == {"group_id", "slot"}


def test_another_persons_category_is_invisible_and_undeletable(
    sam: TestClient, ana: TestClient
) -> None:
    category = sam.post(CATEGORIES, json=CUSTOM).json()

    assert category["id"] not in [c["id"] for c in ana.get(CATEGORIES).json()]
    assert ana.delete(f"{CATEGORIES}/{category['id']}").status_code == 404
    assert sam.delete(f"{CATEGORIES}/{category['id']}").status_code == 204


def test_seeded_categories_cannot_be_deleted(sam: TestClient) -> None:
    assert sam.delete(f"{CATEGORIES}/tshirt").status_code == 404


def test_a_category_in_use_cannot_be_deleted(sam: TestClient, db: Session) -> None:
    category = sam.post(CATEGORIES, json=CUSTOM).json()
    owner = db.scalars(select(User)).one()
    db.add(
        Item(
            user_id=owner.id,
            category_id=category["id"],
            slot="top",
            color_primary="navy",
            formality=4,
            warmth=1,
        )
    )
    db.flush()

    response = sam.delete(f"{CATEGORIES}/{category['id']}")

    assert response.status_code == 409
    assert response.json()["error"]["message"].startswith("1 item still use")
    assert db.get(Category, category["id"]) is not None
