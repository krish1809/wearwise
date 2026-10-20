"""The wardrobe graph and the worn style (docs/ENGINE.md, section 11)."""

import time

import pytest
from engine_support import COLORS, OCCASIONS, SLOT_KINDS, STYLES, context, make, wardrobe
from test_engine_generate import big_wardrobe

from app.engine.generate import good_cores
from app.engine.insights import Family, measure, steady, worn_style
from app.engine.types import EngineItem

FAMILIES = [Family(c["id"], c["name"], c["hex"], c["neutrality"]) for c in COLORS.values()]
SEASONS = ["summer", "monsoon", "winter", "mild"]


def basics() -> list[EngineItem]:
    return [
        make("casual_shirt", "white", fabric="cotton"),
        make("casual_shirt", "navy", fabric="cotton"),
        make("chinos", "beige", fabric="cotton"),
        make("chinos", "grey", fabric="cotton"),
        make("loafers", "brown", fabric="leather"),
    ]


def test_versatility_counts_the_good_outfits_an_item_is_in() -> None:
    items = basics()
    w = wardrobe(*items)
    ctx = context()

    measures = measure(w, ctx, [OCCASIONS["college"]], ["mild"], FAMILIES)

    good = good_cores(steady(w), ctx, 0.7)
    for item in items:
        expected = sum(1 for outfit in good if item.id in outfit.core_ids)
        assert measures.versatility[item.id] == expected
    # Two shirts, two chinos, one pair of loafers: four outfits, every one with the loafers.
    assert len(good) == 4
    assert measures.versatility[items[4].id] == 4
    assert measures.coverage[("college", "mild")] == 4


def test_an_item_that_goes_with_nothing_is_an_orphan_with_a_way_out() -> None:
    clash = make("casual_shirt", "yellow", pattern="graphic", fabric="polyester")
    loud = make("chinos", "purple", pattern="check")
    shoes = make("sneakers", "red", pattern="graphic")

    measures = measure(
        wardrobe(clash, loud, shoes), context(), [OCCASIONS["college"]], ["mild"], FAMILIES
    )

    assert clash.id in measures.orphans
    rescue = measures.rescues[clash.id]
    assert rescue.code == "rescue.slot"
    assert rescue.text.startswith("Nothing you have for the ")
    assert rescue.text.endswith(" one would.")


def test_a_piece_too_dressy_for_every_occasion_says_so() -> None:
    sherwani = make("sherwani", "cream")
    items = [*basics(), sherwani, make("ethnic_bottom", "cream", formality=5)]

    measures = measure(wardrobe(*items), context(), [OCCASIONS["college"]], ["mild"], FAMILIES)

    assert sherwani.id in measures.orphans
    assert measures.rescues[sherwani.id].code == "rescue.occasions"


def test_a_missing_partner_slot_is_named() -> None:
    shirt = make("casual_shirt", "white")

    measures = measure(wardrobe(shirt), context(), [OCCASIONS["college"]], ["mild"], FAMILIES)

    assert measures.rescues[shirt.id].text in {
        "There's no bottom in your wardrobe yet.",
        "There's no footwear in your wardrobe yet.",
    }


def test_coverage_follows_the_seasons_items_are_marked_for() -> None:
    summer_only = [
        make("tshirt", "white", seasons=frozenset({"summer"})),
        make("shorts", "navy", seasons=frozenset({"summer"})),
        make("sandals", "brown", seasons=frozenset({"summer"})),
    ]

    measures = measure(
        wardrobe(*summer_only), context("home"), [OCCASIONS["home"]], SEASONS, FAMILIES
    )

    assert measures.coverage[("home", "summer")] == 1
    assert measures.coverage[("home", "winter")] == 0


def test_the_whole_wardrobe_counts_but_retired_items_do_not() -> None:
    items = basics()
    in_wash = make("casual_shirt", "grey", status="laundry", wears_since_wash=1)
    retired = make("casual_shirt", "olive", status="retired")

    measures = measure(
        wardrobe(*items, in_wash, retired), context(), [OCCASIONS["college"]], ["mild"], FAMILIES
    )

    assert measures.versatility[in_wash.id] > 0
    assert retired.id not in measures.versatility


def test_the_worn_style_weighs_pieces_by_how_often_they_were_worn() -> None:
    navy_shirt = make("casual_shirt", "navy", formality=3)
    white_tee = make("tshirt", "white", formality=2)
    watch = make("watch", "silver")

    style = worn_style(
        [(navy_shirt, 3), (white_tee, 1), (watch, 10)], [STYLES["minimal"]], SLOT_KINDS
    )

    # The watch isn't a core piece; 4 core wears: 3 navy at formality 3, 1 white at 2.
    assert style.wears == 4
    assert style.palette == (("navy", 0.75), ("white", 0.25))
    assert dict(style.formality) == {1: 0.0, 2: 0.25, 3: 0.75, 4: 0.0, 5: 0.0}
    assert style.styles == (("minimal", 1.0),)


def test_no_wears_means_no_worn_style() -> None:
    style = worn_style([(make("tshirt", "white"), 0)], [STYLES["minimal"]], SLOT_KINDS)

    assert style.wears == 0
    assert style.palette == ()


def test_a_150_item_wardrobe_measures_in_a_few_seconds() -> None:
    occasions = [OCCASIONS[o] for o in ("college", "work", "casual_outing", "date")]
    started = time.perf_counter()

    measures = measure(wardrobe(*big_wardrobe()), context(), occasions, SEASONS, FAMILIES)

    elapsed = time.perf_counter() - started
    assert len(measures.coverage) == 16
    assert elapsed < 5.0, f"took {elapsed:.2f} s"


@pytest.mark.parametrize("colour", ["red", "white", "navy"])
def test_the_rescue_colour_is_a_contrasting_neutral(colour: str) -> None:
    clash = make("casual_shirt", colour, pattern="graphic")
    other = make("chinos", "yellow", pattern="check")
    shoes = make("sneakers", "purple", pattern="graphic")

    measures = measure(
        wardrobe(clash, other, shoes), context(), [OCCASIONS["college"]], ["mild"], FAMILIES
    )

    assert clash.id in measures.orphans
    rescue = measures.rescues[clash.id]
    assert rescue.code in ("rescue.slot", "rescue.partners")
    assert any(name in rescue.text for name in ("white", "black", "cream", "grey", "charcoal"))
    assert colour not in rescue.text.split("plain ")[1]
