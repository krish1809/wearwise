"""The outfit template rules, against the templates in seed/taxonomy.json."""

import json

import pytest

from app.engine.outfits import Piece, Template, check_outfit
from app.services.reference_seed import SEED_DIR

TEMPLATES = [
    Template.from_seed(t["id"], t["required"], t["optional"])
    for t in json.loads((SEED_DIR / "taxonomy.json").read_text())["outfit_templates"]
]

TOP = Piece("shirt", "top", "casual_shirt")
BOTTOM = Piece("chinos", "bottom", "chinos")
SHOES = Piece("loafers", "footwear", "loafers")
WATCH = Piece("watch", "watch", "watch")
DRESS = Piece("dress", "one_piece", "dress")
SAREE = Piece("saree", "one_piece", "saree")
BLOUSE = Piece("blouse", "top", "saree_blouse")


def test_top_bottom_and_footwear_make_an_outfit() -> None:
    check = check_outfit([TOP, BOTTOM, SHOES], TEMPLATES)

    assert check.complete
    assert check.template_id == "separates"


def test_accessories_and_a_layer_can_be_added() -> None:
    jacket = Piece("jacket", "layer", "denim_jacket")

    assert check_outfit([TOP, BOTTOM, SHOES, WATCH, jacket], TEMPLATES).complete


def test_a_top_needs_a_bottom_and_footwear() -> None:
    check = check_outfit([TOP], TEMPLATES)

    assert not check.complete
    assert check.template_id == "separates"
    assert check.missing == ("bottom", "footwear")


def test_a_one_piece_needs_no_top_or_bottom() -> None:
    check = check_outfit([DRESS, SHOES], TEMPLATES)

    assert check.complete
    assert check.template_id == "one_piece"


def test_a_one_piece_with_a_separate_bottom_has_a_piece_too_many() -> None:
    check = check_outfit([DRESS, BOTTOM, SHOES], TEMPLATES)

    assert not check.complete
    assert check.template_id == "one_piece"
    assert check.misplaced == (BOTTOM,)


def test_a_saree_needs_its_blouse() -> None:
    assert check_outfit([SAREE, BLOUSE, SHOES], TEMPLATES).template_id == "saree"
    assert check_outfit([SAREE, BLOUSE, SHOES], TEMPLATES).complete

    without_blouse = check_outfit([SAREE, SHOES], TEMPLATES)
    assert not without_blouse.complete
    assert without_blouse.template_id == "saree"
    assert without_blouse.missing == ("top",)


def test_a_saree_blouse_does_not_go_with_trousers() -> None:
    check = check_outfit([BLOUSE, BOTTOM, SHOES], TEMPLATES)

    assert not check.complete
    assert BLOUSE in check.misplaced


def test_two_items_in_one_slot_are_refused() -> None:
    second_watch = Piece("watch2", "watch", "watch")

    check = check_outfit([TOP, BOTTOM, SHOES, WATCH, second_watch], TEMPLATES)

    assert not check.complete
    assert check.crowded == ("watch",)


def test_a_slot_no_template_uses_is_misplaced() -> None:
    comb = Piece("comb", "grooming", "grooming_item")

    check = check_outfit([TOP, BOTTOM, SHOES, comb], TEMPLATES)

    assert not check.complete
    assert check.misplaced == (comb,)


@pytest.mark.parametrize("pieces", [[], [WATCH]])
def test_an_empty_start_points_at_the_first_template(pieces: list[Piece]) -> None:
    check = check_outfit(pieces, TEMPLATES)

    assert check.template_id == "separates"
    assert check.missing == ("top", "bottom", "footwear")


def test_no_templates_means_no_outfit() -> None:
    assert check_outfit([TOP], []) == check_outfit([TOP], [])
    assert not check_outfit([TOP], []).complete
    assert check_outfit([TOP], []).template_id is None
