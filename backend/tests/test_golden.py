"""The golden set: the measure itself, the export, and (once labelled) the real check."""

import csv
import io
import json
import sys
from contextlib import nullcontext
from pathlib import Path

import pytest
from engine_support import OCCASIONS, context, make, wardrobe
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from wardrobe_support import add_item, save_outfit

from app.engine.generate import suggest
from app.engine.golden import (
    OWNER,
    Label,
    agreement,
    candidate_pairs,
    item_from_dict,
    item_to_dict,
    read_labels,
    write_pairs,
)
from scripts import export_golden

GOLDEN = Path(__file__).parent / "golden"
# The pass marks from docs/ENGINE.md, section 9.
MIN_LABELLED = 60
PASS_SHARE = 0.80
TOP = 20


def test_agreement_counts_good_pairs_scored_above_bad_ones() -> None:
    shirt, chinos = make("casual_shirt", "white"), make("chinos", "navy")
    red, yellow = make("casual_shirt", "red"), make("chinos", "yellow")
    items = {item.id: item for item in (shirt, chinos, red, yellow)}

    agrees = agreement(items, [Label(shirt.id, chinos.id, "good"), Label(red.id, yellow.id, "bad")])
    disagrees = agreement(
        items, [Label(shirt.id, chinos.id, "bad"), Label(red.id, yellow.id, "good")]
    )
    ties = agreement(items, [Label(shirt.id, chinos.id, "good"), Label(shirt.id, chinos.id, "bad")])

    assert (agrees.share, agrees.comparisons) == (1.0, 1)
    assert disagrees.share == 0.0
    assert ties.share == 0.5


def test_fine_pairs_are_kept_but_not_compared() -> None:
    a, b = make("casual_shirt", "white"), make("chinos", "navy")

    result = agreement({a.id: a, b.id: b}, [Label(a.id, b.id, "fine")])

    assert (result.comparisons, result.labelled) == (0, 1)


def test_blank_and_unknown_labels_are_skipped() -> None:
    text = "a,b,a_name,b_name,label\ni01,i02,x,y,Good\ni01,i03,x,z,\ni02,i03,y,z,maybe\n"

    assert read_labels(text) == [Label("i01", "i02", "good")]


def test_an_item_survives_the_trip_through_json() -> None:
    item = make("casual_shirt", "olive", seasons=frozenset({"summer"}), set_id="s1")

    back = item_from_dict(json.loads(json.dumps(item_to_dict(item, "i07"))))

    assert back.id == "i07"
    assert back.owner_id == OWNER
    assert back.seasons == frozenset({"summer"})
    assert back.last_worn_on is None
    assert (back.color_hex, back.formality, back.set_id) == (item.color_hex, item.formality, "s1")


def test_candidate_pairs_cover_the_score_range_and_the_main_slot_pairs() -> None:
    items = [
        *(make("casual_shirt", c) for c in ("white", "red", "olive", "black")),
        *(make("chinos", c) for c in ("navy", "yellow", "beige")),
        *(make("sneakers", c) for c in ("white", "maroon")),
        make("watch", "silver"),
    ]

    pairs = candidate_pairs(items, 8)
    rows = list(csv.DictReader(io.StringIO(write_pairs(pairs))))

    assert len(pairs) == 8
    assert all({a.slot, b.slot} in ({"top", "bottom"}, {"bottom", "footwear"}) for a, b in pairs)
    assert all(row["label"] == "" for row in rows)


def test_the_export_writes_the_wardrobe_pairs_and_favourites(
    sam: TestClient, db: Session, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    shirt = add_item(sam, "casual_shirt", "white")
    chinos = add_item(sam, "chinos", "navy")
    shoes = add_item(sam, "loafers", "brown")
    add_item(sam, "jeans", "denim_blue")
    save_outfit(sam, shirt, chinos, shoes, is_favorite=True, occasion_id="college")
    email = sam.get("/api/v1/auth/me").json()["email"]
    monkeypatch.setattr(export_golden, "get_sessionmaker", lambda: lambda: nullcontext(db))
    monkeypatch.setattr(sys, "argv", ["export_golden", "--email", email, "--out", str(tmp_path)])

    export_golden.main()

    items = json.loads((tmp_path / "items.json").read_text())
    loved = json.loads((tmp_path / "outfits.json").read_text())
    pairs = list(csv.DictReader(io.StringIO((tmp_path / "pairs.csv").read_text())))
    assert sorted(item["id"] for item in items) == ["i01", "i02", "i03", "i04"]
    assert all("photo" not in item for item in items)
    assert [(o["occasion"], len(o["items"])) for o in loved] == [("college", 3)]
    assert pairs and all(row["label"] == "" for row in pairs)


def test_the_export_keeps_labels_unless_forced(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "pairs.csv").write_text("a,b,a_name,b_name,label\ni01,i02,x,y,good\n")
    monkeypatch.setattr(
        sys, "argv", ["export_golden", "--email", "x@example.com", "--out", str(tmp_path)]
    )

    with pytest.raises(SystemExit, match="already has labels"):
        export_golden.main()


def test_the_engine_agrees_with_the_owners_labels() -> None:
    """The real golden set. Skipped until the owner has labelled their own pairs."""
    pairs_file = GOLDEN / "pairs.csv"
    labels = read_labels(pairs_file.read_text()) if pairs_file.exists() else []
    if len(labels) < MIN_LABELLED:
        pytest.skip(
            f"Golden set not labelled yet ({len(labels)} of {MIN_LABELLED} pairs): run "
            "scripts/export_golden.py and label tests/golden/pairs.csv."
        )
    items = {
        data["id"]: item_from_dict(data) for data in json.loads((GOLDEN / "items.json").read_text())
    }

    result = agreement(items, labels)

    print(f"Golden pairs: {result.share:.1%} agreement over {result.comparisons} comparisons")
    assert result.share >= PASS_SHARE, f"{result.share:.1%} is below {PASS_SHARE:.0%}"


def test_each_loved_outfit_is_in_the_top_twenty_for_its_occasion() -> None:
    outfits_file = GOLDEN / "outfits.json"
    loved = json.loads(outfits_file.read_text()) if outfits_file.exists() else []
    if not loved:
        pytest.skip("No loved outfits in tests/golden/outfits.json yet.")
    items = [item_from_dict(data) for data in json.loads((GOLDEN / "items.json").read_text())]

    missed = []
    for outfit in loved:
        result = suggest(
            wardrobe(*items),
            context(outfit["occasion"], user_id=OWNER, season=None, count=TOP),
        )
        shown = {frozenset(found.core_ids) for found in result.outfits}
        if frozenset(outfit["items"]) not in shown:
            missed.append(f"{outfit['name'] or outfit['items']} ({outfit['occasion']})")

    assert not missed, f"Not in the top {TOP}: {', '.join(missed)}"
    assert all(outfit["occasion"] in OCCASIONS for outfit in loved)
