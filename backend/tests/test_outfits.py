from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from wardrobe_support import add_item, basics, save_outfit

from app.models import Outfit, WearLog

OUTFITS = "/api/v1/outfits"


def test_a_complete_outfit_is_saved_with_its_pieces_in_slot_order(sam: TestClient) -> None:
    w = basics(sam)

    outfit = save_outfit(sam, w["watch"], w["loafers"], w["chinos"], w["shirt"])

    assert outfit["template_id"] == "separates"
    assert outfit["complete"] is True
    assert [p["slot"] for p in outfit["pieces"]] == ["top", "bottom", "footwear", "watch"]
    assert outfit["display_name"] == "Navy casual shirt with olive chinos"
    assert outfit["is_favorite"] is False
    assert outfit["wear_count"] == 0


def test_an_incomplete_outfit_is_refused_with_what_it_needs(sam: TestClient) -> None:
    w = basics(sam)

    response = sam.post(OUTFITS, json={"item_ids": [w["shirt"]["id"]]})

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "outfit_incomplete"
    assert error["message"] == "Still needed: bottom, footwear."


def test_checking_explains_what_fits_without_saving(sam: TestClient, db: Session) -> None:
    w = basics(sam)

    partial = sam.post(f"{OUTFITS}/check", json={"item_ids": [w["shirt"]["id"]]}).json()
    dress = sam.post(
        f"{OUTFITS}/check",
        json={"item_ids": [w["dress"]["id"], w["chinos"]["id"], w["loafers"]["id"]]},
    ).json()
    done = sam.post(
        f"{OUTFITS}/check",
        json={"item_ids": [w["dress"]["id"], w["loafers"]["id"], w["watch"]["id"]]},
    ).json()

    assert partial["missing"] == ["bottom", "footwear"]
    assert partial["missing_names"] == ["Bottom", "Footwear"]
    assert partial["template_name"] == "Top and bottom"
    assert partial["optional_slots"][:3] == ["layer", "bag", "belt"]
    assert "fragrance" in partial["optional_slots"]
    assert dress["template_id"] == "one_piece"
    assert dress["misplaced_item_ids"] == [w["chinos"]["id"]]
    assert dress["message"] == "Olive chinos doesn't go in a one-piece outfit."
    assert done["complete"] is True
    assert done["message"] is None
    assert db.scalar(select(func.count()).select_from(Outfit)) == 0


def test_two_items_for_one_slot_are_refused(sam: TestClient) -> None:
    w = basics(sam)

    response = sam.post(
        OUTFITS,
        json={
            "item_ids": [
                w["shirt"]["id"],
                w["chinos"]["id"],
                w["loafers"]["id"],
                w["sneakers"]["id"],
            ]
        },
    )

    assert response.status_code == 422
    assert response.json()["error"]["message"] == (
        "Choose one item per slot: there's more than one footwear."
    )


def test_archived_and_unknown_items_are_refused(sam: TestClient, ana: TestClient) -> None:
    w = basics(sam)
    anas_shoes = add_item(ana, "sneakers", "black")
    sam.post(f"/api/v1/items/{w['loafers']['id']}/archive")

    archived = sam.post(
        OUTFITS, json={"item_ids": [w["shirt"]["id"], w["chinos"]["id"], w["loafers"]["id"]]}
    )
    someone_elses = sam.post(
        OUTFITS, json={"item_ids": [w["shirt"]["id"], w["chinos"]["id"], anas_shoes["id"]]}
    )

    assert archived.status_code == 422
    assert archived.json()["error"]["fields"]["item_ids"] == (
        "Brown loafers is archived. Restore it to use it in an outfit."
    )
    assert someone_elses.status_code == 422
    assert someone_elses.json()["error"]["fields"]["item_ids"] == "Some of those items don't exist."


def test_name_occasion_and_favourite_can_be_changed(sam: TestClient) -> None:
    w = basics(sam)
    outfit = save_outfit(sam, w["shirt"], w["chinos"], w["loafers"])

    edited = sam.patch(
        f"{OUTFITS}/{outfit['id']}",
        json={"name": " Friday office ", "occasion_id": "work", "is_favorite": True},
    ).json()

    assert edited["name"] == "Friday office"
    assert edited["display_name"] == "Friday office"
    assert edited["occasion_id"] == "work"
    assert edited["is_favorite"] is True
    assert len(edited["pieces"]) == 3
    bad = sam.patch(f"{OUTFITS}/{outfit['id']}", json={"occasion_id": "moon_landing"})
    assert bad.status_code == 422


def test_one_piece_can_be_swapped_and_the_rest_kept(sam: TestClient) -> None:
    w = basics(sam)
    outfit = save_outfit(sam, w["shirt"], w["chinos"], w["loafers"], name="Easy")

    swapped = sam.patch(
        f"{OUTFITS}/{outfit['id']}",
        json={"item_ids": [w["shirt"]["id"], w["chinos"]["id"], w["sneakers"]["id"]]},
    ).json()
    broken = sam.patch(
        f"{OUTFITS}/{outfit['id']}", json={"item_ids": [w["shirt"]["id"], w["chinos"]["id"]]}
    )

    assert [p["name"] for p in swapped["pieces"]] == [
        "Navy casual shirt",
        "Olive chinos",
        "White sneakers",
    ]
    assert swapped["name"] == "Easy"
    assert broken.status_code == 422
    assert len(sam.get(f"{OUTFITS}/{outfit['id']}").json()["pieces"]) == 3


def test_duplicating_copies_the_pieces(sam: TestClient) -> None:
    w = basics(sam)
    outfit = save_outfit(sam, w["dress"], w["sneakers"], name="Sunday", occasion_id="casual_outing")

    copy = sam.post(f"{OUTFITS}/{outfit['id']}/duplicate").json()

    assert copy["id"] != outfit["id"]
    assert copy["name"] == "Sunday (copy)"
    assert copy["occasion_id"] == "casual_outing"
    assert [p["item"]["id"] for p in copy["pieces"]] == [p["item"]["id"] for p in outfit["pieces"]]


def test_deleting_an_item_shows_it_as_removed_until_it_is_swapped(sam: TestClient) -> None:
    w = basics(sam)
    outfit = save_outfit(sam, w["shirt"], w["chinos"], w["loafers"])

    sam.delete(f"/api/v1/items/{w['loafers']['id']}")

    shown = sam.get(f"{OUTFITS}/{outfit['id']}").json()
    assert shown["complete"] is False
    assert shown["pieces"][2] == {
        "slot": "footwear",
        "item": None,
        "name": "Brown loafers",
        "removed": True,
    }
    fixed = sam.patch(
        f"{OUTFITS}/{outfit['id']}",
        json={"item_ids": [w["shirt"]["id"], w["chinos"]["id"], w["sneakers"]["id"]]},
    ).json()
    assert fixed["complete"] is True
    assert not any(p["removed"] for p in fixed["pieces"])


def test_lists_filter_by_favourite_occasion_and_item(sam: TestClient) -> None:
    w = basics(sam)
    first = save_outfit(sam, w["shirt"], w["chinos"], w["loafers"], is_favorite=True)
    second = save_outfit(sam, w["dress"], w["sneakers"], occasion_id="party")
    third = save_outfit(sam, w["shirt"], w["chinos"], w["sneakers"])

    def ids(**params: str | bool) -> list[str]:
        return [o["id"] for o in sam.get(OUTFITS, params=params).json()["outfits"]]

    assert ids() == [third["id"], second["id"], first["id"]]
    assert ids(favorite=True) == [first["id"]]
    assert ids(occasion="party") == [second["id"]]
    assert ids(item_id=w["sneakers"]["id"]) == [third["id"], second["id"]]
    page = sam.get(OUTFITS, params={"limit": 2}).json()
    rest = sam.get(OUTFITS, params={"limit": 2, "cursor": page["next_cursor"]}).json()
    assert [o["id"] for o in page["outfits"] + rest["outfits"]] == [
        third["id"],
        second["id"],
        first["id"],
    ]
    assert rest["next_cursor"] is None


def test_deleting_an_outfit_keeps_what_was_worn(sam: TestClient, db: Session) -> None:
    w = basics(sam)
    outfit = save_outfit(sam, w["shirt"], w["chinos"], w["loafers"])
    sam.post("/api/v1/wear-logs", json={"worn_on": "2026-10-01", "outfit_id": outfit["id"]})

    assert sam.delete(f"{OUTFITS}/{outfit['id']}").status_code == 204

    assert sam.get(f"{OUTFITS}/{outfit['id']}").status_code == 404
    log = sam.get("/api/v1/wear-logs").json()["logs"][0]
    assert log["outfit_id"] is None
    assert [p["name"] for p in log["pieces"]] == [
        "Navy casual shirt",
        "Olive chinos",
        "Brown loafers",
    ]


def test_another_persons_outfits_are_invisible_and_untouchable(
    sam: TestClient, ana: TestClient
) -> None:
    w = basics(sam)
    outfit = save_outfit(sam, w["shirt"], w["chinos"], w["loafers"])
    path = f"{OUTFITS}/{outfit['id']}"

    assert ana.get(OUTFITS).json()["outfits"] == []
    assert ana.get(path).status_code == 404
    assert ana.patch(path, json={"name": "Mine"}).status_code == 404
    assert ana.post(f"{path}/duplicate").status_code == 404
    assert ana.delete(path).status_code == 404
    assert ana.post(f"{OUTFITS}/check", json={"item_ids": [w["shirt"]["id"]]}).status_code == 422
    assert sam.get(path).json()["display_name"] == "Navy casual shirt with olive chinos"


def test_outfits_need_a_login(client: TestClient) -> None:
    assert client.get(OUTFITS).status_code == 401
    assert client.post(f"{OUTFITS}/check", json={"item_ids": []}).status_code == 401


def test_deleting_the_account_removes_outfits_and_the_wear_log(
    sam: TestClient, db: Session
) -> None:
    w = basics(sam)
    outfit = save_outfit(sam, w["shirt"], w["chinos"], w["loafers"])
    sam.post("/api/v1/wear-logs", json={"worn_on": "2026-10-01", "outfit_id": outfit["id"]})

    sam.post("/api/v1/account/delete", json={"confirm_email": "sam@example.com"})

    assert db.scalar(select(func.count()).select_from(Outfit)) == 0
    assert db.scalar(select(func.count()).select_from(WearLog)) == 0
