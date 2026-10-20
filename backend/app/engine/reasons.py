"""Reasons for a suggestion: codes from the scores, turned into sentences.

Every sentence the engine can say lives in TEXTS, so wording changes never touch scoring. A
reason's code and strength come from the same numbers that set the score; the UI shows the
text and never works a reason out on its own.

Item names are often plural ("Denim blue jeans", "Brown loafers"), so no sentence puts a verb
straight after a single name: names sit in pairs ("A and b are"), after a preposition, or
before a modal verb ("won't", "may").
"""

from collections.abc import Mapping, Sequence
from typing import Protocol

from app.engine.pairs import tone
from app.engine.scoring import Breakdown, PairView, Scorer, upper_warmth
from app.engine.types import EngineItem, Reason, ReasonKind


class _Add(Protocol):
    def __call__(self, code: str, kind: ReasonKind, strength: float, **values: str) -> None: ...


TEXTS: dict[str, str] = {
    # Positives.
    "set.match": "{A} and {b} are a matching set.",
    "color.neutral_plus_accent": "A neutral base lets one colour lead: the {accent}.",
    "color.neutrals": "{A} and {b}: neutrals with clear contrast, so it looks deliberate.",
    "color.quiet_neutrals": "{A} and {b} are close neutrals: quiet and easy.",
    "color.tonal": "{A} and {b} are shades of one colour, light against dark.",
    "color.analogous": "{A} and {b} are neighbouring colours, so they blend.",
    "color.complement": "{A} and {b} are opposite colours, kept soft so they balance.",
    "color.multi_neutral": "A neutral base lets the multicolour {accent} lead.",
    "formality.match": "Every piece sits at the same level of dress.",
    "pattern.one_statement": "The one pattern is the {a}; everything else stays plain.",
    "occasion.fits": "The right level of dress for {occasion}.",
    "occasion.prefers_group": "{group} pieces suit {occasion}.",
    "weather.breathable": "Breathable {fabrics} for the heat.",
    "weather.right_warmth.day": "The right weight for {season}.",
    "weather.right_warmth.winter": "Warm enough for winter.",
    "weather.right_warmth.mild": "The right weight for mild days.",
    "weather.right_warmth.monsoon": "Light enough for humid monsoon days.",
    "rotation.never_worn": "You haven't worn any of these yet.",
    "rotation.not_worn_recently": "None of these has been worn in the last two weeks.",
    "preference.liked": "Close to what you've liked before.",
    "preference.colors": "Uses {color}, one of your favourite colours.",
    "style.match": "Fits your {style} style.",
    "belt.matches_shoes": "The belt matches the shoes.",
    # Cautions.
    "color.near_miss": "{A} and {b} are close in colour without matching; more contrast would "
    "look more deliberate.",
    "color.awkward": "{A} and {b} are colours that can fight each other.",
    "color.loud_complement": "{A} and {b} are two strong opposite colours: a bold look.",
    "color.multi_colour": "The multicolour {a} may compete with the {b}.",
    "color.too_many": "More than two colours compete here.",
    "formality.shoes_more_casual": "The footwear is more casual than the rest.",
    "formality.shoes_dressier": "The footwear is dressier than the rest.",
    "formality.mixed": "These pieces sit at different levels of dress.",
    "pattern.clash": "Two patterns compete for attention.",
    "fabric.clash": "{A} and {b} are fabrics that rarely sit well together.",
    "fabric.denim_on_denim": "Denim on denim in one shade can look like a uniform.",
    "fabric.no_shared_season": "{A} and {b} are usually worn in different seasons.",
    "occasion.more_casual": "A little more casual than {occasion} usually is.",
    "occasion.dressier": "A little dressier than {occasion} usually is.",
    "weather.too_warm": "Probably too warm for {season}.",
    "weather.too_light": "May be too light for {season}; add a layer.",
    "weather.rain": "The {a} won't love the rain.",
    "weather.cold": "The {a} may feel cold at {temperature}.",
    "rotation.repeat": "You wore this exact outfit in the last week.",
    "rotation.just_worn": "You wore the {a} in the last two days.",
    "belt.clashes_shoes": "The belt and shoes are different leathers; matching them looks sharper.",
    # When an outfit can't be made (generate.py).
    "missing.none_owned": "There's no {slot} in your wardrobe yet.",
    "missing.unavailable": "No {slot} is available right now: it's all in the laundry, away, or "
    "due a wash.",
    "missing.too_casual": "No {slot} is dressy enough for {occasion}.",
    "missing.too_dressy": "No {slot} is casual enough for {occasion}.",
    "missing.season": "No {slot} is marked for {season}.",
    "missing.avoided": "Every {slot} you have is in a colour you avoid.",
    "missing.excluded": "You've left out every {slot} for this request.",
    "missing.formality_gap": "Your {slot} options are too far in formality from the rest.",
    "missing.anchors": "These pieces don't fit in one outfit together.",
    "missing.anchor_unavailable": "The {a} can't be used right now; check its status.",
    "missing.anchor_due_wash": "The {a} should be washed first.",
    # Planning a week (planner.py).
    "plan.no_occasion": "Choose an occasion for this day.",
    "plan.blocked": "Everything that fits this day is due a wash or worn too recently by then. "
    "A laundry day in your usual week frees things up.",
    # Packing (packing.py).
    "packing.no_good_outfit": "Nothing you have makes a good enough outfit for this day.",
    "packing.not_enough": "The packed pieces run out of clean wears by this day.",
    # Notes on the whole result.
    "note.only_one": "This is the only outfit your available pieces make.",
    "note.few": "Only {count} different outfits work with what's available.",
    "note.compromise": "Nothing fits {occasion} exactly, so these are the closest, a step "
    "more casual or dressy.",
}

# Seasons as they read inside a sentence ("too warm for mild weather").
SEASON_PHRASES: dict[str, str] = {
    "summer": "summer",
    "monsoon": "the monsoon",
    "mild": "mild weather",
    "winter": "winter",
}

# Colour cases that make a good reason, and those that are worth a caution.
_COLOUR_POSITIVE = {
    "tonal": "color.tonal",
    "analogous": "color.analogous",
    "complement_muted": "color.complement",
}
_COLOUR_CAUTION = {
    "near_miss": "color.near_miss",
    "awkward": "color.awkward",
    "complement_saturated": "color.loud_complement",
    "multi_colour": "color.multi_colour",
}
# A colour caution needs a pair at least this important (top and bottom, shoes and bottom).
_CAUTION_PAIR_WEIGHT = 0.8


def text(code: str, **values: str) -> str:
    return TEXTS[code].format(**values)


def season_phrase(season: str | None) -> str:
    return SEASON_PHRASES.get(season or "", season or "this season")


def mid(name: str) -> str:
    """A name for the middle of a sentence: "Navy shirt" becomes "navy shirt", but an
    acronym or a name in capitals stays as it is."""
    if len(name) > 1 and name[:2].isupper():
        return name
    return name[:1].lower() + name[1:]


def _names(a: EngineItem, b: EngineItem) -> dict[str, str]:
    return {"A": a.name, "a": mid(a.name), "b": mid(b.name)}


def explain(
    breakdown: Breakdown,
    core: Sequence[EngineItem],
    scorer: Scorer,
    color_names: Mapping[str, str],
    group_names: Mapping[str, str],
) -> tuple[Reason, ...]:
    """The two or three strongest positives, then any cautions."""
    found: list[Reason] = []

    def add(code: str, kind: ReasonKind, strength: float, **values: str) -> None:
        found.append(Reason(code=code, kind=kind, strength=strength, text=text(code, **values)))

    config = scorer.config
    core_pairs = sorted(
        (view for view in breakdown.pairs if view.core),
        key=lambda view: (-view.weight, view.a.id, view.b.id),
    )
    sets = [view for view in core_pairs if view.score.same_set]
    if sets:
        add("set.match", "positive", 1.0, **_names(sets[0].a, sets[0].b))
    if core_pairs:
        _colour_reasons(core_pairs, scorer, add)
    if breakdown.hue_groups > config.too_many_hues:
        add("color.too_many", "caution", 0.6)

    levels = [item.formality for item in core]
    if max(levels) - min(levels) <= 1:
        add("formality.match", "positive", 0.6)
    else:
        shoes = next((item for item in core if item.slot == "footwear"), None)
        others = [item.formality for item in core if item is not shoes]
        if shoes is not None and others:
            mean = sum(others) / len(others)
            if shoes.formality <= mean - 1.5:
                add("formality.shoes_more_casual", "caution", 0.5, a=mid(shoes.name))
            elif shoes.formality >= mean + 1.5:
                add("formality.shoes_dressier", "caution", 0.5, a=mid(shoes.name))
            elif max(levels) - min(levels) >= 2:
                add("formality.mixed", "caution", 0.4)

    patterned = [item for item in core if item.pattern not in config.plain_patterns]
    if len(patterned) == 1:
        add("pattern.one_statement", "positive", 0.5, a=mid(patterned[0].name))
    elif len(patterned) > 1:
        add("pattern.clash", "caution", 0.5)

    for view in core_pairs:
        case = view.score.fabric_case
        if case:
            code = f"fabric.{case}"
            add(code, "caution", 0.4, **_names(view.a, view.b))
            break

    _occasion_reasons(breakdown, core, scorer, group_names, add)
    _weather_reasons(breakdown, core, scorer, add)
    _rotation_reasons(breakdown, core, scorer, add)

    components = breakdown.components
    has_feedback = any(
        (item.color_family, item.category_id) in scorer.context.preferences.family_category_counts
        or item.id in scorer.context.preferences.item_counts
        for item in core
    )
    if has_feedback and components.preference >= 0.65:
        add("preference.liked", "positive", components.preference * 0.6)
    preferred = [
        item for item in core if item.color_family in scorer.context.preferences.preferred_colors
    ]
    if preferred:
        family = preferred[0].color_family
        add("preference.colors", "positive", 0.35, color=mid(color_names.get(family, family)))

    if scorer.styles and components.style >= 2 / 3:
        add("style.match", "positive", 0.5 * components.style, style=_style_name(core, scorer))

    if breakdown.belt_shoes > 0:
        add("belt.matches_shoes", "positive", 0.3)
    elif breakdown.belt_shoes < 0:
        add("belt.clashes_shoes", "caution", 0.3)

    positives = sorted(
        (r for r in found if r.kind == "positive"), key=lambda r: (-r.strength, r.code)
    )[: config.max_positive_reasons]
    cautions = sorted(
        (r for r in found if r.kind == "caution"), key=lambda r: (-r.strength, r.code)
    )[: config.max_caution_reasons]
    return (*positives, *cautions)


def _colour_reasons(core_pairs: list[PairView], scorer: Scorer, add: _Add) -> None:
    main = core_pairs[0]
    case = main.score.colour_case
    a, b = main.a, main.b
    tone_a, tone_b = _neutral(a, scorer), _neutral(b, scorer)
    strength = main.weight * main.score.colour
    if case in ("neutral_contrast", "neutral_similar") and tone_a != tone_b:
        neutral, accent = (a, b) if tone_a else (b, a)
        add(
            "color.neutral_plus_accent",
            "positive",
            strength,
            neutral=mid(neutral.name),
            accent=mid(accent.name),
        )
    elif case == "neutral_contrast":
        add("color.neutrals", "positive", strength, **_names(a, b))
    elif case == "neutral_similar":
        add("color.quiet_neutrals", "positive", strength * 0.8, **_names(a, b))
    elif case == "multi_neutral":
        neutral, accent = (b, a) if a.color_hex is None else (a, b)
        add(
            "color.multi_neutral",
            "positive",
            strength,
            neutral=mid(neutral.name),
            accent=mid(accent.name),
        )
    elif case in _COLOUR_POSITIVE:
        add(_COLOUR_POSITIVE[case], "positive", strength, **_names(a, b))
    for view in core_pairs:
        code = _COLOUR_CAUTION.get(view.score.colour_case)
        if code and view.weight >= _CAUTION_PAIR_WEIGHT:
            first, second = (view.a, view.b)
            if view.score.colour_case == "multi_colour" and second.color_hex is None:
                first, second = second, first
            add(code, "caution", 1 - view.score.colour, **_names(first, second))
            break


def _neutral(item: EngineItem, scorer: Scorer) -> bool:
    return tone(item, scorer.config).neutral


def _occasion_reasons(
    breakdown: Breakdown,
    core: Sequence[EngineItem],
    scorer: Scorer,
    group_names: Mapping[str, str],
    add: _Add,
) -> None:
    occasion = scorer.level.occasion
    if occasion is None:
        return
    name = mid(occasion.name)
    groups = sorted(occasion.prefers_groups & {item.group_id for item in core})
    if groups:
        group = group_names.get(groups[0], groups[0])
        add("occasion.prefers_group", "positive", 0.7, group=group, occasion=name)
    value = breakdown.components.occasion
    if value >= 1:
        add("occasion.fits", "positive", 0.55, occasion=name)
    elif value < 0.85:
        mean = sum(item.formality for item in core) / len(core)
        code = "occasion.more_casual" if mean < scorer.level.low else "occasion.dressier"
        add(code, "caution", 1 - value, occasion=name)


def _weather_reasons(
    breakdown: Breakdown, core: Sequence[EngineItem], scorer: Scorer, add: _Add
) -> None:
    climate = scorer.climate
    config = scorer.config
    if climate.band is None:
        return
    season = scorer.context.season
    if climate.feels_like is not None:
        temperature = f"{round(climate.feels_like)}°"
        phrase = f"a {temperature} day"
    else:
        temperature = ""
        phrase = season_phrase(season)
    warmth = upper_warmth(core)
    low, high = climate.band
    if warmth > high:
        add("weather.too_warm", "caution", 0.3 * (warmth - high), season=phrase)
    elif warmth < low:
        add("weather.too_light", "caution", 0.3 * (low - warmth), season=phrase)
    elif climate.hot:
        fabrics = sorted(
            {
                item.fabric
                for item in core
                if item.fabric in config.breathable_fabrics and item.slot != "footwear"
            }
        )
        if fabrics and not any(item.slot == "layer" for item in core):
            add("weather.breathable", "positive", 0.45, fabrics=" and ".join(fabrics))
    elif climate.feels_like is not None:
        add("weather.right_warmth.day", "positive", 0.4, season=phrase)
    elif f"weather.right_warmth.{season}" in TEXTS:
        add(f"weather.right_warmth.{season}", "positive", 0.4)
    if climate.cold:
        exposed = scorer.cold_risks(core)
        if exposed:
            add("weather.cold", "caution", 0.4, a=mid(exposed[0].name), temperature=temperature)
    if climate.rain:
        risky = scorer.rain_risks(core)
        if risky:
            add("weather.rain", "caution", 0.35, a=mid(risky[0].name))


def _rotation_reasons(
    breakdown: Breakdown, core: Sequence[EngineItem], scorer: Scorer, add: _Add
) -> None:
    if breakdown.repeated:
        add("rotation.repeat", "caution", 0.7)
        return
    recent = [
        item
        for item in core
        if item.last_worn_on is not None
        and 0 <= (scorer.context.today - item.last_worn_on).days <= 2
    ]
    if recent:
        add("rotation.just_worn", "caution", 0.35, a=mid(recent[0].name))
    elif all(item.last_worn_on is None for item in core):
        add("rotation.never_worn", "positive", 0.4)
    elif breakdown.components.rotation >= 0.9:
        add("rotation.not_worn_recently", "positive", 0.4)


def _style_name(core: Sequence[EngineItem], scorer: Scorer) -> str:
    """The style most of the pieces match."""
    best = max(
        scorer.styles,
        key=lambda style: (
            sum(1 for item in core if scorer.fits_style(item, style)),
            -scorer.styles.index(style),
        ),
    )
    return best.name
