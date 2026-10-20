from datetime import date, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from wardrobe_support import add_item

from app.api import suggestions as suggestion_routes
from app.engine.config import ENGINE_VERSION
from app.models import Outfit, Suggestion, SuggestionFeedback, WearLog
from app.services import rate_limit

SUGGEST = "/api/v1/outfits/suggest"
SUGGESTIONS = "/api/v1/suggestions"


def wardrobe(client: TestClient) -> dict[str, dict[str, Any]]:
    return {
        "shirt": add_item(client, "casual_shirt", "white", fabric="cotton"),
        "tee": add_item(client, "tshirt", "navy", fabric="cotton"),
        "chinos": add_item(client, "chinos", "beige", fabric="cotton"),
        "jeans": add_item(client, "jeans", "denim_blue", fabric="denim"),
        "sneakers": add_item(client, "sneakers", "white", fabric="canvas"),
        "loafers": add_item(client, "loafers", "brown", fabric="leather"),
    }


def ask(client: TestClient, **body: Any) -> dict[str, Any]:
    response = client.post(SUGGEST, json={"occasion_id": "college", "season": "mild", **body})
    assert response.status_code == 200, response.text
    found: dict[str, Any] = response.json()
    return found


def core_of(suggestion: dict[str, Any]) -> frozenset[str]:
    return frozenset(piece["item"]["id"] for piece in suggestion["pieces"] if piece["core"])


def test_suggestions_are_whole_outfits_with_reasons(sam: TestClient) -> None:
    wardrobe(sam)

    result = ask(sam)

    assert result["engine_version"] == ENGINE_VERSION
    assert result["season"] == "mild"
    assert result["missing"] == []
    assert result["suggestions"]
    for suggestion in result["suggestions"]:
        slots = [piece["slot"] for piece in suggestion["pieces"]]
        assert {"top", "bottom", "footwear"} <= set(slots)
        assert len(slots) == len(set(slots))
        assert 0 <= suggestion["score"] <= 1
        assert suggestion["kind"] == "occasion"
        assert suggestion["reasons"]
        assert suggestion["rating"] is None
        assert suggestion["stale"] is False


def test_each_suggestion_shown_is_kept_with_its_engine_version(
    sam: TestClient, db: Session
) -> None:
    wardrobe(sam)

    result = ask(sam, count=3)

    rows = list(db.scalars(select(Suggestion)))
    assert sorted(str(row.id) for row in rows) == sorted(s["id"] for s in result["suggestions"])
    assert {row.engine_version for row in rows} == {ENGINE_VERSION}


def test_an_occasion_is_needed_unless_pieces_are_given(sam: TestClient) -> None:
    response = sam.post(SUGGEST, json={})

    assert response.status_code == 422
    assert response.json()["error"]["fields"]["occasion_id"] == "Choose an occasion."


@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"occasion_id": "brunch"}, "occasion_id"),
        ({"occasion_id": "college", "season": "spring"}, "season"),
        ({"occasion_id": "college", "style_id": "goth"}, "style_id"),
        ({"occasion_id": "college", "count": 50}, "count"),
    ],
)
def test_unknown_choices_are_refused(sam: TestClient, body: dict[str, Any], field: str) -> None:
    response = sam.post(SUGGEST, json=body)

    assert response.status_code == 422
    assert field in response.json()["error"]["fields"]


def test_what_goes_with_this_keeps_the_piece_in_every_outfit(sam: TestClient) -> None:
    w = wardrobe(sam)

    result = ask(sam, occasion_id=None, anchor_item_ids=[w["jeans"]["id"]])

    assert result["suggestions"]
    for suggestion in result["suggestions"]:
        assert suggestion["kind"] == "with_item"
        assert w["jeans"]["id"] in core_of(suggestion)


def test_completing_an_outfit_keeps_both_pieces(sam: TestClient) -> None:
    w = wardrobe(sam)

    result = ask(sam, anchor_item_ids=[w["shirt"]["id"], w["chinos"]["id"]])

    for suggestion in result["suggestions"]:
        assert suggestion["kind"] == "complete"
        assert {w["shirt"]["id"], w["chinos"]["id"]} <= core_of(suggestion)


def test_two_pieces_for_one_slot_are_refused(sam: TestClient) -> None:
    w = wardrobe(sam)

    response = sam.post(
        SUGGEST,
        json={"occasion_id": "college", "anchor_item_ids": [w["shirt"]["id"], w["tee"]["id"]]},
    )

    assert response.status_code == 422
    assert response.json()["error"]["fields"]["anchor_item_ids"] == "Choose one item per slot."


def test_pieces_in_the_laundry_are_not_suggested(sam: TestClient) -> None:
    w = wardrobe(sam)
    sam.patch(f"/api/v1/items/{w['shirt']['id']}", json={"status": "laundry"})

    result = ask(sam)

    used = {piece["item"]["id"] for s in result["suggestions"] for piece in s["pieces"]}
    assert w["shirt"]["id"] not in used


def test_a_missing_slot_is_named_with_a_reason(sam: TestClient) -> None:
    add_item(sam, "casual_shirt", "white")
    add_item(sam, "chinos", "beige")

    result = ask(sam)

    assert result["suggestions"] == []
    assert result["missing"] == [
        {
            "slot": "footwear",
            "slot_name": "Footwear",
            "code": "missing.none_owned",
            "text": "There's no footwear in your wardrobe yet.",
        }
    ]


def test_a_like_can_become_a_dislike_and_be_taken_back(sam: TestClient, db: Session) -> None:
    wardrobe(sam)
    suggestion = ask(sam)["suggestions"][0]
    url = f"{SUGGESTIONS}/{suggestion['id']}/feedback"

    liked = sam.post(url, json={"verdict": "like"}).json()
    disliked = sam.post(url, json={"verdict": "dislike", "reason": "colors"}).json()

    assert liked["rating"] == "like"
    assert disliked["rating"] == "dislike"
    rows = list(db.scalars(select(SuggestionFeedback)))
    assert [(row.verdict, row.reason) for row in rows] == [("dislike", "colors")]

    cleared = sam.delete(url).json()
    assert cleared["rating"] is None
    assert db.scalar(select(func.count()).select_from(SuggestionFeedback)) == 0


def test_a_dislike_of_one_piece_names_a_piece_of_the_outfit(sam: TestClient, db: Session) -> None:
    w = wardrobe(sam)
    suggestion = ask(sam)["suggestions"][0]
    url = f"{SUGGESTIONS}/{suggestion['id']}/feedback"
    piece = suggestion["pieces"][0]["item"]["id"]
    outside = next(i["id"] for i in w.values() if i["id"] not in core_of(suggestion))

    missing = sam.post(url, json={"verdict": "dislike", "reason": "item"})
    wrong = sam.post(url, json={"verdict": "dislike", "reason": "item", "item_id": outside})
    reason_on_like = sam.post(url, json={"verdict": "like", "reason": "colors"})
    ok = sam.post(url, json={"verdict": "dislike", "reason": "item", "item_id": piece})

    assert missing.status_code == 422
    assert wrong.json()["error"]["fields"]["item_id"] == "That piece isn't in this outfit."
    assert reason_on_like.json()["error"]["fields"]["reason"] == "Only a dislike takes a reason."
    assert ok.status_code == 200
    row = db.scalars(select(SuggestionFeedback)).one()
    assert str(row.item_id) == piece


def test_liking_an_outfit_raises_it_next_time(sam: TestClient) -> None:
    wardrobe(sam)
    first = ask(sam)["suggestions"]
    chosen = first[-1]

    sam.post(f"{SUGGESTIONS}/{chosen['id']}/feedback", json={"verdict": "like"})
    again = ask(sam)["suggestions"]

    after = next(s for s in again if core_of(s) == core_of(chosen))
    assert after["score"] > chosen["score"]


def test_a_disliked_outfit_drops(sam: TestClient) -> None:
    wardrobe(sam)
    best = ask(sam)["suggestions"][0]

    sam.post(f"{SUGGESTIONS}/{best['id']}/feedback", json={"verdict": "dislike"})
    again = ask(sam)["suggestions"]

    after = next(s for s in again if core_of(s) == core_of(best))
    assert after["score"] < best["score"]


def test_saving_makes_an_engine_outfit_once(sam: TestClient, db: Session) -> None:
    wardrobe(sam)
    suggestion = ask(sam)["suggestions"][0]
    url = f"{SUGGESTIONS}/{suggestion['id']}/save"

    first = sam.post(url, json={"name": "Thursday", "is_favorite": True})
    second = sam.post(url, json={})

    assert first.status_code == 201
    assert second.status_code == 200
    outfit = first.json()
    assert second.json()["id"] == outfit["id"]
    assert outfit["source"] == "engine"
    assert outfit["engine_version"] == ENGINE_VERSION
    assert outfit["name"] == "Thursday"
    assert outfit["is_favorite"] is True
    assert outfit["occasion_id"] == "college"
    assert outfit["reasons"] == suggestion["reasons"]
    assert db.scalar(select(func.count()).select_from(Outfit)) == 1
    verdicts = list(db.scalars(select(SuggestionFeedback.verdict)))
    assert verdicts == ["saved"]


def test_wearing_logs_the_outfit_once(sam: TestClient, db: Session) -> None:
    wardrobe(sam)
    suggestion = ask(sam)["suggestions"][0]
    url = f"{SUGGESTIONS}/{suggestion['id']}/wear"
    today = date.today().isoformat()

    first = sam.post(url, json={"worn_on": today})
    second = sam.post(url, json={"worn_on": today})

    assert first.status_code == 201
    assert second.status_code == 200
    assert second.json()["id"] == first.json()["id"]
    worn = {piece["item"]["id"] for piece in first.json()["pieces"]}
    assert worn == {piece["item"]["id"] for piece in suggestion["pieces"]}
    assert db.scalar(select(func.count()).select_from(WearLog)) == 1
    assert list(db.scalars(select(SuggestionFeedback.verdict))) == ["worn"]


def test_a_saved_suggestion_is_worn_as_its_outfit(sam: TestClient) -> None:
    wardrobe(sam)
    suggestion = ask(sam)["suggestions"][0]
    outfit = sam.post(f"{SUGGESTIONS}/{suggestion['id']}/save", json={}).json()

    log = sam.post(
        f"{SUGGESTIONS}/{suggestion['id']}/wear", json={"worn_on": date.today().isoformat()}
    ).json()

    assert log["outfit_id"] == outfit["id"]


def test_a_worn_outfit_is_not_suggested_first_again_this_week(sam: TestClient) -> None:
    wardrobe(sam)
    best = ask(sam)["suggestions"][0]
    sam.post(f"{SUGGESTIONS}/{best['id']}/wear", json={"worn_on": date.today().isoformat()})

    again = ask(sam)["suggestions"]

    assert core_of(again[0]) != core_of(best)


def test_a_suggestion_with_a_deleted_piece_is_stale(sam: TestClient) -> None:
    wardrobe(sam)
    suggestion = ask(sam)["suggestions"][0]
    piece = suggestion["pieces"][0]["item"]["id"]
    sam.delete(f"/api/v1/items/{piece}")

    save = sam.post(f"{SUGGESTIONS}/{suggestion['id']}/save", json={})
    wear = sam.post(
        f"{SUGGESTIONS}/{suggestion['id']}/wear", json={"worn_on": date.today().isoformat()}
    )
    rated = sam.post(f"{SUGGESTIONS}/{suggestion['id']}/feedback", json={"verdict": "like"})

    assert save.status_code == 409
    assert save.json()["error"]["code"] == "suggestion_stale"
    assert wear.status_code == 409
    assert rated.json()["stale"] is True


def test_wearing_on_a_future_day_is_refused(sam: TestClient) -> None:
    wardrobe(sam)
    suggestion = ask(sam)["suggestions"][0]
    later = (date.today() + timedelta(days=5)).isoformat()

    response = sam.post(f"{SUGGESTIONS}/{suggestion['id']}/wear", json={"worn_on": later})

    assert response.status_code == 422
    assert "worn_on" in response.json()["error"]["fields"]


def test_another_account_cannot_see_or_use_a_suggestion(sam: TestClient, ana: TestClient) -> None:
    w = wardrobe(sam)
    suggestion = ask(sam)["suggestions"][0]
    base = f"{SUGGESTIONS}/{suggestion['id']}"
    today = date.today().isoformat()

    assert ana.post(f"{base}/feedback", json={"verdict": "like"}).status_code == 404
    assert ana.delete(f"{base}/feedback").status_code == 404
    assert ana.post(f"{base}/save", json={}).status_code == 404
    assert ana.post(f"{base}/wear", json={"worn_on": today}).status_code == 404
    # Nor build outfits around someone else's piece, or from their wardrobe.
    borrowed = ana.post(SUGGEST, json={"anchor_item_ids": [w["shirt"]["id"]]})
    assert borrowed.status_code == 422
    assert ana.post(SUGGEST, json={"occasion_id": "college"}).json()["suggestions"] == []


def test_suggestions_are_rate_limited(sam: TestClient, monkeypatch: pytest.MonkeyPatch) -> None:
    wardrobe(sam)
    monkeypatch.setattr(
        suggestion_routes,
        "SUGGESTIONS_PER_USER",
        rate_limit.Limit(attempts=1, window=timedelta(hours=1)),
    )

    assert sam.post(SUGGEST, json={"occasion_id": "college"}).status_code == 200
    second = sam.post(SUGGEST, json={"occasion_id": "college"})

    assert second.status_code == 429
    assert second.json()["error"]["code"] == "rate_limited"


def test_deleting_the_account_removes_suggestions_and_feedback(
    sam: TestClient, db: Session
) -> None:
    wardrobe(sam)
    suggestion = ask(sam)["suggestions"][0]
    sam.post(f"{SUGGESTIONS}/{suggestion['id']}/feedback", json={"verdict": "like"})
    email = sam.get("/api/v1/auth/me").json()["email"]

    assert sam.post("/api/v1/account/delete", json={"confirm_email": email}).status_code == 204

    assert db.scalar(select(func.count()).select_from(Suggestion)) == 0
    assert db.scalar(select(func.count()).select_from(SuggestionFeedback)) == 0


def test_swapping_a_piece_clears_the_saved_reasons(sam: TestClient) -> None:
    w = wardrobe(sam)
    suggestion = ask(sam)["suggestions"][0]
    outfit = sam.post(f"{SUGGESTIONS}/{suggestion['id']}/save", json={}).json()
    pieces = [piece["item"]["id"] for piece in outfit["pieces"]]
    renamed = sam.patch(f"/api/v1/outfits/{outfit['id']}", json={"name": "Kept"}).json()
    shoes = next(p["item"] for p in outfit["pieces"] if p["slot"] == "footwear")
    other = w["loafers"] if shoes["id"] == w["sneakers"]["id"] else w["sneakers"]
    swapped_ids = [other["id"] if item_id == shoes["id"] else item_id for item_id in pieces]

    same = sam.patch(f"/api/v1/outfits/{outfit['id']}", json={"item_ids": pieces}).json()
    swapped = sam.patch(f"/api/v1/outfits/{outfit['id']}", json={"item_ids": swapped_ids}).json()

    assert renamed["reasons"] == suggestion["reasons"]
    assert same["reasons"] == suggestion["reasons"]
    assert swapped["reasons"] == []
    assert swapped["score"] is None
    assert swapped["source"] == "engine"
