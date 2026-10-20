"""Pair scores, one rule at a time (docs/ENGINE.md, section 5)."""

import pytest
from engine_support import make

from app.engine.config import DEFAULT
from app.engine.pairs import colour, fabric, formality, pair_score, pattern, style, with_preference


@pytest.mark.parametrize(
    ("first", "second", "case", "score"),
    [
        # One or both neutral: contrast decides.
        ("white", "navy", "neutral_contrast", 0.95),
        ("black", "charcoal", "neutral_similar", 0.85),
        ("beige", "maroon", "neutral_contrast", 0.95),
        # Beige and red are 0.245 apart in lightness, just under the 0.25 line.
        ("beige", "red", "neutral_similar", 0.85),
        # Both colours: the hue gap decides.
        ("light_blue", "blue", "tonal", 0.80),
        ("red", "maroon", "near_miss", 0.55),
        ("red", "rust", "analogous", 0.75),
        ("red", "yellow", "awkward", 0.35),
        ("blue", "green", "split", 0.50),
        ("olive", "purple", "complement_muted", 0.70),
        ("blue", "orange", "complement_saturated", 0.45),
        # Multicolour has no single hue.
        ("multi", "white", "multi_neutral", 0.75),
        ("multi", "red", "multi_colour", 0.45),
    ],
)
def test_colour_follows_the_table(first: str, second: str, case: str, score: float) -> None:
    a, b = make("casual_shirt", first), make("chinos", second)

    assert colour(a, b, DEFAULT) == (score, case)
    assert colour(b, a, DEFAULT) == (score, case)


def test_a_measured_grey_counts_as_neutral_even_in_a_colourful_family() -> None:
    # Chroma near zero is neutral whatever family the person picked.
    greyish = make("casual_shirt", "blue", color_hex="#7F8081")

    assert colour(greyish, make("chinos", "red"), DEFAULT)[1].startswith("neutral")


@pytest.mark.parametrize(
    ("steps", "score", "rejected"),
    [(0, 1.0, False), (1, 0.8, False), (2, 0.4, False), (3, 0.0, True), (4, 0.0, True)],
)
def test_formality_by_steps_apart(steps: int, score: float, rejected: bool) -> None:
    a = make("casual_shirt", formality=1)
    b = make("chinos", formality=1 + steps)

    assert formality(a, b, DEFAULT) == (score, rejected)


@pytest.mark.parametrize(
    ("first", "second", "score"),
    [
        ("solid", "solid", 0.9),
        ("solid", "stripe", 1.0),
        ("graphic", "solid", 1.0),
        ("stripe", "check", 0.5),
        ("check", "check", 0.25),
        ("graphic", "stripe", 0.2),
        ("graphic", "graphic", 0.2),
        # Texture reads as plain.
        ("texture", "solid", 0.9),
        ("texture", "print", 1.0),
    ],
)
def test_pattern_pairs(first: str, second: str, score: float) -> None:
    a = make("casual_shirt", pattern=first)
    b = make("chinos", pattern=second)

    assert pattern(a, b, DEFAULT)[0] == score
    assert pattern(b, a, DEFAULT)[0] == score


def test_linen_with_heavy_wool_clashes() -> None:
    linen = make("casual_shirt", fabric="linen")
    heavy = make("coat", fabric="wool")
    light = make("cardigan", fabric="wool", warmth=2)

    assert fabric(linen, heavy, DEFAULT) == (0.3, "clash")
    assert fabric(linen, light, DEFAULT) == (0.8, None)


def test_technical_sportswear_clashes_with_suiting_and_silk() -> None:
    track = make("activewear_top", fabric="technical")

    assert fabric(track, make("formal_trousers", fabric="wool", warmth=2), DEFAULT)[1] == "clash"
    assert fabric(track, make("skirt", fabric="silk"), DEFAULT)[1] == "clash"
    assert fabric(track, make("joggers", fabric="technical"), DEFAULT) == (0.8, None)


def test_denim_on_denim_only_in_a_similar_shade() -> None:
    jacket = make("denim_jacket", "denim_blue", fabric="denim")
    same = make("jeans", "denim_blue", fabric="denim")
    dark = make("jeans", "navy", fabric="denim")

    assert fabric(jacket, same, DEFAULT) == (0.5, "denim_on_denim")
    assert fabric(jacket, dark, DEFAULT) == (0.8, None)


def test_items_with_no_season_in_common_score_half() -> None:
    summer = make("casual_shirt", seasons=frozenset({"summer"}))
    winter = make("chinos", seasons=frozenset({"winter"}))
    anytime = make("chinos")

    assert fabric(summer, winter, DEFAULT) == (0.4, "no_shared_season")
    assert fabric(summer, anytime, DEFAULT) == (0.8, None)


def test_style_is_the_overlap_of_tags() -> None:
    a = make("casual_shirt", style_tags=frozenset({"minimal", "italian"}))
    b = make("chinos", style_tags=frozenset({"italian"}))

    assert style(a, b, DEFAULT) == 0.5
    assert style(a, make("chinos"), DEFAULT) == 0.5
    assert style(b, make("chinos", style_tags=frozenset({"italian"})), DEFAULT) == 1.0


def test_pair_score_weights_the_components() -> None:
    shirt = make("casual_shirt", "white", formality=3)
    chinos = make("chinos", "navy", formality=3)

    score = pair_score(shirt, chinos, DEFAULT)

    expected = 0.35 * 0.95 + 0.30 * 1.0 + 0.15 * 0.9 + 0.10 * 0.8 + 0.10 * 0.5
    assert score.base == pytest.approx(expected)
    assert not score.rejected


def test_a_matching_set_always_goes_together() -> None:
    jacket = make("blazer", "red", set_id="suit", formality=5)
    trousers = make("joggers", "green", set_id="suit", formality=1)

    score = pair_score(jacket, trousers, DEFAULT)

    assert score.same_set
    assert not score.rejected
    assert with_preference(score, -0.2, DEFAULT) == 1.0


def test_a_learned_preference_moves_the_score_within_limits() -> None:
    score = pair_score(make("casual_shirt", "white"), make("chinos", "navy"), DEFAULT)

    assert with_preference(score, 0.1, DEFAULT) == pytest.approx(score.base + 0.1)
    assert with_preference(score, 5.0, DEFAULT) == pytest.approx(min(1.0, score.base + 0.2))
    assert with_preference(score, -5.0, DEFAULT) == pytest.approx(score.base - 0.2)
