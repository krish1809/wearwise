from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from wardrobe_support import add_item

from app.models import Trip, TripItem
from app.services.wear import today

TRIPS = "/api/v1/trips"


def wardrobe(client: TestClient) -> dict[str, dict[str, Any]]:
    found = {}
    for n, colour in enumerate(["white", "navy", "olive", "grey", "black"]):
        found[f"top{n}"] = add_item(client, "casual_shirt", colour)
    for n, colour in enumerate(["beige", "navy"]):
        found[f"bottom{n}"] = add_item(client, "chinos", colour)
    found["shoes"] = add_item(client, "loafers", "brown")
    found["kurta"] = add_item(client, "kurta", "cream", formality=4)
    found["ethnic"] = add_item(client, "ethnic_bottom", "cream", formality=4)
    found["juttis"] = add_item(client, "juttis", "gold")
    return found


def body(**fields: Any) -> dict[str, Any]:
    start = today() + timedelta(days=10)
    return {
        "destination": "Jaipur, Rajasthan, India",
        "latitude": 26.91,
        "longitude": 75.79,
        "start_date": start.isoformat(),
        "end_date": (start + timedelta(days=2)).isoformat(),
        "occasion_id": "casual_outing",
        **fields,
    }


def test_a_trip_gets_a_packing_list_and_an_outfit_a_day(sam: TestClient) -> None:
    wardrobe(sam)

    response = sam.post(TRIPS, json=body())

    assert response.status_code == 201
    trip = response.json()
    assert [day["occasion_id"] for day in trip["days"]] == ["casual_outing"] * 3
    assert all(day["pieces"] and not day["missing"] for day in trip["days"])
    packed = {row["item"]["id"] for row in trip["items"]}
    for day in trip["days"]:
        assert {piece["item"]["id"] for piece in day["pieces"]} <= packed
    assert trip["basics"] == {"socks": 3, "innerwear": 3}
    assert all(row["packed"] is False for row in trip["items"])


def test_a_day_can_have_its_own_occasion(sam: TestClient) -> None:
    w = wardrobe(sam)
    wedding = (today() + timedelta(days=11)).isoformat()

    trip = sam.post(TRIPS, json=body(day_occasions={wedding: "festive"})).json()

    day = trip["days"][1]
    assert day["occasion_id"] == "festive"
    assert w["kurta"]["id"] in {piece["item"]["id"] for piece in day["pieces"]}


@pytest.mark.parametrize(
    ("fields", "problem"),
    [
        ({"end_date": today().isoformat()}, "end_date"),
        ({"end_date": (today() + timedelta(days=40)).isoformat()}, "end_date"),
        ({"occasion_id": "brunch"}, "occasion_id"),
        ({"latitude": None}, "destination"),
    ],
)
def test_impossible_trips_are_refused(
    sam: TestClient, fields: dict[str, Any], problem: str
) -> None:
    response = sam.post(TRIPS, json=body(**fields))

    assert response.status_code == 422
    assert problem in response.json()["error"]["fields"]


def test_packed_items_leave_everyday_suggestions_until_unpacked(sam: TestClient) -> None:
    wardrobe(sam)
    trip = sam.post(TRIPS, json=body()).json()
    ids = [row["item"]["id"] for row in trip["items"]]

    packed = sam.post(f"{TRIPS}/{trip['id']}/packed", json={"item_ids": ids, "packed": True})

    assert all(row["packed"] for row in packed.json()["items"])
    assert all(sam.get(f"/api/v1/items/{item_id}").json()["status"] == "packed" for item_id in ids)
    found = sam.post(
        "/api/v1/outfits/suggest", json={"occasion_id": "casual_outing", "season": "mild"}
    ).json()
    used = {p["item"]["id"] for s in found["suggestions"] for p in s["pieces"]}
    assert not used & set(ids)

    sam.post(f"{TRIPS}/{trip['id']}/packed", json={"item_ids": ids, "packed": False})
    assert all(
        sam.get(f"/api/v1/items/{item_id}").json()["status"] == "available" for item_id in ids
    )


def test_only_items_on_the_list_can_be_packed(sam: TestClient) -> None:
    w = wardrobe(sam)
    trip = sam.post(TRIPS, json=body()).json()
    off_list = next(
        item["id"]
        for item in w.values()
        if item["id"] not in {row["item"]["id"] for row in trip["items"]}
    )

    response = sam.post(
        f"{TRIPS}/{trip['id']}/packed", json={"item_ids": [off_list], "packed": True}
    )

    assert response.status_code == 422


def test_replanning_keeps_packed_items_in_play(sam: TestClient) -> None:
    wardrobe(sam)
    trip = sam.post(TRIPS, json=body()).json()
    ids = [row["item"]["id"] for row in trip["items"]]
    sam.post(f"{TRIPS}/{trip['id']}/packed", json={"item_ids": ids, "packed": True})

    again = sam.post(f"{TRIPS}/{trip['id']}/replan").json()

    assert all(day["pieces"] for day in again["days"])


def test_deleting_a_trip_unpacks_its_items(sam: TestClient, db: Session) -> None:
    wardrobe(sam)
    trip = sam.post(TRIPS, json=body()).json()
    ids = [row["item"]["id"] for row in trip["items"]]
    sam.post(f"{TRIPS}/{trip['id']}/packed", json={"item_ids": ids, "packed": True})

    assert sam.delete(f"{TRIPS}/{trip['id']}").status_code == 204

    assert db.scalar(select(func.count()).select_from(Trip)) == 0
    assert db.scalar(select(func.count()).select_from(TripItem)) == 0
    assert all(
        sam.get(f"/api/v1/items/{item_id}").json()["status"] == "available" for item_id in ids
    )


def test_trips_are_listed_latest_first(sam: TestClient) -> None:
    wardrobe(sam)
    sam.post(TRIPS, json=body())
    later = today() + timedelta(days=20)
    sam.post(
        TRIPS,
        json=body(
            destination="Goa, India",
            latitude=15.3,
            longitude=74.12,
            start_date=later.isoformat(),
            end_date=(later + timedelta(days=1)).isoformat(),
        ),
    )

    listed = sam.get(TRIPS).json()

    assert [trip["destination"] for trip in listed] == ["Goa, India", "Jaipur, Rajasthan, India"]
    assert all(trip["item_count"] > 0 for trip in listed)


def test_another_account_cannot_see_or_change_a_trip(sam: TestClient, ana: TestClient) -> None:
    wardrobe(sam)
    trip = sam.post(TRIPS, json=body()).json()
    ids = [row["item"]["id"] for row in trip["items"]]

    assert ana.get(f"{TRIPS}/{trip['id']}").status_code == 404
    assert ana.post(f"{TRIPS}/{trip['id']}/replan").status_code == 404
    assert (
        ana.post(f"{TRIPS}/{trip['id']}/packed", json={"item_ids": ids, "packed": True}).status_code
        == 404
    )
    assert ana.delete(f"{TRIPS}/{trip['id']}").status_code == 404
    assert ana.get(TRIPS).json() == []
