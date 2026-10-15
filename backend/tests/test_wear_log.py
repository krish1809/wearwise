from datetime import timedelta
from typing import Any

from fastapi.testclient import TestClient
from wardrobe_support import add_item, basics, save_outfit

from app.services.wear import today

LOGS = "/api/v1/wear-logs"


def item(client: TestClient, item_id: str) -> dict[str, Any]:
    result: dict[str, Any] = client.get(f"/api/v1/items/{item_id}").json()
    return result


def day(offset: int) -> str:
    return (today() + timedelta(days=offset)).isoformat()


def test_logging_an_outfit_counts_a_wear_for_each_piece(sam: TestClient) -> None:
    w = basics(sam)
    outfit = save_outfit(sam, w["shirt"], w["chinos"], w["loafers"], occasion_id="work")

    response = sam.post(LOGS, json={"worn_on": day(0), "outfit_id": outfit["id"]})

    assert response.status_code == 201
    log = response.json()
    assert log["outfit_name"] == "Navy casual shirt with olive chinos"
    assert log["occasion_id"] == "work"
    assert [p["slot"] for p in log["pieces"]] == ["top", "bottom", "footwear"]
    shirt = item(sam, w["shirt"]["id"])
    assert shirt["wears_since_wash"] == 1
    assert shirt["wear_count"] == 1
    assert shirt["last_worn_on"] == day(0)
    assert item(sam, w["watch"]["id"])["wear_count"] == 0
    assert sam.get(f"/api/v1/outfits/{outfit['id']}").json()["wear_count"] == 1


def test_a_second_tap_for_the_same_outfit_and_day_logs_once(sam: TestClient) -> None:
    w = basics(sam)
    outfit = save_outfit(sam, w["shirt"], w["chinos"], w["loafers"])
    first = sam.post(LOGS, json={"worn_on": day(0), "outfit_id": outfit["id"]}).json()

    again = sam.post(LOGS, json={"worn_on": day(0), "outfit_id": outfit["id"]})

    assert again.status_code == 200
    assert again.json()["id"] == first["id"]
    assert item(sam, w["shirt"]["id"])["wear_count"] == 1


def test_loose_items_can_be_logged(sam: TestClient) -> None:
    w = basics(sam)

    log = sam.post(
        LOGS,
        json={
            "worn_on": day(-1),
            "item_ids": [w["sneakers"]["id"], w["dress"]["id"]],
            "note": " Picnic ",
        },
    ).json()

    assert log["outfit_id"] is None
    assert log["note"] == "Picnic"
    assert [p["name"] for p in log["pieces"]] == ["Black dress", "White sneakers"]
    assert item(sam, w["dress"]["id"])["last_worn_on"] == day(-1)


def test_a_log_needs_an_outfit_or_items_but_not_both(sam: TestClient) -> None:
    w = basics(sam)
    outfit = save_outfit(sam, w["shirt"], w["chinos"], w["loafers"])

    nothing = sam.post(LOGS, json={"worn_on": day(0)})
    both = sam.post(
        LOGS, json={"worn_on": day(0), "outfit_id": outfit["id"], "item_ids": [w["watch"]["id"]]}
    )

    assert nothing.status_code == 422
    assert nothing.json()["error"]["fields"]["item_ids"] == "Choose at least one item you wore."
    assert both.status_code == 422


def test_days_that_have_not_happened_are_refused(sam: TestClient) -> None:
    w = basics(sam)
    body = {"item_ids": [w["shirt"]["id"]]}

    # A phone ahead of the server's clock may already be on tomorrow.
    assert sam.post(LOGS, json={**body, "worn_on": day(1)}).status_code == 201
    later = sam.post(LOGS, json={**body, "worn_on": day(2)})
    assert later.status_code == 422
    assert later.json()["error"]["fields"]["worn_on"] == "That day hasn't happened yet."


def test_editing_and_deleting_a_log_recounts_the_wears(sam: TestClient) -> None:
    w = basics(sam)
    log = sam.post(LOGS, json={"worn_on": day(0), "item_ids": [w["shirt"]["id"]]}).json()

    edited = sam.patch(
        f"{LOGS}/{log['id']}", json={"item_ids": [w["chinos"]["id"]], "worn_on": day(-3)}
    )

    assert edited.status_code == 200
    assert edited.json()["worn_on"] == day(-3)
    assert item(sam, w["shirt"]["id"])["wears_since_wash"] == 0
    assert item(sam, w["chinos"]["id"])["wears_since_wash"] == 1
    assert sam.delete(f"{LOGS}/{log['id']}").status_code == 204
    assert item(sam, w["chinos"]["id"])["wears_since_wash"] == 0
    assert item(sam, w["chinos"]["id"])["wear_count"] == 0


def test_a_wash_resets_the_count_and_older_wears_stay_washed(sam: TestClient) -> None:
    w = basics(sam)
    shirt = w["shirt"]["id"]
    sam.post(LOGS, json={"worn_on": day(-2), "item_ids": [shirt]})
    sam.post(LOGS, json={"worn_on": day(-1), "item_ids": [shirt]})
    assert item(sam, shirt)["wears_since_wash"] == 2

    sam.patch(f"/api/v1/items/{shirt}", json={"status": "laundry"})
    sam.patch(f"/api/v1/items/{shirt}", json={"status": "available"})
    assert item(sam, shirt)["wears_since_wash"] == 0

    # Logged afterwards for a day before the wash: still washed since.
    sam.post(LOGS, json={"worn_on": day(-3), "item_ids": [shirt]})
    assert item(sam, shirt)["wears_since_wash"] == 0
    sam.post(LOGS, json={"worn_on": day(1), "item_ids": [shirt]})
    assert item(sam, shirt)["wears_since_wash"] == 1
    assert item(sam, shirt)["wear_count"] == 4


def test_history_survives_changes_to_outfits_and_items(sam: TestClient) -> None:
    w = basics(sam)
    outfit = save_outfit(sam, w["shirt"], w["chinos"], w["loafers"])
    log = sam.post(LOGS, json={"worn_on": day(-1), "outfit_id": outfit["id"]}).json()

    sam.patch(
        f"/api/v1/outfits/{outfit['id']}",
        json={"item_ids": [w["shirt"]["id"], w["chinos"]["id"], w["sneakers"]["id"]]},
    )
    sam.delete(f"/api/v1/items/{w['chinos']['id']}")

    shown = sam.get(LOGS).json()["logs"][0]
    assert shown["id"] == log["id"]
    assert [(p["name"], p["removed"]) for p in shown["pieces"]] == [
        ("Navy casual shirt", False),
        ("Olive chinos", True),
        ("Brown loafers", False),
    ]


def test_the_log_lists_newest_days_first_and_filters(sam: TestClient) -> None:
    w = basics(sam)
    old = sam.post(LOGS, json={"worn_on": day(-5), "item_ids": [w["shirt"]["id"]]}).json()
    new = sam.post(LOGS, json={"worn_on": day(0), "item_ids": [w["dress"]["id"]]}).json()
    middle = sam.post(LOGS, json={"worn_on": day(-2), "item_ids": [w["shirt"]["id"]]}).json()

    def ids(**params: str | bool) -> list[str]:
        return [log["id"] for log in sam.get(LOGS, params=params).json()["logs"]]

    assert ids() == [new["id"], middle["id"], old["id"]]
    assert ids(item_id=w["shirt"]["id"]) == [middle["id"], old["id"]]
    assert ids(on=day(-5)) == [old["id"]]
    page = sam.get(LOGS, params={"limit": 2}).json()
    rest = sam.get(LOGS, params={"limit": 2, "cursor": page["next_cursor"]}).json()
    assert [log["id"] for log in rest["logs"]] == [old["id"]]
    assert rest["next_cursor"] is None


def test_another_persons_log_is_invisible_and_untouchable(sam: TestClient, ana: TestClient) -> None:
    w = basics(sam)
    outfit = save_outfit(sam, w["shirt"], w["chinos"], w["loafers"])
    log = sam.post(LOGS, json={"worn_on": day(0), "outfit_id": outfit["id"]}).json()
    anas = add_item(ana, "tshirt", "red")

    assert ana.get(LOGS).json()["logs"] == []
    assert ana.patch(f"{LOGS}/{log['id']}", json={"note": "x"}).status_code == 404
    assert ana.delete(f"{LOGS}/{log['id']}").status_code == 404
    stolen_outfit = ana.post(LOGS, json={"worn_on": day(0), "outfit_id": outfit["id"]})
    assert stolen_outfit.status_code == 422
    stolen_items = ana.post(
        LOGS, json={"worn_on": day(0), "item_ids": [w["shirt"]["id"], anas["id"]]}
    )
    assert stolen_items.status_code == 422
    assert item(sam, w["shirt"]["id"])["wear_count"] == 1


def test_the_wear_log_needs_a_login(client: TestClient) -> None:
    assert client.get(LOGS).status_code == 401
    assert client.post(LOGS, json={"worn_on": day(0), "item_ids": []}).status_code == 401
