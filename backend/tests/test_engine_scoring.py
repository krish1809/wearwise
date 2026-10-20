"""Outfit and context scores (docs/ENGINE.md, sections 6 and 7)."""

from datetime import timedelta
from typing import Any

import pytest
from engine_support import OCCASIONS, SLOT_KINDS, STYLES, TODAY, context, make

from app.engine.config import DEFAULT
from app.engine.pairs import PairScores
from app.engine.scoring import Range, Scorer
from app.engine.types import EngineItem, Preferences, Weather


def scorer(occasion: str | None = "college", **fields: Any) -> Scorer:
    ctx = context(occasion, **fields)
    found = OCCASIONS[occasion] if occasion else None
    level = Range(found.formality_min, found.formality_max, found) if found else Range(2, 3)
    return Scorer(ctx, level, PairScores(DEFAULT), SLOT_KINDS, DEFAULT)


def outfit(top: str = "white", bottom: str = "navy", shoes: str = "white") -> list[EngineItem]:
    return [
        make("casual_shirt", top, fabric="cotton"),
        make("chinos", bottom, fabric="cotton"),
        make("sneakers", shoes, fabric="canvas"),
    ]


def test_one_bad_pair_drags_the_whole_outfit_down() -> None:
    s = scorer()
    good = outfit()
    clash = [make("casual_shirt", "red"), make("chinos", "yellow"), good[2]]

    good_base = s.base(good)[0]
    clash_base = s.base(clash)[0]

    assert clash_base < good_base - 0.1


def test_the_top_and_bottom_pair_matters_more_than_top_and_shoes() -> None:
    s = scorer()
    red_top = make("casual_shirt", "red")
    yellow_bottom = [red_top, make("chinos", "yellow"), make("sneakers", "white")]
    yellow_shoes = [red_top, make("chinos", "white"), make("sneakers", "yellow")]

    assert s.base(yellow_bottom)[0] < s.base(yellow_shoes)[0]


def test_more_than_two_colour_groups_cost_a_penalty() -> None:
    s = scorer()
    three = [make("casual_shirt", "red"), make("chinos", "green"), make("sneakers", "blue")]
    near = [make("casual_shirt", "red"), make("chinos", "rust"), make("sneakers", "white")]

    assert s.base(three)[2] == 3
    # Red and rust are within one colour group.
    assert s.base(near)[2] == 1


def test_two_patterned_pieces_cost_a_penalty() -> None:
    s = scorer()
    plain = [make("casual_shirt", "white", pattern="stripe"), make("chinos", "navy")]
    busy = [
        make("casual_shirt", "white", pattern="stripe"),
        make("chinos", "navy", pattern="check"),
    ]

    assert s.base(plain)[3] == 1
    assert s.base(busy)[3] == 2


def test_matching_leather_belt_and_shoes_earn_a_bonus() -> None:
    s = scorer()
    core = [
        make("casual_shirt", "white"),
        make("chinos", "navy"),
        make("loafers", "brown", fabric="leather"),
    ]
    matching = make("belt", "brown", fabric="leather")
    clashing = make("belt", "black", fabric="leather")

    assert s.base(core, [matching])[4] == 1
    assert s.base(core, [clashing])[4] == -1
    assert s.base(core, [matching])[0] > s.base(core, [clashing])[0]


def test_occasion_is_full_inside_the_range_and_falls_outside_it() -> None:
    s = scorer("college")  # formality 2 to 3
    inside = [make("casual_shirt", formality=3), make("chinos", formality=2)]
    below = [make("tshirt", formality=1), make("joggers", formality=1)]

    assert s.occasion(inside) == 1.0
    assert s.occasion(below) == pytest.approx(1 - 0.35)


def test_an_occasion_that_prefers_ethnic_wear_rewards_it() -> None:
    s = scorer("festive")
    ethnic = [make("kurta", "maroon", formality=4), make("ethnic_bottom", "cream", formality=4)]
    western = [make("formal_shirt", "white"), make("formal_trousers", "navy")]

    assert s.occasion(ethnic) == pytest.approx(1.1)
    assert s.occasion(western) == pytest.approx(1.0)


def test_upper_body_warmth_is_compared_with_the_season() -> None:
    mild = scorer(season="mild")  # 1 to 3
    winter = scorer(season="winter")  # 3 to 6
    shirt = [make("casual_shirt", warmth=1), make("chinos")]
    layered = [*shirt, make("blazer", warmth=3)]

    assert mild.weather(shirt) == 1.0
    assert mild.weather(layered) == pytest.approx(1 - 0.3)
    assert winter.weather(shirt) == pytest.approx(1 - 0.3 * 2)
    assert winter.weather(layered) == 1.0


def test_summer_prefers_breathable_fabric_and_no_layer() -> None:
    s = scorer(season="summer")
    poly = [make("tshirt", fabric="polyester"), make("shorts", fabric="polyester")]
    layered = [make("tshirt", fabric="cotton"), make("shorts"), make("shrug", warmth=0)]

    assert s.weather(poly) == pytest.approx(1 - 0.2)
    # In the band, plus the cotton t-shirt, minus the layer.
    assert s.weather(layered) == pytest.approx(1 + 0.05 - 0.3)


def test_monsoon_is_hard_on_suede_and_light_bottoms() -> None:
    s = scorer(season="monsoon")
    risky = [
        make("casual_shirt"),
        make("chinos", "white"),
        make("loafers", "tan", fabric="suede"),
    ]
    safe = [make("casual_shirt"), make("chinos", "navy"), make("sneakers", fabric="leather")]

    assert [item.slot for item in s.rain_risks(risky)] == ["bottom", "footwear"]
    assert s.weather(risky) == pytest.approx(1 - 2 * 0.15)
    assert s.weather(safe) == 1.0


def test_rotation_favours_pieces_not_worn_lately() -> None:
    s = scorer()
    fresh = [make("casual_shirt"), make("chinos")]
    half = [
        make("casual_shirt", last_worn_on=TODAY - timedelta(days=7)),
        make("chinos", last_worn_on=TODAY - timedelta(days=7)),
    ]

    assert s.rotation(fresh) == (1.0, False)
    assert s.rotation(half) == (0.5, False)


def test_the_same_outfit_worn_this_week_gets_no_rotation_credit() -> None:
    core = [make("casual_shirt"), make("chinos")]
    worn = (TODAY - timedelta(days=3), frozenset(item.id for item in core))
    s = scorer(recent_outfits=(worn,))

    assert s.rotation(core) == (0.0, True)


def test_feedback_moves_the_preference_score() -> None:
    shirt, chinos = make("casual_shirt", "white"), make("chinos", "navy")
    liked = Preferences(
        family_category_counts={("white", "casual_shirt"): (3, 0), ("navy", "chinos"): (3, 0)}
    )
    disliked_item = Preferences(item_counts={shirt.id: (0, 2)})

    neutral = scorer().preference([shirt, chinos])
    up = scorer(preferences=liked).preference([shirt, chinos])
    down = scorer(preferences=disliked_item).preference([shirt, chinos])

    assert neutral == pytest.approx(0.5)
    assert up > neutral
    assert down < neutral
    # An item dislike lowers that item only.
    assert scorer(preferences=disliked_item).item_preference(chinos) == pytest.approx(0.5)


def test_preferred_colours_add_a_small_bonus() -> None:
    core = [make("casual_shirt", "olive"), make("chinos", "beige")]
    s = scorer(preferences=Preferences(preferred_colors=frozenset({"olive"})))

    assert s.preference(core) == pytest.approx(0.5 + 0.1 * 0.5)


def test_style_counts_pieces_that_match_the_style() -> None:
    minimal = scorer(style=STYLES["minimal"])
    pieces = [
        make("tshirt", "white", fabric="cotton", fit="regular"),
        make("chinos", "black", fabric="cotton", fit="regular"),
        make("sneakers", "red", pattern="graphic", fabric="canvas", formality=1),
    ]

    assert minimal.style(pieces) == pytest.approx(2 / 3)
    assert scorer().style(pieces) == 0.5


def test_a_style_tag_on_the_item_is_a_match() -> None:
    s = scorer(style=STYLES["streetwear"])

    assert s.matches_style(make("formal_shirt", "white", style_tags=frozenset({"streetwear"})))


def test_the_total_stays_between_zero_and_one() -> None:
    s = scorer()
    breakdown = s.score(outfit())

    assert 0 <= breakdown.score <= 1
    expected = (
        0.5 * breakdown.components.base
        + 0.15 * breakdown.components.occasion
        + 0.10 * breakdown.components.weather
        + 0.10 * breakdown.components.rotation
        + 0.10 * breakdown.components.preference
        + 0.05 * breakdown.components.style
    )
    assert breakdown.score == pytest.approx(min(1.0, expected))


@pytest.mark.parametrize(
    ("feels_like", "band"),
    [
        (36.0, (0, 1)),
        (32.0, (0, 1)),
        (28.0, (1, 2)),
        (20.0, (2, 4)),
        (12.0, (4, 6)),
        (4.0, (6, 20)),
    ],
)
def test_a_forecast_sets_the_warmth_band_by_temperature(
    feels_like: float, band: tuple[int, int]
) -> None:
    s = scorer(weather=Weather(feels_like=feels_like, rain_chance=0))

    assert s.climate.band == band


def test_a_forecast_replaces_the_season() -> None:
    # Winter by the calendar, but a warm day: dress for the day.
    s = scorer(season="winter", weather=Weather(feels_like=28.0, rain_chance=0))
    shirt = [make("casual_shirt", warmth=1), make("chinos")]

    assert s.weather(shirt) == 1.0


def test_rain_comes_from_the_forecast_when_there_is_one() -> None:
    risky = [make("casual_shirt"), make("chinos", "navy"), make("loafers", fabric="suede")]
    dry_monsoon = scorer(season="monsoon", weather=Weather(feels_like=27.0, rain_chance=20))
    wet = scorer(season="mild", weather=Weather(feels_like=27.0, rain_chance=70))

    assert dry_monsoon.weather(risky) == 1.0
    assert wet.weather(risky) == pytest.approx(1 - 0.15)


def test_the_cold_is_hard_on_bare_legs_and_open_toes() -> None:
    s = scorer("home", weather=Weather(feels_like=6.0, rain_chance=0))
    bare = [
        make("hoodie", warmth=6),
        make("shorts", traits=frozenset({"bare_legs"})),
        make("sandals", traits=frozenset({"open_toe"})),
    ]
    covered = [make("hoodie", warmth=6), make("joggers"), make("sneakers")]

    assert [item.slot for item in s.cold_risks(bare)] == ["bottom", "footwear"]
    assert s.weather(bare) == pytest.approx(1 - 2 * 0.2)
    assert s.weather(covered) == 1.0
