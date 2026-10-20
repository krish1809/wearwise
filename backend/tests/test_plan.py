from collections.abc import Iterator
from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from wardrobe_support import add_item

from app.adapters.weather import FakeWeather
from app.api import plan as plan_routes
from app.models import Event, PlanDay, WearLog
from app.services import rate_limit
from app.services import weather as weather_service
from app.services.wear import today

PLAN = "/api/v1/plan"
PUNE = {"city": "Pune, Maharashtra, India", "latitude": 18.52, "longitude": 73.86}
EVERY_DAY_COLLEGE = {str(day): "college" for day in range(7)}


@pytest.fixture(autouse=True)
def no_remembered_outages() -> Iterator[None]:
    weather_service.forget_failures()
    yield
    weather_service.forget_failures()


def wardrobe(client: TestClient) -> dict[str, dict[str, Any]]:
    found = {}
    for n, colour in enumerate(["white", "navy", "olive", "grey", "black", "beige", "maroon"]):
        found[f"top{n}"] = add_item(client, "casual_shirt", colour)
    for n, colour in enumerate(["beige", "navy", "olive", "black"]):
        found[f"bottom{n}"] = add_item(client, "chinos", colour)
    for n, colour in enumerate(["white", "brown", "black"]):
        found[f"shoes{n}"] = add_item(client, "loafers", colour)
    return found


def set_up(client: TestClient, **profile: Any) -> dict[str, dict[str, Any]]:
    client.patch(
        "/api/v1/profile", json={**PUNE, "weekday_occasions": EVERY_DAY_COLLEGE, **profile}
    )
    return wardrobe(client)


def plan(client: TestClient, **body: Any) -> dict[str, Any]:
    response = client.post(f"{PLAN}/generate", json=body)
    assert response.status_code == 200, response.text
    week: dict[str, Any] = response.json()
    return week


def core(day: dict[str, Any]) -> list[str]:
    return sorted(piece["item"]["id"] for piece in day["pieces"] if piece["core"])


def top(day: dict[str, Any]) -> str:
    return str(next(piece["item"]["id"] for piece in day["pieces"] if piece["slot"] == "top"))


def test_a_planned_week_has_an_outfit_a_day_and_keeps_the_rules(sam: TestClient) -> None:
    set_up(sam)

    week = plan(sam)

    assert week["start"] == today().isoformat()
    days = week["days"]
    assert len(days) == 7
    assert all(day["pieces"] and day["occasion_id"] == "college" for day in days)
    assert all(day["weather"]["source"] == "forecast" for day in days)
    tops = [top(day) for day in days]
    for index, shirt in enumerate(tops):
        # A shirt needs a wash after one wear, so no top comes back within the week.
        assert shirt not in tops[index + 1 :]


def test_the_week_can_be_read_back(sam: TestClient) -> None:
    set_up(sam)
    planned = plan(sam)

    again = sam.get(PLAN).json()

    assert [core(day) for day in again["days"]] == [core(day) for day in planned["days"]]


def test_a_day_without_an_occasion_asks_for_one(sam: TestClient) -> None:
    set_up(sam, weekday_occasions={})

    days = plan(sam)["days"]

    assert all(day["occasion_source"] == "none" for day in days)
    assert days[0]["missing"] == ["Choose an occasion for this day."]


def test_an_event_sets_its_day_and_can_be_removed(sam: TestClient) -> None:
    set_up(sam)
    friday = today() + timedelta(days=3)
    event = sam.post(
        "/api/v1/events",
        json={"day": friday.isoformat(), "title": "Cousin's wedding", "occasion_id": "festive"},
    ).json()

    days = plan(sam)["days"]

    assert (days[3]["occasion_id"], days[3]["occasion_source"]) == ("festive", "event")
    assert days[3]["events"][0]["title"] == "Cousin's wedding"
    assert sam.delete(f"/api/v1/events/{event['id']}").status_code == 204
    assert sam.get(PLAN).json()["days"][3]["occasion_source"] == "usual"


def test_choosing_an_occasion_marks_the_day_out_of_date_until_planned_again(
    sam: TestClient,
) -> None:
    set_up(sam)
    plan(sam)
    tomorrow = (today() + timedelta(days=1)).isoformat()

    changed = sam.patch(f"{PLAN}/days/{tomorrow}", json={"occasion_id": "date"}).json()
    replanned = plan(sam)["days"][1]
    back = sam.patch(f"{PLAN}/days/{tomorrow}", json={"occasion_id": None}).json()

    assert (changed["occasion_id"], changed["occasion_source"], changed["outdated"]) == (
        "date",
        "chosen",
        True,
    )
    assert (replanned["occasion_id"], replanned["outdated"]) == ("date", False)
    assert back["occasion_source"] == "usual"


def test_locking_two_days_keeps_them_when_the_rest_is_planned_again(sam: TestClient) -> None:
    set_up(sam)
    first = plan(sam)["days"]
    for index in (1, 4):
        sam.patch(f"{PLAN}/days/{first[index]['day']}", json={"locked": True})

    again = plan(sam)["days"]

    assert [day["locked"] for day in again] == [False, True, False, False, True, False, False]
    assert core(again[1]) == core(first[1])
    assert core(again[4]) == core(first[4])
    tops = [top(day) for day in again]
    assert len(tops) == len(set(tops))


def test_swapping_a_day_uses_one_of_its_options_and_locks_it(sam: TestClient) -> None:
    set_up(sam)
    week = plan(sam)["days"]
    day = week[2]["day"]

    options = sam.get(f"{PLAN}/days/{day}/options").json()
    chosen = options[0]
    swapped = sam.patch(f"{PLAN}/days/{day}", json={"item_ids": chosen["item_ids"]}).json()

    assert options and all(core_ids(o) != core(week[2]) for o in options)
    assert sorted(p["item"]["id"] for p in swapped["pieces"]) == sorted(chosen["item_ids"])
    assert swapped["locked"] is True
    assert swapped["reasons"]


def core_ids(option: dict[str, Any]) -> list[str]:
    return sorted(piece["item"]["id"] for piece in option["pieces"] if piece["core"])


def test_a_swap_must_be_a_whole_outfit(sam: TestClient) -> None:
    w = set_up(sam)
    plan(sam)

    response = sam.patch(f"{PLAN}/days/{today().isoformat()}", json={"item_ids": [w["top0"]["id"]]})

    assert response.status_code == 422
    assert "whole outfit" in response.json()["error"]["message"]


def test_wearing_a_planned_day_logs_it_once(sam: TestClient, db: Session) -> None:
    set_up(sam)
    first = plan(sam)["days"][0]
    url = f"{PLAN}/days/{first['day']}/wear"

    worn = sam.post(url).json()
    sam.post(url)

    assert worn["worn"] is True
    assert db.scalar(select(func.count()).select_from(WearLog)) == 1
    log = sam.get("/api/v1/wear-logs").json()["logs"][0]
    assert sorted(p["item"]["id"] for p in log["pieces"]) == sorted(
        p["item"]["id"] for p in first["pieces"]
    )
    # A worn day is kept when the week is planned again.
    assert core(plan(sam)["days"][0]) == core(first)


def test_with_the_weather_service_down_the_manual_setting_is_used(
    sam: TestClient, weather: FakeWeather
) -> None:
    weather.fail = True
    set_up(sam, manual_weather="hot")

    days = plan(sam)["days"]

    assert {day["weather"]["source"] for day in days} == {"manual"}
    assert days[0]["weather"]["feels_like"] == 34.0
    assert all(day["pieces"] for day in days)


def test_a_week_in_the_past_is_refused(sam: TestClient) -> None:
    response = sam.post(
        f"{PLAN}/generate", json={"start": (today() - timedelta(days=5)).isoformat()}
    )

    assert response.status_code == 422


def test_laundry_lists_what_is_due_and_resets_it(sam: TestClient) -> None:
    w = set_up(sam)
    shirt = w["top0"]["id"]
    trousers = w["bottom0"]["id"]
    sam.post(
        "/api/v1/wear-logs",
        json={"worn_on": today().isoformat(), "item_ids": [shirt, trousers]},
    )
    sam.patch(f"/api/v1/items/{w['top1']['id']}", json={"status": "laundry"})

    pending = sam.get("/api/v1/laundry").json()["items"]
    done = sam.post("/api/v1/laundry/done", json={"item_ids": [shirt, w["top1"]["id"]]})

    assert [(row["item"]["id"], row["in_laundry"]) for row in pending] == [
        (w["top1"]["id"], True),
        (shirt, False),
    ]
    assert done.json()["items"] == []
    assert sam.get(f"/api/v1/items/{shirt}").json()["wears_since_wash"] == 0
    assert sam.get(f"/api/v1/items/{w['top1']['id']}").json()["status"] == "available"


def test_another_account_cannot_touch_events_laundry_or_plans(
    sam: TestClient, ana: TestClient
) -> None:
    w = set_up(sam)
    plan(sam)
    event = sam.post(
        "/api/v1/events",
        json={"day": today().isoformat(), "title": "Exam", "occasion_id": "college"},
    ).json()

    assert ana.patch(f"/api/v1/events/{event['id']}", json={"title": "x"}).status_code == 404
    assert ana.delete(f"/api/v1/events/{event['id']}").status_code == 404
    assert ana.get("/api/v1/events").json() == []
    stolen = ana.post("/api/v1/laundry/done", json={"item_ids": [w["top0"]["id"]]})
    assert stolen.status_code == 422
    assert all(not day["pieces"] for day in ana.get(PLAN).json()["days"])
    borrowed = ana.patch(f"{PLAN}/days/{today().isoformat()}", json={"item_ids": [w["top0"]["id"]]})
    assert borrowed.status_code == 422


def test_planning_is_rate_limited(sam: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    set_up(sam)
    monkeypatch.setattr(
        plan_routes, "PLANS_PER_USER", rate_limit.Limit(attempts=1, window=timedelta(hours=1))
    )

    assert sam.post(f"{PLAN}/generate", json={}).status_code == 200
    assert sam.post(f"{PLAN}/generate", json={}).status_code == 429


def test_deleting_the_account_removes_the_plan_and_events(sam: TestClient, db: Session) -> None:
    set_up(sam)
    plan(sam)
    sam.post(
        "/api/v1/events",
        json={"day": date.today().isoformat(), "title": "Exam", "occasion_id": "college"},
    )
    email = sam.get("/api/v1/auth/me").json()["email"]

    sam.post("/api/v1/account/delete", json={"confirm_email": email})

    assert db.scalar(select(func.count()).select_from(PlanDay)) == 0
    assert db.scalar(select(func.count()).select_from(Event)) == 0
