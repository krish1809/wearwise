"""Shopping: candidates, analysis, buying, gaps, the capsule, the budget split, the guide."""

from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from photo_support import photo_bytes
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from wardrobe_support import add_item

from app.adapters.storage import MemoryStorage
from app.models import Candidate
from app.services import insights, shopping
from app.services.wear import today

CANDIDATES = "/api/v1/candidates"


@pytest.fixture(autouse=True)
def fresh_caches() -> Iterator[None]:
    insights.without_cache()
    shopping.without_cache()
    yield
    insights.without_cache()
    shopping.without_cache()


def candidate(client: TestClient, category_id: str, color: str, **fields: Any) -> dict[str, Any]:
    body = {"category_id": category_id, "color_primary": color, **fields}
    response = client.post(CANDIDATES, json=body)
    assert response.status_code == 201, response.text
    found: dict[str, Any] = response.json()
    return found


def college(client: TestClient) -> None:
    response = client.patch("/api/v1/profile", json={"occasion_ids": ["college"]})
    assert response.status_code == 200, response.text


def wardrobe(client: TestClient) -> dict[str, dict[str, Any]]:
    return {
        "white": add_item(client, "casual_shirt", "white", fabric="cotton"),
        "navy": add_item(client, "casual_shirt", "navy", fabric="cotton"),
        "chinos": add_item(client, "chinos", "beige", fabric="cotton"),
        "grey": add_item(client, "chinos", "grey", fabric="cotton"),
        "loafers": add_item(client, "loafers", "brown", fabric="leather"),
    }


def upload(client: TestClient) -> str:
    response = client.post(
        "/api/v1/photos", files={"file": ("shirt.png", photo_bytes(), "image/png")}
    )
    assert response.status_code == 201, response.text
    return str(response.json()["id"])


def test_a_candidate_takes_the_category_defaults_and_dates_its_price(sam: TestClient) -> None:
    found = candidate(sam, "chinos", "olive", price=199900, url="https://example.com/chinos")

    assert (found["slot"], found["status"], found["source"]) == ("bottom", "considering", "manual")
    assert found["formality"] == 3 and found["display_name"] == "Olive chinos"
    assert found["price_checked_at"] is not None
    assert found["verdict"] is None


def test_a_link_must_be_a_web_link(sam: TestClient) -> None:
    response = sam.post(
        CANDIDATES,
        json={"category_id": "tshirt", "color_primary": "white", "url": "javascript:alert(1)"},
    )

    assert response.status_code == 422
    assert "https://" in response.json()["error"]["fields"]["url"]


def test_a_status_is_one_of_the_list_and_purchased_comes_from_buying(sam: TestClient) -> None:
    found = candidate(sam, "tshirt", "white")

    later = sam.patch(f"{CANDIDATES}/{found['id']}", json={"status": "later"})
    bought = sam.patch(f"{CANDIDATES}/{found['id']}", json={"status": "purchased"})

    assert later.status_code == 200 and later.json()["status"] == "later"
    assert bought.status_code == 422


def test_analysis_waits_for_occasions(sam: TestClient) -> None:
    found = candidate(sam, "tshirt", "white")

    response = sam.get(f"{CANDIDATES}/{found['id']}/analysis")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "needs_occasions"
    assert sam.get(CANDIDATES).json()["needs_occasions"] is True


def test_a_duplicate_is_skip_and_names_what_you_own(sam: TestClient) -> None:
    college(sam)
    owned = wardrobe(sam)
    found = candidate(sam, "chinos", "beige", fabric="cotton", price=150000)

    analysis = sam.get(f"{CANDIDATES}/{found['id']}/analysis").json()

    assert analysis["verdict"] == "skip"
    assert analysis["closest"]["id"] == owned["chinos"]["id"]
    assert analysis["reasons"][0]["text"] == "Very close to your beige chinos."
    assert analysis["redundancy"] == pytest.approx(1.0)
    # The list now shows the verdict without working it out again.
    assert sam.get(CANDIDATES).json()["candidates"][0]["verdict"] == "skip"


def test_an_analysis_shows_matches_examples_and_cost_per_new_outfit(sam: TestClient) -> None:
    college(sam)
    owned = wardrobe(sam)
    found = candidate(sam, "chinos", "navy", fabric="cotton", price=180000)

    analysis = sam.get(f"{CANDIDATES}/{found['id']}/analysis").json()

    assert analysis["kind"] == "core"
    assert analysis["new_outfits"] >= 2
    matched = {match["item"]["id"] for match in analysis["matches"]}
    assert owned["white"]["id"] in matched and owned["loafers"]["id"] in matched
    assert all(m["item"]["slot"] != "bottom" for m in analysis["matches"])
    assert analysis["cost_per_new_outfit"] == round(180000 / analysis["new_outfits"])
    example = analysis["examples"][0]["pieces"]
    assert sum(1 for piece in example if piece["candidate"]) == 1
    assert len(analysis["cells"]) == 4
    # Too little wear history for an estimate of cost per wear.
    assert analysis["projected"] is None


def test_the_analysis_is_kept_until_the_wardrobe_changes(sam: TestClient, db: Session) -> None:
    college(sam)
    wardrobe(sam)
    found = candidate(sam, "chinos", "navy", fabric="cotton")
    url = f"{CANDIDATES}/{found['id']}/analysis"

    first = sam.get(url).json()
    row = db.scalar(select(Candidate).where(Candidate.id == found["id"]))
    assert row is not None
    key = row.analysis_key
    assert sam.get(url).json() == first
    db.refresh(row)
    assert row.analysis_key == key

    add_item(sam, "casual_shirt", "light_blue", fabric="cotton")
    second = sam.get(url).json()

    db.refresh(row)
    assert row.analysis_key != key
    assert second["new_outfits"] > first["new_outfits"]


def test_buying_makes_a_wardrobe_item_with_the_photo(sam: TestClient) -> None:
    photo = upload(sam)
    found = candidate(sam, "chinos", "olive", price=199900, photo_id=photo, name="Olive chinos")

    response = sam.post(
        f"{CANDIDATES}/{found['id']}/purchase", json={"price": 179900, "purchased_on": "2026-10-01"}
    )

    assert response.status_code == 201, response.text
    item = sam.get(f"/api/v1/items/{response.json()['item_id']}").json()
    assert (item["category_id"], item["color_primary"]) == ("chinos", "olive")
    assert item["price"] == 179900
    assert item["purchased_on"] == "2026-10-01"
    assert item["photo"]["id"] == photo
    after = sam.get(f"{CANDIDATES}/{found['id']}").json()
    assert (after["status"], after["item_id"]) == ("purchased", item["id"])
    again = sam.post(f"{CANDIDATES}/{found['id']}/purchase", json={})
    assert again.status_code == 409
    assert sam.patch(f"{CANDIDATES}/{found['id']}", json={"name": "x"}).status_code == 409


def test_a_purchase_date_cannot_be_in_the_future(sam: TestClient) -> None:
    found = candidate(sam, "tshirt", "white")

    response = sam.post(f"{CANDIDATES}/{found['id']}/purchase", json={"purchased_on": "2999-01-01"})

    assert response.status_code == 422


def test_a_candidate_photo_is_not_up_for_grabs(sam: TestClient) -> None:
    photo = upload(sam)
    candidate(sam, "tshirt", "white", photo_id=photo)

    response = sam.post(
        "/api/v1/items", json={"category_id": "tshirt", "color_primary": "white", "photo_id": photo}
    )

    assert response.status_code == 422


def test_deleting_a_candidate_deletes_its_photo(sam: TestClient, storage: MemoryStorage) -> None:
    found = candidate(sam, "tshirt", "white", photo_id=upload(sam))
    assert storage.files

    response = sam.delete(f"{CANDIDATES}/{found['id']}")

    assert response.status_code == 204
    assert storage.files == {}


def test_compare_shows_each_with_its_analysis(sam: TestClient) -> None:
    college(sam)
    wardrobe(sam)
    a = candidate(sam, "chinos", "navy", fabric="cotton")
    b = candidate(sam, "chinos", "beige", fabric="cotton")

    response = sam.get(f"{CANDIDATES}/compare", params=[("id", a["id"]), ("id", b["id"])])

    assert response.status_code == 200, response.text
    found = response.json()["candidates"]
    assert [entry["candidate"]["id"] for entry in found] == [a["id"], b["id"]]
    assert found[1]["analysis"]["verdict"] == "skip"


def test_gaps_rank_what_adds_most_and_staples_can_go_on_the_list(sam: TestClient) -> None:
    college(sam)
    add_item(sam, "casual_shirt", "white", fabric="cotton")
    add_item(sam, "chinos", "beige", fabric="cotton")

    found = sam.get("/api/v1/shopping/gaps").json()

    assert found["needs_occasions"] is False and found["covered"] is False
    first = found["gaps"][0]
    assert [staple["slot"] for staple in first["staples"]] == ["footwear"]
    assert first["coverage_gain"] > 0 and first["reason"]
    staple_id = first["staples"][0]["id"]

    added = sam.post(f"{CANDIDATES}/from-staple", json={"archetype_id": staple_id})

    assert added.status_code == 201, added.text
    assert added.json()["source"] == "archetype"
    again = sam.get("/api/v1/shopping/gaps").json()
    listed = {s["id"]: s["on_list"] for gap in again["gaps"] for s in gap["staples"]}
    assert listed[staple_id] is True


def test_a_capsule_from_nothing_starts_with_a_whole_outfit(sam: TestClient) -> None:
    sam.patch(
        "/api/v1/profile",
        json={
            "occasion_ids": ["college"],
            "sections": ["menswear"],
            "category_budgets": {"tops": 100000, "bottoms": 150000, "footwear": 250000},
        },
    )

    response = sam.post("/api/v1/shopping/capsule", json={"budget": 1000000})

    assert response.status_code == 200, response.text
    plan = response.json()
    first = plan["steps"][0]
    assert sorted(staple["slot"] for staple in first["staples"]) == ["bottom", "footwear", "top"]
    assert first["stage"] == 1
    assert plan["total"] is not None and plan["total"] <= 1000000
    assert {g["id"] for g in plan["unpriced_groups"]} >= {"layers"}


def test_the_budget_split_buys_what_works_together(sam: TestClient) -> None:
    college(sam)
    add_item(sam, "loafers", "brown", fabric="leather")
    shirt = candidate(sam, "casual_shirt", "white", fabric="cotton", price=100000)
    chinos = candidate(sam, "chinos", "navy", fabric="cotton", price=150000)
    candidate(sam, "blazer", "navy", price=400000)
    unpriced = candidate(sam, "tshirt", "grey")

    response = sam.post("/api/v1/shopping/split", json={"budget": 300000})

    assert response.status_code == 200, response.text
    found = response.json()
    assert {c["id"] for c in found["chosen"]} == {shirt["id"], chinos["id"]}
    assert found["spent"] == 250000 and found["spent"] <= found["budget"]
    assert [c["id"] for c in found["unpriced"]] == [unpriced["id"]]
    assert found["exhaustive"] is True


def test_the_guide_has_fabrics_colour_basics_and_styles(sam: TestClient) -> None:
    add_item(sam, "tshirt", "white", fabric="cotton", formality=2)

    guide = sam.get("/api/v1/guide").json()

    assert guide["fabrics"][0]["id"] == "cotton" and guide["fabrics"][0]["care"]
    assert {entry["id"] for entry in guide["colour"]} >= {"neutrals", "how_many", "leathers"}
    assert "navy" in {family["id"] for family in guide["neutrals"]}
    minimal = next(style for style in guide["styles"] if style["id"] == "minimal")
    owned = [piece for piece in minimal["pieces"] if piece["owned"]]
    assert [piece["staple"]["id"] for piece in owned] == ["white_tshirt"]


def test_a_custom_category_on_the_list_cannot_be_deleted(sam: TestClient) -> None:
    created = sam.post(
        "/api/v1/categories", json={"name": "Kurta pyjama", "group_id": "ethnic", "slot": "top"}
    )
    assert created.status_code == 201, created.text
    category = created.json()
    candidate(sam, category["id"], "white")

    response = sam.delete(f"/api/v1/categories/{category['id']}")

    assert response.status_code == 409
    assert "on your shopping list" in response.json()["error"]["message"]


def test_another_account_gets_404_for_every_candidate(sam: TestClient, ana: TestClient) -> None:
    found = candidate(sam, "tshirt", "white")
    url = f"{CANDIDATES}/{found['id']}"
    other = candidate(ana, "tshirt", "black")

    assert ana.get(url).status_code == 404
    assert ana.patch(url, json={"name": "mine"}).status_code == 404
    assert ana.get(f"{url}/analysis").status_code == 404
    assert ana.post(f"{url}/purchase", json={}).status_code == 404
    compare = ana.get(f"{CANDIDATES}/compare", params=[("id", found["id"]), ("id", other["id"])])
    assert compare.status_code == 404
    assert ana.delete(url).status_code == 404
    assert [c["id"] for c in ana.get(CANDIDATES).json()["candidates"]] == [other["id"]]
    assert sam.get(url).status_code == 200


def test_shopping_needs_a_login(client: TestClient) -> None:
    assert client.get(CANDIDATES).status_code == 401
    assert client.get("/api/v1/shopping/gaps").status_code == 401
    assert client.get("/api/v1/guide").status_code == 401


def test_deleting_the_account_removes_candidates_and_their_photos(
    sam: TestClient, db: Session, storage: MemoryStorage
) -> None:
    candidate(sam, "tshirt", "white", photo_id=upload(sam))

    response = sam.post("/api/v1/account/delete", json={"confirm_email": "sam@example.com"})

    assert response.status_code == 204, response.text
    assert db.scalar(select(Candidate)) is None
    assert storage.files == {}


def test_trying_a_candidate_with_pieces_you_own(sam: TestClient, ana: TestClient) -> None:
    college(sam)
    owned = wardrobe(sam)
    found = candidate(sam, "chinos", "olive", fabric="cotton")
    url = f"{CANDIDATES}/{found['id']}/try"

    part = sam.post(url, json={"item_ids": [owned["white"]["id"]]})
    whole = sam.post(
        url,
        json={"item_ids": [owned["white"]["id"], owned["loafers"]["id"]], "occasion_id": "college"},
    )
    theirs = ana.post(url, json={"item_ids": []})

    assert part.json()["complete"] is False and "footwear" in part.json()["message"]
    result = whole.json()
    assert result["complete"] is True and 0 < result["score"] <= 1
    assert result["good"] is (result["score"] >= 0.7) and result["reasons"]
    assert theirs.status_code == 404


def test_waiting_before_buying_asks_again_on_the_day(
    sam: TestClient, ana: TestClient, db: Session
) -> None:
    found = candidate(sam, "chinos", "olive")
    url = f"{CANDIDATES}/{found['id']}"
    week = (today() + timedelta(days=7)).isoformat()

    waiting = sam.patch(url, json={"remind_on": week})
    past = sam.patch(url, json={"remind_on": today().isoformat()})
    too_far = sam.patch(url, json={"remind_on": (today() + timedelta(days=400)).isoformat()})
    theirs = ana.patch(url, json={"remind_on": week})

    assert waiting.status_code == 200
    assert (waiting.json()["remind_on"], waiting.json()["reminder_due"]) == (week, False)
    assert past.status_code == 422 and too_far.status_code == 422
    assert theirs.status_code == 404

    # The day comes (set here directly: the API only takes days still to come).
    db.execute(update(Candidate).where(Candidate.id == found["id"]).values(remind_on=today()))
    db.flush()
    assert [c["reminder_due"] for c in sam.get(CANDIDATES).json()["candidates"]] == [True]

    # Skipping it ends the reminder; so does keeping it (clearing the day).
    skipped = sam.patch(url, json={"status": "skipped"}).json()
    assert (skipped["remind_on"], skipped["reminder_due"]) == (None, False)
    again = candidate(sam, "loafers", "brown")
    sam.patch(f"{CANDIDATES}/{again['id']}", json={"remind_on": week})
    kept = sam.patch(f"{CANDIDATES}/{again['id']}", json={"remind_on": None}).json()
    assert (kept["remind_on"], kept["status"]) == (None, "considering")
