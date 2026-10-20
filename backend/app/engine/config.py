"""Every number the outfit engine uses, in one place (docs/ENGINE.md).

These are the starting values from the engine doc. Tune them only against the golden set, one
change at a time, and give every change a new ENGINE_VERSION so feedback can be compared
between versions.
"""

from dataclasses import dataclass, field

ENGINE_VERSION = "1.0"


def _pair_weights() -> dict[frozenset[str], float]:
    # How much each pair of slots matters to the outfit's base score (section 6).
    return {
        frozenset({"top", "bottom"}): 1.0,
        frozenset({"top", "layer"}): 0.9,
        frozenset({"bottom", "footwear"}): 0.8,
        frozenset({"belt", "footwear"}): 0.7,
        frozenset({"layer", "bottom"}): 0.6,
        frozenset({"top", "footwear"}): 0.5,
        # A one-piece plays the top and the bottom at once; a saree's blouse sits with it.
        frozenset({"one_piece", "top"}): 1.0,
        frozenset({"one_piece", "layer"}): 0.9,
        frozenset({"one_piece", "footwear"}): 0.8,
    }


def _warmth_bands() -> dict[str, tuple[int, int]]:
    # Target warmth of the upper body for each season, standing in for the feels-like
    # temperature until weather arrives (M6). The doc's bands are 1 above 32 °C, 1 to 2 at
    # 25 to 32 °C, 2 to 4 at 18 to 25 °C, and 4 to 6 at 10 to 18 °C. Indian seasons straddle
    # them: summer is the first, monsoon the second, mild (a shirt alone or a light layer)
    # spans the second and third, and winter the third and fourth.
    return {"summer": (0, 1), "monsoon": (1, 2), "mild": (1, 3), "winter": (3, 6)}


def _season_by_month() -> dict[int, str]:
    # The season when a request doesn't name one, on the Indian calendar the app starts with.
    return {
        1: "winter",
        2: "winter",
        3: "summer",
        4: "summer",
        5: "summer",
        6: "monsoon",
        7: "monsoon",
        8: "monsoon",
        9: "monsoon",
        10: "mild",
        11: "mild",
        12: "winter",
    }


@dataclass(frozen=True)
class EngineConfig:
    # Pair score (section 5): the weight of each component.
    colour_weight: float = 0.35
    formality_weight: float = 0.30
    pattern_weight: float = 0.15
    fabric_weight: float = 0.10
    style_weight: float = 0.10
    # The learned adjustment for a pair stays within plus or minus this.
    preference_limit: float = 0.2

    # Colour. OKLCH lightness runs 0 to 1; chroma is about 0 to 0.37.
    neutral_neutrality: float = 0.8
    neutral_chroma: float = 0.03
    muted_chroma: float = 0.10
    neutral_contrast: float = 0.25
    tonal_contrast: float = 0.20
    colour_neutral_contrast: float = 0.95
    colour_neutral_similar: float = 0.85
    colour_tonal: float = 0.80
    colour_near_miss: float = 0.55
    colour_analogous: float = 0.75
    colour_awkward: float = 0.35
    colour_split: float = 0.50
    colour_complement_muted: float = 0.70
    colour_complement_saturated: float = 0.45
    # Multicolour has no single hue: it sits on a neutral well and is a gamble with a colour.
    colour_multi_neutral: float = 0.75
    colour_multi_colour: float = 0.45

    # Formality: score by difference in steps; this many steps apart can't be worn together.
    formality_scores: tuple[float, ...] = (1.0, 0.8, 0.4)
    formality_reject: int = 3

    # Pattern. Texture reads as plain from a few steps away, so it pairs like a solid.
    plain_patterns: frozenset[str] = frozenset({"solid", "texture"})
    pattern_solid_solid: float = 0.9
    pattern_solid_patterned: float = 1.0
    pattern_different: float = 0.5
    pattern_same: float = 0.25
    pattern_graphic: float = 0.2

    # Fabric and season.
    fabric_base: float = 0.8
    fabric_clash: float = 0.3
    fabric_denim_on_denim: float = 0.5
    fabric_no_shared_season: float = 0.5
    # Wool this warm or warmer counts as heavy.
    heavy_wool_warmth: int = 3
    # Formality this high or higher counts as suiting.
    suiting_formality: int = 4
    # Denim pieces closer than this in lightness read as the same shade.
    denim_same_shade: float = 0.12

    # Style: overlap of tags, or this when either item has none.
    style_unknown: float = 0.5

    # Outfit base score (section 6).
    pair_weights: dict[frozenset[str], float] = field(default_factory=_pair_weights)
    core_pair_default: float = 0.5
    accessory_pair_weight: float = 0.3
    base_mean_weight: float = 0.7
    base_worst_weight: float = 0.3
    # Hues closer than this belong to one colour group.
    hue_group_width: float = 20.0
    too_many_hues: int = 2
    too_many_hues_penalty: float = 0.15
    too_many_patterns_penalty: float = 0.10
    belt_shoes_match_bonus: float = 0.05
    belt_shoes_clash_penalty: float = 0.05
    # Leathers this close in lightness and hue read as a match even across colour families.
    belt_shoes_close_lightness: float = 0.15
    belt_shoes_close_hue: float = 30.0

    # Context score (section 7).
    base_weight: float = 0.50
    occasion_weight: float = 0.15
    weather_weight: float = 0.10
    rotation_weight: float = 0.10
    preference_weight: float = 0.10
    style_context_weight: float = 0.05
    occasion_step_penalty: float = 0.35
    occasion_group_bonus: float = 0.1
    warmth_bands: dict[str, tuple[int, int]] = field(default_factory=_warmth_bands)
    weather_step_penalty: float = 0.3
    hot_season: str = "summer"
    breathable_fabrics: frozenset[str] = frozenset({"linen", "cotton"})
    breathable_bonus: float = 0.05
    hot_fabrics: frozenset[str] = frozenset({"polyester"})
    hot_fabric_penalty: float = 0.1
    hot_layer_penalty: float = 0.3
    rain_season: str = "monsoon"
    rain_shy_fabrics: frozenset[str] = frozenset({"suede", "canvas"})
    rain_penalty: float = 0.15
    # Bottoms this light or lighter show every splash.
    light_bottom_lightness: float = 0.85
    rotation_days: int = 14
    repeat_outfit_days: int = 7
    preferred_colour_bonus: float = 0.1
    preferred_fit_bonus: float = 0.05
    # An item matches a style when at least this share of the style's signals fit it.
    style_match_share: float = 0.5
    style_signal_formality_steps: int = 1
    no_style: float = 0.5
    season_by_month: dict[int, str] = field(default_factory=_season_by_month)

    # Generation, accessories, diversity (section 8). The doc starts enumerating up to 50,000
    # combinations; above 5,000 the beam search found the same top ten in every trial at a
    # tenth of the time, which matters on a small server (D35).
    enumerate_limit: int = 5_000
    beam_width: int = 200
    accessorise_top: int = 50
    accessory_min: float = 0.7
    # Hard filter: an item this many steps outside the occasion's range is left out.
    occasion_filter_steps: int = 2
    mmr_relevance: float = 0.7
    mmr_similarity: float = 0.3
    max_item_share: float = 0.5

    # Reasons: how many to show.
    max_positive_reasons: int = 3
    max_caution_reasons: int = 2

    # Learning from feedback (section 10).
    learning_rate: float = 0.3


DEFAULT = EngineConfig()
