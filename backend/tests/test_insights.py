"""Insights against a fixed fixture: every expected number is worked out by hand below."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import update
from sqlalchemy.orm import Session
from wardrobe_support import add_item

from app.models import Item
from app.services import insights as insights_service
from app.services.wear import today

INSIGHTS = "/api/v1/insights"


@pytest.fixture(autouse=True)
def fresh_cache() -> Iterator[None]:
    insights_service.without_cache()
    yield
    insights_service.without_cache()


def backdate(db: Session, item: dict[str, Any], days: int) -> None:
    when = datetime.now(UTC) - timedelta(days=days)
    db.execute(update(Item).where(Item.id == item["id"]).values(created_at=when))
    db.flush()


def log(client: TestClient, days_ago: int, *items: dict[str, Any]) -> None:
    response = client.post(
        "/api/v1/wear-logs",
        json={
            "worn_on": (today() - timedelta(days=days_ago)).isoformat(),
            "item_ids": [item["id"] for item in items],
        },
    )
    assert response.status_code == 201, response.text


def fixture(client: TestClient, db: Session) -> dict[str, dict[str, Any]]:
    client.patch("/api/v1/profile", json={"occasion_ids": ["college"]})
    w = {
        "white": add_item(client, "casual_shirt", "white", price=150000),  # ₹1,500
        "navy": add_item(client, "casual_shirt", "navy", price=200000),  # ₹2,000
        "chinos": add_item(client, "chinos", "beige", price=240000),  # ₹2,400
        "loafers": add_item(client, "loafers", "brown"),  # no price
        "tee": add_item(client, "tshirt", "olive", price=50000),  # never worn
        "sherwani": add_item(client, "sherwani", "cream"),  # never worn, suits no occasion
    }
    for item in w.values():
        backdate(db, item, 60)
    backdate(db, w["sherwani"], 200)
    # Five days logged: white x3, navy x2, chinos x4, loafers x5.
    log(client, 1, w["white"], w["chinos"], w["loafers"])
    log(client, 2, w["white"], w["chinos"], w["loafers"])
    log(client, 3, w["white"], w["chinos"], w["loafers"])
    log(client, 40, w["navy"], w["chinos"], w["loafers"])
    log(client, 41, w["navy"], w["loafers"])
    return w


def ids(rows: list[dict[str, Any]]) -> list[str]:
    return [row["item"]["id"] for row in rows]


def test_wear_counts_and_rankings(sam: TestClient, db: Session) -> None:
    w = fixture(sam, db)

    found = sam.get(INSIGHTS).json()

    assert (found["items"], found["logs"], found["days_logged_30"]) == (6, 5, 3)
    assert found["enough"] is True
    assert [(row["item"]["id"], row["wears"]) for row in found["most_worn"]] == [
        (w["loafers"]["id"], 5),
        (w["chinos"]["id"], 4),
        (w["white"]["id"], 3),
        (w["navy"]["id"], 2),
    ]
    # Least worn among things owned a month or more: never-worn first, by when they arrived.
    assert ids(found["least_worn"]) == [
        w["sherwani"]["id"],
        w["tee"]["id"],
        w["navy"]["id"],
        w["white"]["id"],
        w["chinos"]["id"],
    ]
    assert found["most_worn"][0]["last_worn_on"] == (today() - timedelta(days=1)).isoformat()


def test_cost_per_wear_only_where_there_is_a_price_and_a_wear(sam: TestClient, db: Session) -> None:
    w = fixture(sam, db)

    found = sam.get(INSIGHTS).json()

    # white 150000 / 3 = 50000; chinos 240000 / 4 = 60000; navy 200000 / 2 = 100000.
    assert [(row["item"]["id"], row["per_wear"]) for row in found["cheapest"]] == [
        (w["white"]["id"], 50000),
        (w["chinos"]["id"], 60000),
        (w["navy"]["id"], 100000),
    ]
    # Only three priced and worn: all are in the cheapest list, none left for the dearest.
    assert found["dearest"] == []
    # Worn but unpriced: "add a price". The tee has a price but no wears: not listed.
    assert [item["id"] for item in found["needs_price"]] == [w["loafers"]["id"]]


def test_wears_by_month_group_and_colour(sam: TestClient, db: Session) -> None:
    fixture(sam, db)
    days = [today() - timedelta(days=n) for n in (1, 2, 3, 40, 41)]
    expected: dict[str, int] = {}
    for day in days:
        key = f"{day.year:04d}-{day.month:02d}"
        expected[key] = expected.get(key, 0) + 1

    found = sam.get(INSIGHTS).json()

    months = {row["month"]: row["days"] for row in found["by_month"]}
    assert len(found["by_month"]) == 6
    assert {key: months[key] for key in expected} == expected
    assert sum(months.values()) == 5
    # Tops: white 3 + navy 2 = 5; footwear: 5; bottoms: 4. Ties keep the seed's order.
    assert [(row["id"], row["wears"]) for row in found["by_group"]] == [
        ("tops", 5),
        ("footwear", 5),
        ("bottoms", 4),
    ]
    assert [(row["id"], row["wears"]) for row in found["by_color"]] == [
        ("brown", 5),
        ("beige", 4),
        ("white", 3),
        ("navy", 2),
    ]


def test_the_worn_style_comes_from_what_is_worn(sam: TestClient, db: Session) -> None:
    fixture(sam, db)

    style = sam.get(INSIGHTS).json()["style"]

    # Core wears: loafers 5, chinos 4, white 3, navy 2 = 14, all at formality 3.
    assert style["wears"] == 14
    assert [(row["id"], row["share"]) for row in style["palette"]] == [
        ("brown", round(5 / 14, 4)),
        ("beige", round(4 / 14, 4)),
        ("white", round(3 / 14, 4)),
        ("navy", round(2 / 14, 4)),
    ]
    shares = {row["id"]: row["share"] for row in style["formality"]}
    assert shares == {"1": 0.0, "2": 0.0, "3": 1.0, "4": 0.0, "5": 0.0}


def test_versatility_coverage_and_declutter(sam: TestClient, db: Session) -> None:
    w = fixture(sam, db)

    found = sam.get(INSIGHTS).json()

    coverage = found["coverage"]
    assert coverage["occasion_ids"] == ["college"]
    assert coverage["seasons"] == ["summer", "monsoon", "winter", "mild"]
    assert all(cell["outfits"] > 0 for cell in coverage["cells"])
    orphans = {row["item"]["id"]: row for row in found["orphans"]}
    assert w["sherwani"]["id"] in orphans
    assert orphans[w["sherwani"]["id"]]["outfits"] == 0
    assert orphans[w["sherwani"]["id"]]["rescue"] == (
        "It's dressier or more casual than any occasion you dress for."
    )
    # Not worn and owned for over six months, and in no good outfit.
    assert [(row["item"]["id"], row["outfits"]) for row in found["declutter"]] == [
        (w["sherwani"]["id"], 0)
    ]
    assert found["versatile"][0]["outfits"] >= 2


def test_rankings_wait_for_enough_days(sam: TestClient) -> None:
    shirt = add_item(sam, "casual_shirt", "white", price=100000)
    log(sam, 1, shirt)

    found = sam.get(INSIGHTS).json()

    assert (found["logs"], found["needed_logs"], found["enough"]) == (1, 5, False)
    assert found["most_worn"] == [] and found["least_worn"] == []
    assert found["style"] is None
    # Cost per wear isn't a ranking of habits: it shows from the first wear.
    assert found["cheapest"][0]["per_wear"] == 100000


def test_coverage_waits_for_occasions(sam: TestClient) -> None:
    add_item(sam, "casual_shirt", "white")

    found = sam.get(INSIGHTS).json()

    assert (found["coverage"], found["versatile"], found["orphans"]) == (None, None, None)


def test_another_account_sees_only_its_own(sam: TestClient, ana: TestClient, db: Session) -> None:
    fixture(sam, db)

    theirs = ana.get(INSIGHTS).json()

    assert (theirs["items"], theirs["logs"]) == (0, 0)
    assert theirs["by_group"] == [] and theirs["cheapest"] == []


def test_insights_need_a_login(client: TestClient) -> None:
    assert client.get(INSIGHTS).status_code == 401
