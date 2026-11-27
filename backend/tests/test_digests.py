"""This week's picks (docs/AGENTS.md, section 5): worked out from approved trends and the
person's own wardrobe, with links only from the shop-search adapter, "not for me" that sticks,
and nothing of anyone else's."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session
from wardrobe_support import add_item

from app.api import digests as digest_routes
from app.models import Digest, DigestPick, Trend, User
from app.services import rate_limit, trends

LATEST = "/api/v1/digests/latest"
PREVIEW = "/api/v1/digests/preview"
NOW = datetime.now(UTC)


def a_trend(db: Session, name: str, status: str = "approved", **fields: Any) -> Trend:
    values: dict[str, Any] = {
        "summary": f"{name}, everywhere this season.",
        "why_now": "Warm afternoons.",
        "category_ids": ["chinos"],
        "color_families": ["olive"],
        "fabrics": ["cotton"],
        "sections": ["menswear"],
        "style_profile_ids": ["minimal"],
        **fields,
    }
    trend = Trend(
        name=name,
        name_key=trends.name_key(name),
        status=status,
        first_seen_at=NOW,
        last_seen_at=NOW,
        **values,
    )
    db.add(trend)
    db.flush()
    return trend


def dresses_for_college(client: TestClient) -> dict[str, dict[str, Any]]:
    """A small wardrobe that makes college outfits, with a usual spend for bottoms."""
    client.patch(
        "/api/v1/profile",
        json={
            "sections": ["menswear"],
            "occasion_ids": ["college"],
            "category_budgets": {"bottoms": 150000},
        },
    )
    return {
        "white shirt": add_item(client, "casual_shirt", "white", fabric="cotton"),
        "navy shirt": add_item(client, "casual_shirt", "navy", fabric="cotton"),
        "black tee": add_item(client, "tshirt", "black", fabric="cotton"),
        "beige chinos": add_item(client, "chinos", "beige", fabric="cotton"),
        "sneakers": add_item(client, "sneakers", "white"),
        "loafers": add_item(client, "loafers", "brown", fabric="leather"),
    }


def test_this_weeks_picks_come_from_approved_trends_and_the_persons_own_wardrobe(
    db: Session, sam: TestClient
) -> None:
    owned = dresses_for_college(sam)
    a_trend(db, "Olive chinos")
    a_trend(db, "Waiting trend", status="pending", color_families=["rust"])

    digest = sam.post(PREVIEW).json()

    assert digest["status"] == "built"
    [pick] = digest["picks"]
    assert (pick["kind"], pick["name"], pick["trend_name"]) == (
        "buy",
        "Olive cotton chinos",
        "Olive chinos",
    )
    assert pick["verdict"] in ("buy", "consider") and pick["new_outfits"] >= 2
    assert pick["text"] == (
        f"Olive cotton chinos would make {pick['new_outfits']} new outfits with what you own."
    )
    assert pick["reasons"] and pick["usual_spend"] == 150000
    # Where to look comes from the shop-search adapter, and nothing else.
    assert pick["query"] == "Olive cotton chinos men"
    assert [link["shop"] for link in pick["links"]] == ["Myntra", "AJIO", "Flipkart", "Amazon"]
    assert all(link["url"].startswith("https://www.") for link in pick["links"])
    # Only the person's own pieces are named, each with its photo reference.
    ids = {item["id"] for item in owned.values()}
    assert pick["items"] and {item["id"] for item in pick["items"]} <= ids
    assert digest["subject"] == "Worth a look this week: olive cotton chinos"
    assert sam.get(LATEST).json()["id"] == digest["id"]


def test_a_trend_already_owned_shows_the_piece_and_what_to_wear_it_with(
    db: Session, sam: TestClient
) -> None:
    owned = dresses_for_college(sam)
    a_trend(db, "Beige chinos are back", color_families=["beige"])

    [pick] = sam.post(PREVIEW).json()["picks"]

    assert pick["kind"] == "owned" and pick["links"] == [] and pick["verdict"] is None
    assert pick["items"][0]["id"] == owned["beige chinos"]["id"]
    assert pick["text"].startswith("You already have one: your beige chinos.")
    assert pick["trend_name"] == "Beige chinos are back"


def test_not_for_me_sticks_through_a_new_week_of_picks_and_can_be_undone(
    db: Session, sam: TestClient
) -> None:
    dresses_for_college(sam)
    a_trend(db, "Olive chinos")
    [pick] = sam.post(PREVIEW).json()["picks"]

    declined = sam.post(f"/api/v1/digest-picks/{pick['id']}/not-for-me").json()
    again = sam.post(PREVIEW).json()
    undone = sam.delete(f"/api/v1/digest-picks/{pick['id']}/not-for-me").json()

    assert declined["picks"][0]["not_for_me"] is True
    # Worked out again: the declined trend isn't picked, and the answer is kept.
    assert again["status"] == "nothing"
    assert [(p["id"], p["not_for_me"]) for p in again["picks"]] == [(pick["id"], True)]
    assert "good week to buy nothing" in again["note"]
    assert undone["picks"][0]["not_for_me"] is False


def test_someone_elses_picks_are_not_there(db: Session, sam: TestClient, ana: TestClient) -> None:
    dresses_for_college(sam)
    a_trend(db, "Olive chinos")
    [pick] = sam.post(PREVIEW).json()["picks"]

    assert ana.get(LATEST).status_code == 404
    assert ana.post(f"/api/v1/digest-picks/{pick['id']}/not-for-me").status_code == 404
    assert ana.delete(f"/api/v1/digest-picks/{pick['id']}/not-for-me").status_code == 404
    assert sam.get(LATEST).json()["picks"][0]["not_for_me"] is False


@pytest.mark.parametrize(
    ("occasions", "approved", "note"),
    [
        (False, True, "Choose the occasions you dress for first"),
        (True, False, "No trends have been approved for your sections yet."),
    ],
)
def test_with_nothing_to_go_on_it_says_why(
    db: Session, sam: TestClient, occasions: bool, approved: bool, note: str
) -> None:
    if occasions:
        dresses_for_college(sam)
    if approved:
        a_trend(db, "Olive chinos")

    digest = sam.post(PREVIEW).json()

    assert (digest["status"], digest["picks"]) == ("nothing", [])
    assert digest["note"].startswith(note)
    assert digest["subject"] == "Nothing worth buying this week"


def test_a_weeks_email_once_sent_stays_as_it_was_sent(db: Session, sam: TestClient) -> None:
    dresses_for_college(sam)
    a_trend(db, "Olive chinos")
    first = sam.post(PREVIEW).json()
    sent = db.get_one(Digest, first["id"])
    sent.status = "sent"
    db.flush()
    a_trend(db, "Grey trousers", category_ids=["casual_trousers"], color_families=["grey"])

    again = sam.post(PREVIEW).json()

    assert again["id"] == first["id"]
    assert [p["id"] for p in again["picks"]] == [p["id"] for p in first["picks"]]


def test_working_out_picks_is_limited(
    db: Session, sam: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(digest_routes, "PREVIEWS_PER_USER", rate_limit.Limit(1, timedelta(hours=1)))

    assert sam.post(PREVIEW).status_code == 200
    assert sam.post(PREVIEW).status_code == 429


def test_an_avoided_colour_is_never_suggested(db: Session, sam: TestClient) -> None:
    dresses_for_college(sam)
    sam.patch("/api/v1/profile", json={"avoided_colors": ["olive"]})
    a_trend(db, "Olive chinos")

    assert sam.post(PREVIEW).json()["picks"] == []


def test_deleting_the_account_deletes_the_picks(db: Session, sam: TestClient) -> None:
    dresses_for_college(sam)
    a_trend(db, "Olive chinos")
    sam.post(PREVIEW)
    user = db.scalars(select(User).where(User.email == "sam@example.com")).one()
    user_id = user.id

    deleted = sam.post("/api/v1/account/delete", json={"confirm_email": "sam@example.com"})

    assert deleted.status_code == 204

    assert db.scalars(select(Digest).where(Digest.user_id == user_id)).all() == []


def test_a_pick_never_shows_someone_elses_piece(
    db: Session, sam: TestClient, ana: TestClient
) -> None:
    dresses_for_college(sam)
    theirs = add_item(ana, "chinos", "olive", fabric="cotton")
    a_trend(db, "Olive chinos")
    [pick] = sam.post(PREVIEW).json()["picks"]
    row = db.get_one(DigestPick, uuid.UUID(pick["id"]))
    row.item_ids = [*row.item_ids, uuid.UUID(theirs["id"])]
    db.flush()

    shown = sam.get(LATEST).json()["picks"][0]["items"]

    assert theirs["id"] not in {item["id"] for item in shown}
