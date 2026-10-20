"""Suggesting outfits end to end (docs/ENGINE.md, sections 3, 4, and 8)."""

import dataclasses
import time
from collections import Counter
from datetime import timedelta

from engine_support import STYLES, TODAY, context, make, wardrobe

from app.engine.config import DEFAULT, ENGINE_VERSION
from app.engine.generate import season_for, suggest
from app.engine.reasons import TEXTS
from app.engine.types import EngineItem, Preferences, Suggestions

COLOURS = ["white", "navy", "black", "grey", "beige", "olive", "light_blue", "maroon"]


def basics() -> list[EngineItem]:
    return [
        make("casual_shirt", "white", fabric="cotton"),
        make("tshirt", "navy", fabric="cotton"),
        make("chinos", "beige", fabric="cotton"),
        make("jeans", "denim_blue", fabric="denim"),
        make("sneakers", "white", fabric="canvas"),
        make("loafers", "brown", fabric="leather"),
    ]


def slots_of(result: Suggestions) -> list[list[str]]:
    return [[item.slot for item in outfit.items] for outfit in result.outfits]


def ids_of(result: Suggestions) -> set[str]:
    return {item.id for outfit in result.outfits for item in outfit.items}


def test_suggestions_are_whole_outfits_with_one_item_per_slot() -> None:
    result = suggest(wardrobe(*basics()), context())

    assert result.outfits
    assert result.engine_version == ENGINE_VERSION
    for outfit in result.outfits:
        slots = [item.slot for item in outfit.items]
        assert len(slots) == len(set(slots))
        assert {"top", "bottom", "footwear"} <= set(slots)
        assert 0 <= outfit.score <= 1


def test_the_first_suggestion_is_the_best_scoring_one() -> None:
    result = suggest(wardrobe(*basics()), context())

    assert result.outfits[0].score == max(outfit.score for outfit in result.outfits)


def test_unusable_items_are_never_suggested() -> None:
    laundry = make("casual_shirt", "black", status="laundry")
    due = make("polo", "grey", wears_before_wash=2, wears_since_wash=2)
    archived = make("tshirt", "olive", archived=True)
    theirs = make("casual_shirt", "white", owner_id="user-b")
    avoided = make("casual_shirt", "maroon")
    excluded = make("polo", "navy")
    off_season = make("sweater", "grey", seasons=frozenset({"winter"}))
    too_formal = make("formal_shoes", "black")  # 4 is two steps above college's 3? no: 4 < 5
    gym_only = make("track_pants", "black")  # 1 is two steps below college's 2? no: 1 > 0
    items = [*basics(), laundry, due, archived, theirs, avoided, excluded, off_season]

    result = suggest(
        wardrobe(*items, too_formal, gym_only),
        context(
            exclude_ids=frozenset({excluded.id}),
            preferences=Preferences(avoided_colors=frozenset({"maroon"})),
            season="summer",
        ),
    )

    used = ids_of(result)
    for item in (laundry, due, archived, theirs, avoided, excluded, off_season):
        assert item.id not in used


def test_items_two_steps_outside_the_occasion_are_left_out() -> None:
    sherwani = make("sherwani", "cream", formality=5)  # college is 2 to 3
    slides = make("slides", "black", formality=1)

    result = suggest(wardrobe(*basics(), sherwani), context())
    assert sherwani.id not in ids_of(result)

    formal = suggest(wardrobe(*basics(), slides), context("interview"))
    assert slides.id not in ids_of(formal)


def test_a_dress_makes_a_one_piece_outfit() -> None:
    dress = make("dress", "red")
    flats = make("flats", "beige")

    result = suggest(wardrobe(dress, flats), context("date"))

    assert [outfit.template_id for outfit in result.outfits] == ["one_piece"]
    assert slots_of(result) == [["one_piece", "footwear"]]


def test_a_saree_needs_its_blouse_and_the_blouse_is_not_a_top() -> None:
    saree = make("saree", "maroon")
    blouse = make("saree_blouse", "gold")
    juttis = make("juttis", "gold")
    skirt = make("skirt", "cream", formality=4)

    result = suggest(wardrobe(saree, blouse, juttis, skirt), context("festive"))

    assert {outfit.template_id for outfit in result.outfits} == {"saree"}
    assert all(skirt.id not in outfit.core_ids for outfit in result.outfits)


def test_what_goes_with_this_keeps_the_item_in_every_outfit() -> None:
    items = basics()
    shirt = items[0]

    result = suggest(wardrobe(*items), context(anchor_ids=(shirt.id,)))

    assert result.outfits
    assert all(shirt.id in outfit.core_ids for outfit in result.outfits)


def test_an_anchor_sets_the_level_when_no_occasion_is_given() -> None:
    items = basics()
    result = suggest(wardrobe(*items), context(None, anchor_ids=(items[2].id,)))

    assert result.outfits
    assert all(items[2].id in outfit.core_ids for outfit in result.outfits)


def test_completing_an_outfit_keeps_every_chosen_piece() -> None:
    items = basics()
    shirt, chinos = items[0], items[2]

    result = suggest(wardrobe(*items), context(anchor_ids=(shirt.id, chinos.id)))

    for outfit in result.outfits:
        assert {shirt.id, chinos.id} <= set(outfit.core_ids)
        assert "footwear" in [item.slot for item in outfit.items]


def test_an_anchored_watch_comes_with_every_outfit() -> None:
    watch = make("watch", "silver", fabric="other")

    result = suggest(wardrobe(*basics(), watch), context(anchor_ids=(watch.id,)))

    assert result.outfits
    assert all(watch in outfit.items for outfit in result.outfits)


def test_an_anchor_in_the_laundry_says_so() -> None:
    shirt = make("casual_shirt", "white", status="laundry")

    result = suggest(wardrobe(shirt, *basics()), context(anchor_ids=(shirt.id,)))

    assert result.outfits == ()
    assert [m.code for m in result.missing] == ["missing.anchor_unavailable"]


def test_an_anchor_due_a_wash_says_so() -> None:
    shirt = make("casual_shirt", "white", wears_before_wash=1, wears_since_wash=1)

    result = suggest(wardrobe(shirt, *basics()), context(anchor_ids=(shirt.id,)))

    assert result.outfits == ()
    assert [m.text for m in result.missing] == ["The white casual shirt should be washed first."]


def test_anchors_that_cannot_share_an_outfit_say_so() -> None:
    dress = make("dress", "black")
    items = basics()

    result = suggest(wardrobe(dress, *items), context(anchor_ids=(dress.id, items[3].id)))

    assert result.outfits == ()
    assert [m.code for m in result.missing] == ["missing.anchors"]


def test_a_belt_that_goes_with_the_outfit_is_added() -> None:
    belt = make("belt", "brown", fabric="leather")

    result = suggest(wardrobe(*basics(), belt), context())

    assert any(belt in outfit.items for outfit in result.outfits)


def test_an_accessory_that_goes_badly_is_left_off() -> None:
    # A loud graphic cap at the casual end clashes with smart pieces in pattern and colour.
    cap = make("cap", "yellow", pattern="graphic", formality=1)
    smart = [
        make("formal_shirt", "red", pattern="check", formality=4),
        make("formal_trousers", "purple", pattern="stripe", formality=4),
        make("formal_shoes", "black", formality=4),
    ]

    result = suggest(wardrobe(*smart, cap), context("work"))

    assert result.outfits
    assert all(cap not in outfit.items for outfit in result.outfits)


def test_a_fragrance_is_chosen_by_season() -> None:
    summer = make("perfume", "multi", seasons=frozenset({"summer"}))
    winter = make("perfume", "multi", seasons=frozenset({"winter"}))

    result = suggest(wardrobe(*basics(), summer, winter), context(season="summer"))

    used = ids_of(result)
    assert summer.id in used
    assert winter.id not in used


def test_results_differ_and_no_piece_takes_over() -> None:
    tops = [make("tshirt", colour, fabric="cotton") for colour in COLOURS]
    bottoms = [make("chinos", c) for c in ("beige", "navy", "black")]
    shoes = [make("sneakers", c) for c in ("white", "black", "brown")]

    result = suggest(wardrobe(*tops, *bottoms, *shoes), context(count=10))

    assert len(result.outfits) == 10
    assert len({outfit.core_ids for outfit in result.outfits}) == 10
    uses = Counter(item_id for outfit in result.outfits for item_id in outfit.core_ids)
    assert max(uses.values()) <= 5


def test_a_tiny_wardrobe_returns_its_one_outfit_and_says_so() -> None:
    result = suggest(
        wardrobe(make("tshirt", "white"), make("jeans", "navy"), make("sneakers", "white")),
        context(),
    )

    assert len(result.outfits) == 1
    assert result.note == TEXTS["note.only_one"]


def test_fewer_outfits_than_asked_for_get_a_note() -> None:
    result = suggest(wardrobe(*basics()), context(count=10))

    assert 1 < len(result.outfits) < 10
    assert (
        result.note == f"Only {len(result.outfits)} different outfits work with what's available."
    )


def test_no_footwear_says_which_slot_is_missing() -> None:
    items = [item for item in basics() if item.slot != "footwear"]

    result = suggest(wardrobe(*items), context())

    assert result.outfits == ()
    assert [(m.slot, m.code) for m in result.missing] == [("footwear", "missing.none_owned")]
    assert result.missing[0].text == "There's no footwear in your wardrobe yet."


def test_footwear_in_the_laundry_says_so() -> None:
    items = [item for item in basics() if item.slot != "footwear"]
    dirty = make("sneakers", "white", status="laundry")

    result = suggest(wardrobe(*items, dirty), context())

    assert [m.code for m in result.missing] == ["missing.unavailable"]


def test_nothing_dressy_enough_offers_a_flagged_compromise() -> None:
    # An interview wants 4 to 5. A polo and chinos are a step short, still worn together.
    items = [make("polo", "navy"), make("chinos", "beige"), make("loafers", "brown")]
    casual_shoes = [make("polo", "white", formality=2), make("chinos", "grey")]
    sneakers = make("sneakers", "white", formality=2)

    result = suggest(wardrobe(*items[:2], *casual_shoes, sneakers), context("interview"))

    assert result.compromise
    assert result.outfits
    assert all(outfit.compromise for outfit in result.outfits)
    assert [m.code for m in result.missing] == ["missing.too_casual"]
    assert "interview" in (result.note or "").lower()


def test_an_empty_wardrobe_does_not_crash() -> None:
    result = suggest(wardrobe(), context())

    assert result.outfits == ()
    assert result.missing[0].code == "missing.none_owned"


def test_every_outfit_explains_itself() -> None:
    result = suggest(wardrobe(*basics()), context(style=STYLES["minimal"]))

    for outfit in result.outfits:
        assert outfit.reasons
        assert all(reason.code in TEXTS for reason in outfit.reasons)
        kinds = [reason.kind for reason in outfit.reasons]
        assert kinds == sorted(kinds, key=lambda kind: kind != "positive")
        assert kinds.count("positive") <= 3
        assert kinds.count("caution") <= 2


def test_a_matching_set_is_given_as_the_reason() -> None:
    jacket = make("blazer", "navy", set_id="suit")
    trousers = make("formal_trousers", "navy", set_id="suit")
    shirt = make("formal_shirt", "white")
    shoes = make("formal_shoes", "black")

    # In winter, so the jacket's warmth is welcome.
    result = suggest(wardrobe(jacket, trousers, shirt, shoes), context("work", season="winter"))

    best = result.outfits[0]
    assert jacket in best.items
    assert best.reasons[0].code == "set.match"


def test_the_same_request_gives_the_same_answer() -> None:
    items = basics()
    first = suggest(wardrobe(*items), context())
    second = suggest(wardrobe(*reversed(items)), context())

    assert first == second


def test_a_pair_cache_is_filled_and_reused() -> None:
    cache: dict[tuple[str, str], object] = {}
    items = basics()

    first = suggest(wardrobe(*items), context(), pair_cache=cache)  # type: ignore[arg-type]
    filled = len(cache)
    again = suggest(wardrobe(*items), context(), pair_cache=cache)  # type: ignore[arg-type]

    assert filled > 0
    assert len(cache) == filled
    assert first == again


def test_recently_worn_pieces_drop_down_the_list() -> None:
    items = basics()
    shirt = items[0]
    worn = [
        make("casual_shirt", "white", fabric="cotton", id=shirt.id, last_worn_on=TODAY),
        *items[1:],
    ]

    fresh = suggest(wardrobe(*items), context())
    after = suggest(wardrobe(*worn), context())

    assert shirt.id in fresh.outfits[0].core_ids
    assert shirt.id not in after.outfits[0].core_ids


def test_the_season_follows_the_indian_calendar() -> None:
    assert season_for(TODAY) == "mild"
    assert season_for(TODAY.replace(month=7)) == "monsoon"
    assert season_for(TODAY.replace(month=5)) == "summer"
    assert season_for(TODAY.replace(month=1)) == "winter"


def big_wardrobe() -> list[EngineItem]:
    """150 items: enough combinations to need the beam search."""
    items: list[EngineItem] = []
    plans = [
        ("casual_shirt", 25),
        ("tshirt", 20),
        ("polo", 5),
        ("chinos", 20),
        ("jeans", 10),
        ("casual_trousers", 5),
        ("sneakers", 10),
        ("loafers", 9),
        ("boots", 4),
        ("overshirt", 6),
        ("cardigan", 5),
        ("casual_jacket", 4),
        ("belt", 4),
        ("watch", 3),
        ("sunglasses", 3),
        ("sling_bag", 3),
        ("socks", 10),
        ("perfume", 2),
        ("necklace_chain", 2),
    ]
    for category, how_many in plans:
        for index in range(how_many):
            colour = COLOURS[(index * 3 + len(items)) % len(COLOURS)]
            pattern = ("solid", "stripe", "check", "solid", "texture")[index % 5]
            worn = TODAY - timedelta(days=index * 2) if index % 3 else None
            items.append(make(category, colour, pattern=pattern, last_worn_on=worn))
    assert len(items) == 150
    return items


def test_a_150_item_wardrobe_takes_under_a_second() -> None:
    items = big_wardrobe()
    started = time.perf_counter()

    result = suggest(wardrobe(*items), context(count=10))

    elapsed = time.perf_counter() - started
    assert len(result.outfits) == 10
    assert elapsed < 1.0, f"took {elapsed:.2f} s"


def test_the_beam_search_is_used_and_finds_good_outfits() -> None:
    items = big_wardrobe()
    tops = sum(1 for item in items if item.slot == "top")
    bottoms = sum(1 for item in items if item.slot == "bottom")
    shoes = sum(1 for item in items if item.slot == "footwear")
    layers = sum(1 for item in items if item.slot == "layer") + 1
    assert tops * bottoms * shoes * layers > DEFAULT.enumerate_limit

    result = suggest(wardrobe(*items), context(count=5))

    assert all(outfit.score > 0.6 for outfit in result.outfits)


def test_the_beam_search_finds_what_trying_everything_finds() -> None:
    # 18 tops, 14 bottoms, 9 shoes, and 8 layers (or none): 20,412 combinations.
    patterns = ("solid", "stripe", "check", "solid", "texture")
    items = [
        make(category, COLOURS[(n * 5 + offset) % 8], pattern=patterns[n % 5])
        for category, count, offset in (
            ("casual_shirt", 10, 0),
            ("tshirt", 8, 1),
            ("chinos", 8, 2),
            ("jeans", 6, 3),
            ("sneakers", 5, 4),
            ("loafers", 4, 5),
            ("overshirt", 8, 6),
        )
        for n in range(count)
    ]
    everything = dataclasses.replace(DEFAULT, enumerate_limit=10**9)
    beam_only = dataclasses.replace(DEFAULT, enumerate_limit=0)

    full = suggest(wardrobe(*items), context(), config=everything)
    beam = suggest(wardrobe(*items), context(), config=beam_only)

    assert [o.core_ids for o in beam.outfits] == [o.core_ids for o in full.outfits]
