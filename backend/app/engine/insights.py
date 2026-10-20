"""What the wardrobe can do (docs/ENGINE.md, section 11), and the style its wear history shows.

These describe the wardrobe, not today: every item that isn't archived or retired counts
(laundry, packed, lent, and repair are treated as at hand), rotation is fixed at "not worn
lately", and the weather comes from each season. So the numbers move only when the wardrobe
does, and can be cached per wardrobe version.
"""

from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace

from app.engine.color import oklch
from app.engine.config import DEFAULT, EngineConfig
from app.engine.generate import good_cores
from app.engine.pairs import PairScore, PairScores
from app.engine.reasons import mid, text
from app.engine.scoring import Range, Scorer, fits_style
from app.engine.types import Context, EngineItem, Occasion, Style, Wardrobe


@dataclass(frozen=True)
class Family:
    id: str
    name: str
    hex: str | None
    neutrality: float


@dataclass(frozen=True)
class Rescue:
    """Why an item is stranded, and what would help, in one sentence."""

    code: str
    text: str


@dataclass(frozen=True)
class Measures:
    # Distinct good outfits each item is part of (accessories: good outfits it finishes).
    versatility: Mapping[str, int]
    # Items in fewer than two good outfits, least versatile first.
    orphans: tuple[str, ...]
    rescues: Mapping[str, Rescue]
    # Distinct good outfits for each (occasion, season).
    coverage: Mapping[tuple[str, str], int]


@dataclass(frozen=True)
class WornStyle:
    """Shares of core wears, each between 0 and 1."""

    palette: tuple[tuple[str, float], ...]
    formality: tuple[tuple[int, float], ...]
    styles: tuple[tuple[str, float], ...]
    wears: int


def steady(wardrobe: Wardrobe) -> Wardrobe:
    """The wardrobe as a whole: retired items out, everything else clean and at hand, and
    nothing worn lately."""
    return replace(
        wardrobe,
        items=tuple(
            replace(item, status="available", wears_since_wash=0, last_worn_on=None)
            for item in wardrobe.items
            if item.status != "retired" and not item.archived
        ),
    )


def measure(
    wardrobe: Wardrobe,
    base: Context,
    occasions: Sequence[Occasion],
    seasons: Sequence[str],
    families: Sequence[Family],
    config: EngineConfig = DEFAULT,
    pair_cache: dict[tuple[str, str], PairScore] | None = None,
) -> Measures:
    whole = steady(wardrobe)
    context = replace(base, recent_outfits=(), weather=None, anchor_ids=(), exclude_ids=frozenset())
    coverage: dict[tuple[str, str], int] = {}
    good: dict[tuple[str, ...], str] = {}
    for occasion in occasions:
        for season in seasons:
            found = good_cores(
                whole,
                replace(context, occasion=occasion, season=season),
                config.versatility_min_score,
                config,
                pair_cache,
            )
            coverage[(occasion.id, season)] = len(found)
            for outfit in found:
                good.setdefault(outfit.core_ids, outfit.template_id)

    items = {item.id: item for item in whole.items if item.owner_id == base.user_id}
    kinds = whole.slot_kinds
    versatility: Counter[str] = Counter()
    for core in good:
        versatility.update(core)
    scorer = Scorer(context, Range(1, 5), PairScores(config, pair_cache), kinds, config)
    templates = {template.id: template for template in whole.templates}
    accessories = [item for item in items.values() if kinds.get(item.slot) == "accessory"]
    for core, template_id in good.items():
        pieces = [items[item_id] for item_id in core]
        allowed = templates[template_id].optional
        for accessory in accessories:
            if (
                accessory.slot in allowed
                and _fit(accessory, pieces, scorer) >= config.accessory_min
            ):
                versatility[accessory.id] += 1

    counted = [item for item in items.values() if kinds.get(item.slot) in ("core", "accessory")]
    orphans = sorted(
        (item for item in counted if versatility[item.id] < config.orphan_below),
        key=lambda item: (versatility[item.id], item.id),
    )
    rescues = {
        item.id: _rescue(item, whole, items, scorer, families, occasions, config)
        for item in orphans
    }
    return Measures(
        versatility={item.id: versatility[item.id] for item in counted},
        orphans=tuple(item.id for item in orphans),
        rescues=rescues,
        coverage=coverage,
    )


def _fit(item: EngineItem, core: Sequence[EngineItem], scorer: Scorer) -> float:
    total = weights = 0.0
    for piece in core:
        weight = scorer.pair_weight(item, piece)
        total += weight * scorer.pair_value(item, piece)[1]
        weights += weight
    return total / weights if weights else 0.0


def _rescue(
    item: EngineItem,
    wardrobe: Wardrobe,
    items: Mapping[str, EngineItem],
    scorer: Scorer,
    families: Sequence[Family],
    occasions: Sequence[Occasion],
    config: EngineConfig,
) -> Rescue:
    """Why the item is stranded, in order: nothing to pair with in a slot; a level of dress
    none of the occasions has; a slot it pairs badly with; or partners that pair with it but
    not with each other. The last two suggest a plain neutral that would help."""
    names = wardrobe.slot_names
    if wardrobe.slot_kinds.get(item.slot) != "core":
        return Rescue("rescue.accessory", text("rescue.accessory"))
    partners: set[str] = set()
    for template in wardrobe.templates:
        slots = [requirement.slot for requirement in template.required]
        holds = any(
            requirement.slot == item.slot and requirement.accepts(item.category_id)
            for requirement in template.required
        )
        if holds:
            partners.update(slot for slot in slots if slot != item.slot)
    best: dict[str, float] = {}
    for slot in sorted(partners):
        options = [other for other in items.values() if other.slot == slot]
        if not options:
            name = mid(names.get(slot, slot))
            return Rescue("missing.none_owned", text("missing.none_owned", slot=name))
        best[slot] = max(scorer.pair_value(item, other)[1] for other in options)
    outside = occasions and all(
        item.formality < occasion.formality_min or item.formality > occasion.formality_max
        for occasion in occasions
    )
    if outside or not best:
        return Rescue("rescue.occasions", text("rescue.occasions"))
    slot = min(best, key=lambda key: (best[key], key))
    colour = _contrasting_neutral(item, families)
    if colour is None:
        return Rescue("rescue.accessory", text("rescue.accessory"))
    code = "rescue.slot" if best[slot] < config.pair_edge else "rescue.partners"
    return Rescue(code, text(code, slot=mid(names.get(slot, slot)), color=colour))


def _contrasting_neutral(item: EngineItem, families: Sequence[Family]) -> str | None:
    """The neutral that contrasts most in lightness with the item: neutrals with clear
    contrast are the colour table's best pairing."""
    lightness = oklch(item.color_hex)[0] if item.color_hex else 0.5
    neutrals = [
        family
        for family in families
        if family.hex is not None and family.neutrality >= 1.0 and family.id != item.color_family
    ]
    if not neutrals:
        return None
    best = max(
        neutrals,
        key=lambda family: (abs(oklch(family.hex or "#808080")[0] - lightness), family.id),
    )
    return best.name.split(" / ")[0].split(" (")[0].lower()


def worn_style(
    worn: Sequence[tuple[EngineItem, int]],
    styles: Sequence[Style],
    slot_kinds: Mapping[str, str],
    config: EngineConfig = DEFAULT,
) -> WornStyle:
    """The palette, formality mix, and styles of what's actually worn: core pieces, weighted
    by how often each was worn."""
    core = [(item, count) for item, count in worn if slot_kinds.get(item.slot) == "core" and count]
    total = sum(count for _, count in core)
    if not total:
        return WornStyle((), (), (), 0)
    palette: Counter[str] = Counter()
    levels: Counter[int] = Counter()
    matched: Counter[str] = Counter()
    for item, count in core:
        palette[item.color_family] += count
        levels[item.formality] += count
        for style in styles:
            if fits_style(item, style, config):
                matched[style.id] += count
    return WornStyle(
        palette=tuple(
            (family, count / total)
            for family, count in sorted(palette.items(), key=lambda entry: (-entry[1], entry[0]))
        ),
        formality=tuple((level, levels[level] / total) for level in range(1, 6)),
        styles=tuple(
            (style, count / total)
            for style, count in sorted(matched.items(), key=lambda entry: (-entry[1], entry[0]))
        ),
        wears=total,
    )
