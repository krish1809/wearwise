"""Scoring a whole outfit: the base score from its pairs, then the context score
(docs/ENGINE.md, sections 6 and 7).

The Scorer works out everything that depends on one item only (rotation, preference, style
match) once per request, so scoring thousands of combinations stays cheap.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.engine.color import hue_distance
from app.engine.config import EngineConfig
from app.engine.pairs import PairScore, PairScores, Tone, pair_key, tone, with_preference
from app.engine.types import Components, Context, EngineItem, Occasion, Style

# Slots whose warmth counts towards the upper body.
UPPER_SLOTS = ("top", "one_piece", "layer")
CLOTHING_SLOTS = ("top", "bottom", "one_piece")


@dataclass(frozen=True)
class Range:
    """The level of dress asked for: an occasion's range, or the anchors' own."""

    low: int
    high: int
    occasion: Occasion | None = None


@dataclass(frozen=True)
class PairView:
    a: EngineItem
    b: EngineItem
    weight: float
    score: PairScore
    # P(a, b) with the learned preference.
    value: float
    core: bool


@dataclass(frozen=True)
class Breakdown:
    """A scored outfit, with the details reasons are built from."""

    score: float
    components: Components
    pairs: tuple[PairView, ...]
    hue_groups: int
    patterned: int
    belt_shoes: int  # +1 matching leather, -1 clashing, 0 neither
    repeated: bool  # the same core outfit was worn in the last week


class Scorer:
    def __init__(
        self,
        context: Context,
        level: Range,
        pairs: PairScores,
        slot_kinds: Mapping[str, str],
        config: EngineConfig,
    ) -> None:
        self.context = context
        self.level = level
        self.pairs = pairs
        self.slot_kinds = slot_kinds
        self.config = config
        self.styles: tuple[Style, ...] = (
            (context.style,) if context.style else context.profile_styles
        )
        # Worked out once per request.
        self._weights: dict[tuple[str, str], float] = {}
        self._values: dict[tuple[str, str], tuple[PairScore, float]] = {}
        self._tones: dict[str, Tone] = {}
        self._rotation: dict[str, float] = {}
        self._preference: dict[str, float] = {}
        self._style: dict[str, bool] = {}
        self._recent = {
            core
            for worn_on, core in context.recent_outfits
            if 0 <= (context.today - worn_on).days < config.repeat_outfit_days
        }

    # Pairs and the base score (section 6).

    def pair_weight(self, a: EngineItem, b: EngineItem) -> float:
        key = (a.slot, b.slot)
        weight = self._weights.get(key)
        if weight is None:
            weight = self.config.pair_weights.get(frozenset(key))
            if weight is None:
                core = self._is_core_slot(a.slot) and self._is_core_slot(b.slot)
                weight = (
                    self.config.core_pair_default if core else self.config.accessory_pair_weight
                )
            self._weights[key] = weight
        return weight

    def pair_value(self, a: EngineItem, b: EngineItem) -> tuple[PairScore, float]:
        """The pair's scores, and P(a, b) with the learned preference."""
        key = pair_key(a, b)
        found = self._values.get(key)
        if found is None:
            score = self.pairs.get(a, b)
            preference = self.context.preferences.pair_prefs.get(key, 0.0)
            found = (score, with_preference(score, preference, self.config))
            self._values[key] = found
        return found

    def base(
        self, core: Sequence[EngineItem], extras: Sequence[EngineItem] = ()
    ) -> tuple[float, tuple[PairView, ...], int, int, int]:
        """B for the core pieces; extras (an anchored accessory, a belt) join the weighted
        mean, while the worst pair is taken over the core only. Also returns the pairs and
        the counts the adjustments used, for reasons."""
        views: list[PairView] = []
        value, hue_groups, patterned, belt_shoes = self._base(core, extras, views)
        return value, tuple(views), hue_groups, patterned, belt_shoes

    def _base(
        self,
        core: Sequence[EngineItem],
        extras: Sequence[EngineItem],
        views: list[PairView] | None,
    ) -> tuple[float, int, int, int]:
        weighted = weights = 0.0
        worst = 2.0
        count = len(core)
        for i in range(count):
            a = core[i]
            for j in range(i + 1, count):
                b = core[j]
                score, value = self.pair_value(a, b)
                weight = self.pair_weight(a, b)
                weighted += weight * value
                weights += weight
                worst = min(worst, value)
                if views is not None:
                    views.append(PairView(a, b, weight, score, value, core=True))
        for extra in extras:
            for item in core:
                score, value = self.pair_value(extra, item)
                weight = self.pair_weight(extra, item)
                weighted += weight * value
                weights += weight
                if views is not None:
                    views.append(PairView(extra, item, weight, score, value, core=False))
        if not weights:
            return 1.0, 0, 0, 0
        mean = weighted / weights
        if worst > 1:
            worst = mean
        config = self.config
        value = config.base_mean_weight * mean + config.base_worst_weight * worst
        hue_groups = self._hue_groups(core)
        if hue_groups > config.too_many_hues:
            value -= config.too_many_hues_penalty
        patterned = sum(1 for item in core if item.pattern not in config.plain_patterns)
        if patterned > 1:
            value -= config.too_many_patterns_penalty
        belt_shoes = self._belt_shoes(core, extras) if extras else 0
        if belt_shoes > 0:
            value += config.belt_shoes_match_bonus
        elif belt_shoes < 0:
            value -= config.belt_shoes_clash_penalty
        return _clamp(value), hue_groups, patterned, belt_shoes

    def tone(self, item: EngineItem) -> Tone:
        found = self._tones.get(item.id)
        if found is None:
            found = tone(item, self.config)
            self._tones[item.id] = found
        return found

    def _hue_groups(self, core: Sequence[EngineItem]) -> int:
        hues = sorted(
            tone_.hue
            for tone_ in (self.tone(item) for item in core)
            if tone_.known and not tone_.neutral
        )
        if not hues:
            return 0
        width = self.config.hue_group_width
        groups = 1
        start = hues[0]
        for hue in hues[1:]:
            if hue - start > width:
                groups += 1
                start = hue
        # Hues just either side of 0 degrees are one group.
        if groups > 1 and hues[0] + 360 - hues[-1] <= width:
            return groups - 1
        return groups

    def _belt_shoes(self, core: Sequence[EngineItem], extras: Sequence[EngineItem]) -> int:
        belt = next((item for item in extras if item.slot == "belt"), None)
        shoes = next((item for item in core if item.slot == "footwear"), None)
        if belt is None or shoes is None or belt.fabric != "leather" or shoes.fabric != "leather":
            return 0
        if belt.color_family == shoes.color_family:
            return 1
        tb, ts = self.tone(belt), self.tone(shoes)
        if not tb.known or not ts.known:
            return 0
        close = abs(tb.lightness - ts.lightness) <= self.config.belt_shoes_close_lightness
        if not tb.neutral and not ts.neutral:
            close = close and hue_distance(tb.hue, ts.hue) <= self.config.belt_shoes_close_hue
        return 0 if close else -1

    # Context (section 7).

    def occasion(self, core: Sequence[EngineItem]) -> float:
        mean = sum(item.formality for item in core) / len(core)
        if mean < self.level.low:
            distance = self.level.low - mean
        elif mean > self.level.high:
            distance = mean - self.level.high
        else:
            distance = 0.0
        value = max(0.0, 1 - self.config.occasion_step_penalty * distance)
        occasion = self.level.occasion
        if occasion and occasion.prefers_groups & {item.group_id for item in core}:
            value += self.config.occasion_group_bonus
        return value

    def weather(self, core: Sequence[EngineItem]) -> float:
        season = self.context.season
        band = self.config.warmth_bands.get(season) if season else None
        if band is None:
            return 1.0
        by_slot = {item.slot: item for item in core}
        upper = by_slot.get("one_piece") or by_slot.get("top")
        warmth = (upper.warmth if upper else 0) + (
            by_slot["layer"].warmth if "layer" in by_slot else 0
        )
        low, high = band
        distance = low - warmth if warmth < low else max(0, warmth - high)
        value = 1 - self.config.weather_step_penalty * distance
        if season == self.config.hot_season:
            for item in core:
                if item.slot in CLOTHING_SLOTS and item.fabric in self.config.breathable_fabrics:
                    value += self.config.breathable_bonus
                if item.fabric in self.config.hot_fabrics:
                    value -= self.config.hot_fabric_penalty
            if "layer" in by_slot:
                value -= self.config.hot_layer_penalty
        if season == self.config.rain_season:
            value -= self.config.rain_penalty * len(self.rain_risks(core))
        return _clamp(value)

    def rain_risks(self, core: Sequence[EngineItem]) -> list[EngineItem]:
        """Pieces the rain is hard on: suede or canvas shoes, and very light bottoms."""
        risky = []
        for item in core:
            if item.slot == "footwear" and item.fabric in self.config.rain_shy_fabrics:
                risky.append(item)
            elif item.slot == "bottom":
                tone_ = self.tone(item)
                if tone_.known and tone_.lightness >= self.config.light_bottom_lightness:
                    risky.append(item)
        return risky

    def item_rotation(self, item: EngineItem) -> float:
        found = self._rotation.get(item.id)
        if found is None:
            if item.last_worn_on is None:
                found = 1.0
            else:
                days = max(0, (self.context.today - item.last_worn_on).days)
                found = min(days, self.config.rotation_days) / self.config.rotation_days
            self._rotation[item.id] = found
        return found

    def rotation(self, core: Sequence[EngineItem]) -> tuple[float, bool]:
        """R, and whether this exact core outfit was worn in the last week."""
        if self._recent and frozenset(item.id for item in core) in self._recent:
            return 0.0, True
        return sum(self.item_rotation(item) for item in core) / len(core), False

    def item_preference(self, item: EngineItem) -> float:
        found = self._preference.get(item.id)
        if found is None:
            preferences = self.context.preferences
            likes, dislikes = preferences.family_category_counts.get(
                (item.color_family, item.category_id), (0, 0)
            )
            item_likes, item_dislikes = preferences.item_counts.get(item.id, (0, 0))
            found = (_like_rate(likes, dislikes) + _like_rate(item_likes, item_dislikes)) / 2
            self._preference[item.id] = found
        return found

    def preference(self, core: Sequence[EngineItem]) -> float:
        preferences = self.context.preferences
        value = sum(self.item_preference(item) for item in core) / len(core)
        if preferences.preferred_colors:
            share = sum(
                1 for item in core if item.color_family in preferences.preferred_colors
            ) / len(core)
            value += self.config.preferred_colour_bonus * share
        if preferences.fit_preference:
            share = sum(1 for item in core if item.fit == preferences.fit_preference) / len(core)
            value += self.config.preferred_fit_bonus * share
        return min(1.0, value)

    def matches_style(self, item: EngineItem) -> bool:
        found = self._style.get(item.id)
        if found is None:
            found = any(self.fits_style(item, style) for style in self.styles)
            self._style[item.id] = found
        return found

    def fits_style(self, item: EngineItem, style: Style) -> bool:
        if style.id in item.style_tags:
            return True
        checks = [
            item.color_family in style.colors,
            item.pattern in style.patterns,
            item.category_id in style.categories,
            abs(item.formality - style.formality_center)
            <= self.config.style_signal_formality_steps,
        ]
        if item.fabric:
            checks.append(item.fabric in style.fabrics)
        if item.fit:
            checks.append(item.fit in style.fits)
        return sum(checks) / len(checks) >= self.config.style_match_share

    def style(self, core: Sequence[EngineItem]) -> float:
        if not self.styles:
            return self.config.no_style
        return sum(1 for item in core if self.matches_style(item)) / len(core)

    # Everything together.

    def score(self, core: Sequence[EngineItem], extras: Sequence[EngineItem] = ()) -> Breakdown:
        """The score with everything reasons need."""
        views: list[PairView] = []
        base, hue_groups, patterned, belt_shoes = self._base(core, extras, views)
        rotation, repeated = self.rotation(core)
        components = Components(
            base=base,
            occasion=self.occasion(core),
            weather=self.weather(core),
            rotation=rotation,
            preference=self.preference(core),
            style=self.style(core),
        )
        return Breakdown(
            score=self._total(
                base,
                components.occasion,
                components.weather,
                rotation,
                components.preference,
                components.style,
            ),
            components=components,
            pairs=tuple(views),
            hue_groups=hue_groups,
            patterned=patterned,
            belt_shoes=belt_shoes,
            repeated=repeated,
        )

    def quick(self, core: Sequence[EngineItem], extras: Sequence[EngineItem] = ()) -> float:
        """The same score as score(), without the details: for ranking many combinations."""
        base = self._base(core, extras, None)[0]
        return self._total(
            base,
            self.occasion(core),
            self.weather(core),
            self.rotation(core)[0],
            self.preference(core),
            self.style(core),
        )

    def _total(
        self,
        base: float,
        occasion: float,
        weather: float,
        rotation: float,
        preference: float,
        style: float,
    ) -> float:
        config = self.config
        return _clamp(
            config.base_weight * base
            + config.occasion_weight * occasion
            + config.weather_weight * weather
            + config.rotation_weight * rotation
            + config.preference_weight * preference
            + config.style_context_weight * style
        )

    def _is_core_slot(self, slot: str) -> bool:
        return self.slot_kinds.get(slot) == "core"


def _like_rate(likes: int, dislikes: int) -> float:
    return (likes + 1) / (likes + dislikes + 2)


def _clamp(value: float) -> float:
    return min(1.0, max(0.0, value))
