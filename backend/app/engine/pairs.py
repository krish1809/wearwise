"""How well two items go together: P(a, b) from docs/ENGINE.md, section 5.

Each component is a small function from two items to a score between 0 and 1, plus a short
code naming the case it found, so reasons can be built from the same decision that set the
score. P depends only on the two items, so it can be cached per wardrobe version; the learned
preference for a pair is added on top by the caller.
"""

from dataclasses import dataclass

from app.engine.color import hue_distance, oklch
from app.engine.config import EngineConfig
from app.engine.types import EngineItem


@dataclass(frozen=True)
class Tone:
    """An item's colour as the rules see it."""

    lightness: float
    chroma: float
    hue: float
    neutral: bool
    # False for multicolour, which has no single hue.
    known: bool


@dataclass(frozen=True)
class PairScore:
    colour: float
    formality: float
    pattern: float
    fabric: float
    style: float
    # The weighted sum, before any learned preference; 1 for a matching set.
    base: float
    colour_case: str
    pattern_case: str
    # None when nothing about the fabrics or seasons stood out.
    fabric_case: str | None
    same_set: bool
    # Three or more steps apart in formality: never worn together.
    rejected: bool


def tone(item: EngineItem, config: EngineConfig) -> Tone:
    if item.color_hex is None:
        return Tone(0.5, 0.0, 0.0, neutral=False, known=False)
    lightness, chroma, hue = oklch(item.color_hex)
    neutral = item.color_neutrality >= config.neutral_neutrality or chroma < config.neutral_chroma
    return Tone(lightness, chroma, hue, neutral=neutral, known=True)


def colour(a: EngineItem, b: EngineItem, config: EngineConfig) -> tuple[float, str]:
    ta, tb = tone(a, config), tone(b, config)
    if not ta.known or not tb.known:
        other = tb if not ta.known else ta
        if other.known and other.neutral:
            return config.colour_multi_neutral, "multi_neutral"
        return config.colour_multi_colour, "multi_colour"
    contrast = abs(ta.lightness - tb.lightness)
    if ta.neutral or tb.neutral:
        if contrast >= config.neutral_contrast:
            return config.colour_neutral_contrast, "neutral_contrast"
        return config.colour_neutral_similar, "neutral_similar"
    gap = hue_distance(ta.hue, tb.hue)
    if gap < 15:
        if contrast >= config.tonal_contrast:
            return config.colour_tonal, "tonal"
        return config.colour_near_miss, "near_miss"
    if gap < 45:
        return config.colour_analogous, "analogous"
    if gap < 100:
        return config.colour_awkward, "awkward"
    if gap < 150:
        return config.colour_split, "split"
    if min(ta.chroma, tb.chroma) < config.muted_chroma:
        return config.colour_complement_muted, "complement_muted"
    return config.colour_complement_saturated, "complement_saturated"


def formality(a: EngineItem, b: EngineItem, config: EngineConfig) -> tuple[float, bool]:
    """The score, and whether the two are too far apart to wear together."""
    steps = abs(a.formality - b.formality)
    if steps >= config.formality_reject:
        return 0.0, True
    return config.formality_scores[min(steps, len(config.formality_scores) - 1)], False


def pattern(a: EngineItem, b: EngineItem, config: EngineConfig) -> tuple[float, str]:
    plain_a = a.pattern in config.plain_patterns
    plain_b = b.pattern in config.plain_patterns
    if plain_a and plain_b:
        return config.pattern_solid_solid, "solids"
    if plain_a or plain_b:
        return config.pattern_solid_patterned, "one_pattern"
    if "graphic" in (a.pattern, b.pattern):
        return config.pattern_graphic, "graphic_clash"
    if a.pattern == b.pattern:
        return config.pattern_same, "same_pattern"
    return config.pattern_different, "two_patterns"


def fabric(a: EngineItem, b: EngineItem, config: EngineConfig) -> tuple[float, str | None]:
    score, case = config.fabric_base, None
    if _clash(a, b, config) or _clash(b, a, config):
        score, case = config.fabric_clash, "clash"
    elif a.fabric == "denim" and b.fabric == "denim" and _same_shade(a, b, config):
        score, case = config.fabric_denim_on_denim, "denim_on_denim"
    if a.seasons and b.seasons and not a.seasons & b.seasons:
        score *= config.fabric_no_shared_season
        case = case or "no_shared_season"
    return score, case


def _clash(a: EngineItem, b: EngineItem, config: EngineConfig) -> bool:
    if a.fabric == "linen" and b.fabric == "wool" and b.warmth >= config.heavy_wool_warmth:
        return True
    if a.fabric == "technical" and b.fabric != "technical":
        return b.fabric in ("silk", "satin") or b.formality >= config.suiting_formality
    return False


def _same_shade(a: EngineItem, b: EngineItem, config: EngineConfig) -> bool:
    ta, tb = tone(a, config), tone(b, config)
    if not ta.known or not tb.known:
        return True
    return abs(ta.lightness - tb.lightness) < config.denim_same_shade


def style(a: EngineItem, b: EngineItem, config: EngineConfig) -> float:
    if not a.style_tags or not b.style_tags:
        return config.style_unknown
    return len(a.style_tags & b.style_tags) / len(a.style_tags | b.style_tags)


def pair_score(a: EngineItem, b: EngineItem, config: EngineConfig) -> PairScore:
    colour_score, colour_case = colour(a, b, config)
    formality_score, rejected = formality(a, b, config)
    pattern_score, pattern_case = pattern(a, b, config)
    fabric_score, fabric_case = fabric(a, b, config)
    style_score = style(a, b, config)
    same_set = a.set_id is not None and a.set_id == b.set_id
    base = (
        1.0
        if same_set
        else (
            config.colour_weight * colour_score
            + config.formality_weight * formality_score
            + config.pattern_weight * pattern_score
            + config.fabric_weight * fabric_score
            + config.style_weight * style_score
        )
    )
    return PairScore(
        colour=colour_score,
        formality=formality_score,
        pattern=pattern_score,
        fabric=fabric_score,
        style=style_score,
        base=base,
        colour_case=colour_case,
        pattern_case=pattern_case,
        fabric_case=fabric_case,
        same_set=same_set,
        rejected=rejected and not same_set,
    )


def pair_key(a: EngineItem, b: EngineItem) -> tuple[str, str]:
    return (a.id, b.id) if a.id < b.id else (b.id, a.id)


class PairScores:
    """Pair scores for one wardrobe, worked out once each. The cache is a plain dictionary
    the caller can keep between requests while the wardrobe is unchanged."""

    def __init__(
        self,
        config: EngineConfig,
        cache: dict[tuple[str, str], PairScore] | None = None,
    ) -> None:
        self.config = config
        self.cache = cache if cache is not None else {}

    def get(self, a: EngineItem, b: EngineItem) -> PairScore:
        key = pair_key(a, b)
        found = self.cache.get(key)
        if found is None:
            found = pair_score(a, b, self.config)
            self.cache[key] = found
        return found


def with_preference(score: PairScore, preference: float, config: EngineConfig) -> float:
    """P(a, b): the base score plus the learned preference, between 0 and 1."""
    if score.same_set:
        return 1.0
    limit = config.preference_limit
    return min(1.0, max(0.0, score.base + max(-limit, min(limit, preference))))
