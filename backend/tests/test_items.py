from typing import Any

from fastapi.testclient import TestClient
from photo_support import photo_bytes
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from wardrobe_support import add_item

from app.adapters.storage import MemoryStorage
from app.models import Item, ItemImage, User

ITEMS = "/api/v1/items"


def add(client: TestClient, **fields: Any) -> dict[str, Any]:
    body = {"category_id": "tshirt", "color_primary": "navy", **fields}
    response = client.post(ITEMS, json=body)
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


def listed(client: TestClient, **params: Any) -> list[str]:
    response = client.get(ITEMS, params=params)
    assert response.status_code == 200, response.text
    return [item["display_name"] for item in response.json()["items"]]


def test_a_category_and_a_colour_are_enough(sam: TestClient) -> None:
    item = add(sam, category_id="formal_shirt", color_primary="white")

    assert item["display_name"] == "White formal shirt"
    assert item["slot"] == "top"
    assert item["formality"] == 4
    assert item["warmth"] == 1
    assert item["wears_before_wash"] == 1
    assert item["pattern"] == "solid"
    assert item["status"] == "available"
    assert item["photo"] is None


def test_names_shorten_long_colour_and_category_names(sam: TestClient) -> None:
    assert add(sam, category_id="jeans", color_primary="beige")["display_name"] == "Beige jeans"
    named = add(sam, name="  Favourite tee ", brand="Uniqlo")
    assert named["display_name"] == "Favourite tee"
    assert named["brand"] == "Uniqlo"


def test_an_uploaded_photo_is_attached_and_its_colour_kept(sam: TestClient) -> None:
    photo = sam.post("/api/v1/photos", files={"file": ("s.png", photo_bytes(), "image/png")}).json()

    item = add(sam, photo_id=photo["id"])

    assert item["photo"]["id"] == photo["id"]
    assert item["color_hex"] == photo["dominant_hex"]
    again = sam.post(
        ITEMS, json={"category_id": "tshirt", "color_primary": "navy", "photo_id": photo["id"]}
    )
    assert again.status_code == 422
    assert "photo_id" in again.json()["error"]["fields"]


def test_choices_must_exist(sam: TestClient) -> None:
    response = sam.post(
        ITEMS,
        json={
            "category_id": "spacesuit",
            "color_primary": "octarine",
            "pattern": "polka",
            "fabric": "kevlar",
            "seasons": ["eternal"],
            "occasion_ids": ["moon_landing"],
            "status": "lost",
        },
    )

    assert response.status_code == 422
    assert set(response.json()["error"]["fields"]) == {
        "category_id",
        "color_primary",
        "pattern",
        "fabric",
        "seasons",
        "occasion_ids",
        "status",
    }


def test_values_are_checked(sam: TestClient) -> None:
    bad = sam.post(
        ITEMS,
        json={
            "category_id": "tshirt",
            "color_primary": "navy",
            "formality": 9,
            "color_hex": "navy",
            "purchased_on": "2999-01-01",
            "price": -5,
            "style_tags": ["x" * 31],
        },
    )

    assert bad.status_code == 422
    assert set(bad.json()["error"]["fields"]) == {
        "formality",
        "color_hex",
        "purchased_on",
        "price",
        "style_tags",
    }


def test_editing_changes_only_what_was_sent_and_null_clears(sam: TestClient) -> None:
    item = add(sam, brand="Zara", seasons=["summer"], notes="Soft")

    edited = sam.patch(
        f"{ITEMS}/{item['id']}", json={"brand": None, "seasons": None, "status": "laundry"}
    )

    assert edited.status_code == 200
    body = edited.json()
    assert body["brand"] is None
    assert body["seasons"] == []
    assert body["notes"] == "Soft"
    assert body["status"] == "laundry"
    refused = sam.patch(f"{ITEMS}/{item['id']}", json={"color_primary": None})
    assert refused.status_code == 422


def test_changing_the_category_moves_the_item_to_its_slot(sam: TestClient) -> None:
    item = add(sam)

    moved = sam.patch(f"{ITEMS}/{item['id']}", json={"category_id": "sneakers"}).json()

    assert moved["slot"] == "footwear"


def test_replacing_the_photo_deletes_the_old_files(sam: TestClient, storage: MemoryStorage) -> None:
    first = sam.post("/api/v1/photos", files={"file": ("a.png", photo_bytes(), "image/png")}).json()
    item = add(sam, photo_id=first["id"])
    second = sam.post(
        "/api/v1/photos", files={"file": ("b.png", photo_bytes(), "image/png")}
    ).json()

    sam.patch(f"{ITEMS}/{item['id']}", json={"photo_id": second["id"]})

    assert all(first["id"] not in key for key in storage.files)
    removed = sam.patch(f"{ITEMS}/{item['id']}", json={"photo_id": None}).json()
    assert removed["photo"] is None
    assert storage.files == {}


def test_filters_combine(sam: TestClient) -> None:
    add(sam, name="Navy tee", seasons=["summer"], occasion_ids=["college"])
    add(sam, name="Black tee", color_primary="black", status="laundry")
    add(sam, name="Any-season tee")
    add(
        sam,
        name="Winter jeans",
        category_id="jeans",
        color_primary="denim_blue",
        seasons=["winter"],
    )
    add(
        sam,
        name="Minimal shirt",
        category_id="casual_shirt",
        color_secondary="navy",
        style_tags=["minimal"],
    )

    assert listed(sam, color="navy") == ["Minimal shirt", "Any-season tee", "Navy tee"]
    assert listed(sam, season="summer") == [
        "Minimal shirt",
        "Any-season tee",
        "Black tee",
        "Navy tee",
    ]
    assert listed(sam, group="bottoms") == ["Winter jeans"]
    assert listed(sam, slot="bottom") == ["Winter jeans"]
    assert listed(sam, category=["tshirt", "jeans"], season="winter") == [
        "Winter jeans",
        "Any-season tee",
        "Black tee",
    ]
    assert listed(sam, occasion="college") == ["Navy tee"]
    assert listed(sam, style="minimal") == ["Minimal shirt"]
    assert listed(sam, status="laundry") == ["Black tee"]


def test_search_matches_names_brands_categories_and_colours(sam: TestClient) -> None:
    add(sam, name="Weekend tee", brand="Uniqlo")
    add(sam, category_id="jeans", color_primary="black")

    assert listed(sam, q="uniqlo") == ["Weekend tee"]
    assert listed(sam, q="black jeans") == ["Black jeans"]
    assert listed(sam, q="JEA") == ["Black jeans"]
    assert listed(sam, q="100%") == []


def test_pages_cover_every_item_once_in_each_order(sam: TestClient) -> None:
    for name in ["A", "B", "C", "D", "E"]:
        add(sam, name=name, category_id="sneakers" if name in "BD" else "tshirt")

    for sort, expected in {
        "newest": ["E", "D", "C", "B", "A"],
        "oldest": ["A", "B", "C", "D", "E"],
        "category": ["E", "C", "A", "D", "B"],
    }.items():
        seen: list[str] = []
        cursor = None
        while True:
            params: dict[str, Any] = {"sort": sort, "limit": 2}
            if cursor:
                params["cursor"] = cursor
            page = sam.get(ITEMS, params=params).json()
            assert page["total"] == 5
            seen += [item["name"] for item in page["items"]]
            cursor = page["next_cursor"]
            if cursor is None:
                break
        assert seen == expected, sort


def test_a_broken_page_link_is_refused(sam: TestClient) -> None:
    assert sam.get(ITEMS, params={"cursor": "not-a-cursor"}).status_code == 422


def test_archived_items_leave_the_wardrobe_and_can_come_back(sam: TestClient) -> None:
    item = add(sam, name="Old tee")

    sam.post(f"{ITEMS}/{item['id']}/archive")

    assert listed(sam) == []
    assert listed(sam, archived=True) == ["Old tee"]
    restored = sam.post(f"{ITEMS}/{item['id']}/restore").json()
    assert restored["archived"] is False
    assert listed(sam) == ["Old tee"]


def test_deleting_removes_the_item_and_its_photo(
    sam: TestClient, storage: MemoryStorage, db: Session
) -> None:
    photo = sam.post("/api/v1/photos", files={"file": ("a.png", photo_bytes(), "image/png")}).json()
    item = add(sam, photo_id=photo["id"])

    assert sam.delete(f"{ITEMS}/{item['id']}").status_code == 204

    assert sam.get(f"{ITEMS}/{item['id']}").status_code == 404
    assert storage.files == {}
    assert db.scalar(select(func.count()).select_from(ItemImage)) == 0


def test_matching_sets_link_merge_and_dissolve(sam: TestClient) -> None:
    jacket = add(sam, name="Jacket", category_id="blazer")
    trousers = add(sam, name="Trousers", category_id="formal_trousers")
    waistcoat = add(sam, name="Waistcoat", category_id="waistcoat")

    linked = sam.post(f"{ITEMS}/{jacket['id']}/set", json={"item_id": trousers["id"]}).json()
    assert [m["display_name"] for m in linked["set_members"]] == ["Trousers"]
    three = sam.post(f"{ITEMS}/{waistcoat['id']}/set", json={"item_id": jacket["id"]}).json()
    assert {m["display_name"] for m in three["set_members"]} == {"Jacket", "Trousers"}

    sam.delete(f"{ITEMS}/{waistcoat['id']}/set")
    assert len(sam.get(f"{ITEMS}/{jacket['id']}").json()["set_members"]) == 1
    sam.delete(f"{ITEMS}/{trousers['id']}/set")
    # A set of one isn't a set.
    assert sam.get(f"{ITEMS}/{jacket['id']}").json()["set_id"] is None


def test_an_item_cannot_be_set_with_itself(sam: TestClient) -> None:
    item = add(sam)

    assert sam.post(f"{ITEMS}/{item['id']}/set", json={"item_id": item["id"]}).status_code == 409


def test_another_persons_items_are_invisible_and_untouchable(
    sam: TestClient, ana: TestClient
) -> None:
    item = add(sam, name="Sam's tee")
    anas = add(ana, name="Ana's tee")
    path = f"{ITEMS}/{item['id']}"

    assert listed(ana) == ["Ana's tee"]
    assert ana.get(path).status_code == 404
    assert ana.patch(path, json={"name": "Mine"}).status_code == 404
    assert ana.post(f"{path}/archive").status_code == 404
    assert ana.delete(path).status_code == 404
    assert ana.post(f"{ITEMS}/{anas['id']}/set", json={"item_id": item["id"]}).status_code == 404
    assert sam.get(path).json()["name"] == "Sam's tee"


def test_every_change_bumps_the_wardrobe_version(sam: TestClient, db: Session) -> None:
    user = db.scalars(select(User)).one()
    start = user.wardrobe_version

    item = add(sam)
    sam.patch(f"{ITEMS}/{item['id']}", json={"name": "Tee"})
    sam.post(f"{ITEMS}/{item['id']}/archive")
    sam.delete(f"{ITEMS}/{item['id']}")

    db.refresh(user)
    assert user.wardrobe_version == start + 4


def test_items_need_a_login(client: TestClient) -> None:
    assert client.get(ITEMS).status_code == 401
    assert (
        client.post(ITEMS, json={"category_id": "tshirt", "color_primary": "navy"}).status_code
        == 401
    )


def test_deleting_the_account_removes_items_photos_and_custom_categories(
    sam: TestClient, db: Session, storage: MemoryStorage
) -> None:
    category = sam.post(
        "/api/v1/categories", json={"name": "Kurta set", "group_id": "ethnic", "slot": "top"}
    ).json()
    photo = sam.post("/api/v1/photos", files={"file": ("a.png", photo_bytes(), "image/png")}).json()
    add(sam, category_id=category["id"], photo_id=photo["id"])

    response = sam.post("/api/v1/account/delete", json={"confirm_email": "sam@example.com"})

    assert response.status_code == 204
    assert db.scalar(select(func.count()).select_from(Item)) == 0
    assert db.scalar(select(func.count()).select_from(ItemImage)) == 0
    assert storage.files == {}


def test_the_colour_map_places_items_with_the_engines_colour_rules(
    sam: TestClient, ana: TestClient
) -> None:
    navy = add_item(sam, "chinos", "navy")
    orange = add_item(sam, "tshirt", "orange")
    patterned = add_item(sam, "casual_shirt", "multi")
    gone = add_item(sam, "tshirt", "white")
    sam.post(f"/api/v1/items/{gone['id']}/archive")
    add_item(ana, "tshirt", "red")

    points = {p["id"]: p for p in sam.get("/api/v1/items/colours").json()}

    assert set(points) == {navy["id"], orange["id"], patterned["id"]}
    assert points[navy["id"]]["neutral"] is True and points[navy["id"]]["known"] is True
    assert points[orange["id"]]["neutral"] is False
    assert 30 < points[orange["id"]]["hue"] < 80
    assert points[navy["id"]]["lightness"] < points[orange["id"]]["lightness"]
    assert points[patterned["id"]]["known"] is False and points[patterned["id"]]["hex"] is None
