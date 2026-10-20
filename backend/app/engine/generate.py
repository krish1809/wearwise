"""Suggesting outfits: the pipeline in docs/ENGINE.md, sections 2 to 8.

filter -> templates -> generate -> score -> accessorise -> diversify -> explain

One function, suggest(), serves all three entry points: no anchors suggests for an occasion,
one anchor answers "what goes with this?", two or more complete an outfit. Same input, same
output: items are sorted by id and every tie is broken by item ids.
"""

import math
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date
from itertools import product

from app.engine.config import DEFAULT, ENGINE_VERSION, EngineConfig
from app.engine.outfits import Piece, Requirement, Template, check_outfit
from app.engine.pairs import PairScore, PairScores
from app.engine.reasons import explain, mid, season_phrase, text
from app.engine.scoring import Breakdown, Range, Scorer
from app.engine.types import (
    Context,
    EngineItem,
    Missing,
    ScoredOutfit,
    Suggestions,
    Wardrobe,
)

LAYER = "layer"


@dataclass(frozen=True)
class _Draft:
    """A core outfit with its quick score, before accessories and details."""

    template: Template
    core: tuple[EngineItem, ...]
    extras: tuple[EngineItem, ...]
    score: float
    key: tuple[str, ...]


@dataclass(frozen=True)
class _Candidate:
    template: Template
    core: tuple[EngineItem, ...]
    extras: tuple[EngineItem, ...]
    breakdown: Breakdown
    # Sorted ids of the core pieces: the outfit's identity, and the tie-breaker.
    key: tuple[str, ...]


@dataclass
class _Run:
    candidates: list[_Draft]
    missing: list[Missing]


def season_for(day: date, config: EngineConfig = DEFAULT) -> str:
    """The season a day falls in, when a request doesn't name one."""
    return config.season_by_month[day.month]


def suggest(
    wardrobe: Wardrobe,
    context: Context,
    config: EngineConfig = DEFAULT,
    pair_cache: dict[tuple[str, str], PairScore] | None = None,
) -> Suggestions:
    """Up to context.count outfits, best first and different from each other."""
    return _suggest(wardrobe, context, config, pair_cache, diverse=True)


def rank(
    wardrobe: Wardrobe,
    context: Context,
    config: EngineConfig = DEFAULT,
    pair_cache: dict[tuple[str, str], PairScore] | None = None,
    item_cap: int | None = None,
) -> Suggestions:
    """Up to context.count outfits in score order, without the variety pass: for the
    planner, which keeps a week varied itself. With item_cap, no core piece appears in more
    than that many of them, so the list spans the wardrobe."""
    return _suggest(wardrobe, context, config, pair_cache, diverse=False, item_cap=item_cap)


def _suggest(
    wardrobe: Wardrobe,
    context: Context,
    config: EngineConfig,
    pair_cache: dict[tuple[str, str], PairScore] | None,
    *,
    diverse: bool,
    item_cap: int | None = None,
) -> Suggestions:
    owned = sorted(
        (item for item in wardrobe.items if item.owner_id == context.user_id),
        key=lambda item: item.id,
    )
    by_id = {item.id: item for item in owned if not item.archived}
    anchors = tuple(by_id[anchor] for anchor in context.anchor_ids if anchor in by_id)
    if len(anchors) != len(context.anchor_ids):
        raise ValueError("Anchors must be the person's own items, not archived.")
    for anchor in anchors:
        if not _clean(anchor):
            code = (
                "missing.anchor_unavailable"
                if anchor.status != "available"
                else "missing.anchor_due_wash"
            )
            missing = Missing(
                slot=anchor.slot,
                template_id="",
                code=code,
                text=text(code, a=mid(anchor.name)),
            )
            return Suggestions(outfits=(), missing=(missing,), engine_version=ENGINE_VERSION)

    pairs = PairScores(config, pair_cache)
    level = _level(context, anchors)
    # Long ranked lists (the planner's) need a beam spread across the wardrobe.
    spread = item_cap is not None
    first = _run(wardrobe, context, config, pairs, owned, anchors, level, spread)
    if first.candidates:
        return _finish(
            wardrobe,
            context,
            config,
            pairs,
            first,
            level,
            anchors,
            compromise=False,
            diverse=diverse,
            item_cap=item_cap,
        )
    if context.occasion is not None and not _anchor_problem(first):
        relaxed = Range(level.low - 1, level.high + 1, level.occasion)
        second = _run(wardrobe, context, config, pairs, owned, anchors, relaxed, spread)
        if second.candidates:
            # The first run's gaps explain why these are compromises.
            second.missing = first.missing
            return _finish(
                wardrobe,
                context,
                config,
                pairs,
                second,
                level,
                anchors,
                compromise=True,
                diverse=diverse,
                item_cap=item_cap,
            )
    return Suggestions(outfits=(), missing=tuple(first.missing), engine_version=ENGINE_VERSION)


def _level(context: Context, anchors: Sequence[EngineItem]) -> Range:
    if context.occasion is not None:
        occasion = context.occasion
        return Range(occasion.formality_min, occasion.formality_max, occasion)
    if not anchors:
        raise ValueError("Suggesting needs an occasion or at least one anchor.")
    levels = [item.formality for item in anchors]
    return Range(min(levels), max(levels))


def _clean(item: EngineItem) -> bool:
    """Available and not due a wash."""
    if item.status != "available":
        return False
    return item.wears_before_wash is None or item.wears_since_wash < item.wears_before_wash


def _why_not(item: EngineItem, context: Context, level: Range, config: EngineConfig) -> str | None:
    """Which hard filter (section 3) removes the item, or None if it can be used."""
    if item.archived:
        return "archived"
    if item.id in context.exclude_ids:
        return "missing.excluded"
    if not _clean(item):
        return "missing.unavailable"
    if item.color_family in context.preferences.avoided_colors:
        return "missing.avoided"
    if item.formality <= level.low - config.occasion_filter_steps:
        return "missing.too_casual"
    if item.formality >= level.high + config.occasion_filter_steps:
        return "missing.too_dressy"
    if context.season and item.seasons and context.season not in item.seasons:
        return "missing.season"
    return None


def _run(
    wardrobe: Wardrobe,
    context: Context,
    config: EngineConfig,
    pairs: PairScores,
    owned: Sequence[EngineItem],
    anchors: tuple[EngineItem, ...],
    level: Range,
    spread: bool = False,
) -> _Run:
    anchor_ids = {anchor.id for anchor in anchors}
    usable = [
        item
        for item in owned
        if item.id not in anchor_ids and _why_not(item, context, level, config) is None
    ]
    scorer = Scorer(context, level, pairs, wardrobe.slot_kinds, config)
    candidates: list[_Draft] = []
    gaps: list[tuple[int, int, list[Missing]]] = []
    fitting = [t for t in wardrobe.templates if _holds(t, anchors)]
    if not fitting:
        anchor = anchors[0] if anchors else None
        missing = Missing(
            slot=anchor.slot if anchor else "",
            template_id="",
            code="missing.anchors",
            text=text("missing.anchors"),
        )
        return _Run([], [missing])
    # Anchors outside the core (a watch, a fragrance) ride along with every outfit.
    extras = tuple(anchor for anchor in anchors if not _is_core(anchor.slot, wardrobe))
    for order, template in enumerate(fitting):
        slots = _core_slots(template, anchors, usable)
        empty = [
            requirement
            for requirement, options in zip(template.required, slots, strict=False)
            if not options
        ]
        if empty:
            explained = [
                _explain_empty(requirement, template, owned, context, level, config, wardrobe)
                for requirement in empty
            ]
            gaps.append((len(empty), order, explained))
            continue
        found = _generate(template, slots, extras, scorer, config, spread)
        if not found:
            requirement = template.required[-1]
            name = wardrobe.slot_names.get(requirement.slot, requirement.slot)
            missing = Missing(
                slot=requirement.slot,
                template_id=template.id,
                code="missing.formality_gap",
                text=text("missing.formality_gap", slot=mid(name)),
            )
            gaps.append((1, order, [missing]))
        candidates += found
    if candidates:
        return _Run(candidates, [])
    gaps.sort(key=lambda gap: (gap[0], gap[1]))
    return _Run([], gaps[0][2] if gaps else [])


def _holds(template: Template, anchors: Sequence[EngineItem]) -> bool:
    """Whether the template has a place for every anchor, one per slot."""
    slots = [anchor.slot for anchor in anchors]
    if len(slots) != len(set(slots)):
        return False
    required = {requirement.slot: requirement for requirement in template.required}
    for anchor in anchors:
        requirement = required.get(anchor.slot)
        if requirement is not None:
            if not requirement.accepts(anchor.category_id):
                return False
        elif anchor.slot not in template.optional:
            return False
    return True


def _core_slots(
    template: Template, anchors: Sequence[EngineItem], usable: Sequence[EngineItem]
) -> list[list[EngineItem | None]]:
    """The options for each core slot, in fill order: the required slots, then the layer
    (which may stay empty)."""
    anchored = {anchor.slot: anchor for anchor in anchors}
    slots: list[list[EngineItem | None]] = []
    for requirement in template.required:
        if requirement.slot in anchored:
            slots.append([anchored[requirement.slot]])
        else:
            slots.append(
                [
                    item
                    for item in usable
                    if item.slot == requirement.slot and requirement.accepts(item.category_id)
                ]
            )
    if LAYER in template.optional:
        if LAYER in anchored:
            slots.append([anchored[LAYER]])
        else:
            slots.append([None, *(item for item in usable if item.slot == LAYER)])
    return slots


def _generate(
    template: Template,
    slots: list[list[EngineItem | None]],
    extras: tuple[EngineItem, ...],
    scorer: Scorer,
    config: EngineConfig,
    spread: bool = False,
) -> list[_Draft]:
    """Every core outfit when there are few enough, otherwise a beam search."""
    total = math.prod(len(options) for options in slots)
    if total <= config.enumerate_limit:
        combos: list[tuple[EngineItem, ...]] = []
        for combo in product(*slots):
            core = tuple(item for item in combo if item is not None)
            if not _rejected(core, scorer):
                combos.append(core)
    else:
        combos = _beam(slots, extras, scorer, config, spread)
    scored = _scored_extras(extras, scorer)
    return [
        _Draft(template, core, extras, scorer.quick(core, scored), _key(core)) for core in combos
    ]


def _beam(
    slots: list[list[EngineItem | None]],
    extras: tuple[EngineItem, ...],
    scorer: Scorer,
    config: EngineConfig,
    spread: bool = False,
) -> list[tuple[EngineItem, ...]]:
    """Fill the slots in order, keeping the best partial outfits at each step. With
    `spread`, no piece takes more than its share of the beam, or the few best tops would
    crowd out the rest of the wardrobe after the first step (anchors, the only option for a
    slot, are exempt)."""
    scored = _scored_extras(extras, scorer)
    cap = max(1, int(config.beam_width * config.beam_item_share)) if spread else 0
    fixed = {option.id for options in slots if len(options) == 1 for option in options if option}
    partials: list[tuple[EngineItem, ...]] = [()]
    for options in slots:
        grown: list[tuple[float, tuple[str, ...], tuple[EngineItem, ...]]] = []
        for partial in partials:
            for option in options:
                if option is None:
                    core = partial
                else:
                    if any(scorer.pairs.get(option, item).rejected for item in partial):
                        continue
                    core = (*partial, option)
                grown.append((scorer.quick(core, scored), _key(core), core))
        grown.sort(key=lambda entry: (-entry[0], entry[1]))
        ranked = [core for _, _, core in grown]
        partials = (
            _spread(ranked, config.beam_width, cap, fixed)
            if spread
            else ranked[: config.beam_width]
        )
    return partials


def _spread(
    ranked: list[tuple[EngineItem, ...]], width: int, cap: int, fixed: set[str]
) -> list[tuple[EngineItem, ...]]:
    """The best `width` partial outfits, at most `cap` per piece; if that leaves room, the
    best of the rest fill it."""
    uses: Counter[str] = Counter()
    kept: list[tuple[EngineItem, ...]] = []
    skipped: list[tuple[EngineItem, ...]] = []
    for core in ranked:
        if len(kept) == width:
            break
        free = [item.id for item in core if item.id not in fixed]
        if any(uses[item_id] >= cap for item_id in free):
            skipped.append(core)
            continue
        kept.append(core)
        uses.update(free)
    return kept + skipped[: width - len(kept)]


def _is_core(slot: str, wardrobe: Wardrobe) -> bool:
    return wardrobe.slot_kinds.get(slot) == "core"


def _scored_extras(extras: Sequence[EngineItem], scorer: Scorer) -> tuple[EngineItem, ...]:
    """Extras that pair with the clothes: accessories. A fragrance has no colour to match."""
    return tuple(item for item in extras if scorer.slot_kinds.get(item.slot) == "accessory")


def _rejected(core: Sequence[EngineItem], scorer: Scorer) -> bool:
    for index, a in enumerate(core):
        for b in core[index + 1 :]:
            if scorer.pairs.get(a, b).rejected:
                return True
    return False


def _key(core: Sequence[EngineItem]) -> tuple[str, ...]:
    return tuple(sorted(item.id for item in core))


def _explain_empty(
    requirement: Requirement,
    template: Template,
    owned: Sequence[EngineItem],
    context: Context,
    level: Range,
    config: EngineConfig,
    wardrobe: Wardrobe,
) -> Missing:
    slot_name = mid(wardrobe.slot_names.get(requirement.slot, requirement.slot))
    in_slot = [
        item
        for item in owned
        if item.slot == requirement.slot
        and requirement.accepts(item.category_id)
        and not item.archived
    ]
    causes = Counter(_why_not(item, context, level, config) for item in in_slot)
    causes.pop(None, None)
    order = [
        "missing.unavailable",
        "missing.too_casual",
        "missing.too_dressy",
        "missing.season",
        "missing.avoided",
        "missing.excluded",
    ]
    code = (
        "missing.none_owned"
        if not in_slot or not causes
        else max(order, key=lambda cause: (causes.get(cause, 0), -order.index(cause)))
    )
    values = {
        "slot": slot_name,
        "occasion": mid(level.occasion.name) if level.occasion else "this",
        "season": season_phrase(context.season),
    }
    return Missing(
        slot=requirement.slot,
        template_id=template.id,
        code=code,
        text=text(code, **values),
    )


def _anchor_problem(run: _Run) -> bool:
    return any(missing.code == "missing.anchors" for missing in run.missing)


def _finish(
    wardrobe: Wardrobe,
    context: Context,
    config: EngineConfig,
    pairs: PairScores,
    run: _Run,
    level: Range,
    anchors: tuple[EngineItem, ...],
    *,
    compromise: bool,
    diverse: bool,
    item_cap: int | None = None,
) -> Suggestions:
    scorer = Scorer(context, level, pairs, wardrobe.slot_kinds, config)
    ranked = sorted(run.candidates, key=lambda draft: (-draft.score, draft.key))
    if item_cap is None:
        pool = ranked[: max(config.accessorise_top, context.count)]
    else:
        pool = _capped(ranked, item_cap, context.count)
    usable = [
        item
        for item in wardrobe.items
        if item.owner_id == context.user_id
        and item.id not in {anchor.id for anchor in anchors}
        and _why_not(item, context, level, config) is None
    ]
    usable.sort(key=lambda item: item.id)
    finished = [_accessorise(c, anchors, usable, scorer, wardrobe, level) for c in pool]
    if diverse:
        picked = _diversify(finished, {anchor.id for anchor in anchors}, context.count, config)
    else:
        picked = sorted(finished, key=lambda c: (-c.breakdown.score, c.key))[: context.count]
    order = list(wardrobe.slot_kinds)
    outfits = []
    for candidate in picked:
        everything = (*candidate.core, *candidate.extras)
        items = tuple(
            sorted(
                everything,
                key=lambda item: (order.index(item.slot) if item.slot in order else 99, item.id),
            )
        )
        outfits.append(
            ScoredOutfit(
                template_id=candidate.template.id,
                items=items,
                core_ids=candidate.key,
                score=round(candidate.breakdown.score, 4),
                components=candidate.breakdown.components,
                reasons=explain(
                    candidate.breakdown,
                    candidate.core,
                    scorer,
                    wardrobe.color_names,
                    wardrobe.group_names,
                ),
                compromise=compromise,
            )
        )
    note = None
    if compromise and level.occasion:
        note = text("note.compromise", occasion=mid(level.occasion.name))
    elif len(outfits) == 1:
        note = text("note.only_one")
    elif len(outfits) < context.count:
        note = text("note.few", count=str(len(outfits)))
    return Suggestions(
        outfits=tuple(outfits),
        missing=tuple(run.missing),
        compromise=compromise,
        note=note,
        engine_version=ENGINE_VERSION,
    )


def _accessorise(
    candidate: _Draft,
    anchors: Sequence[EngineItem],
    usable: Sequence[EngineItem],
    scorer: Scorer,
    wardrobe: Wardrobe,
    level: Range,
) -> _Candidate:
    """Add the best accessory for each free optional slot, if it goes well enough, and a
    fragrance chosen by season and occasion."""
    taken = {item.slot for item in (*candidate.core, *candidate.extras)}
    added: list[EngineItem] = []
    for slot in _slot_order(candidate.template.optional, wardrobe.slot_kinds):
        if slot == LAYER or slot in taken:
            continue
        options = [item for item in usable if item.slot == slot]
        if not options:
            continue
        if wardrobe.slot_kinds.get(slot) == "finishing":
            chosen = _fragrance(options, scorer.context, level)
            if chosen:
                added.append(chosen)
            continue
        fit, best = min(
            ((_accessory_fit(option, candidate.core, scorer), option) for option in options),
            key=lambda entry: (-entry[0], entry[1].id),
        )
        if fit >= scorer.config.accessory_min:
            added.append(best)
    extras = (*candidate.extras, *added)
    breakdown = scorer.score(candidate.core, _scored_extras(extras, scorer))
    return _Candidate(candidate.template, candidate.core, extras, breakdown, candidate.key)


def _capped(ranked: Sequence[_Draft], cap: int, count: int) -> list[_Draft]:
    """The best drafts in order, with each piece in no more than its fair share of them: the
    count divided by how many pieces its slot has (at least `cap`), so a long list spans the
    wardrobe instead of leaning on a few favourites. If that leaves room, the best of the
    rest fill it."""
    by_slot: dict[str, set[str]] = {}
    for draft in ranked:
        for item in draft.core:
            by_slot.setdefault(item.slot, set()).add(item.id)
    share = {
        item_id: max(cap, math.ceil(count / len(ids)))
        for ids in by_slot.values()
        for item_id in ids
    }
    uses: Counter[str] = Counter()
    picked: list[_Draft] = []
    skipped: list[_Draft] = []
    for draft in ranked:
        if len(picked) == count:
            break
        if any(uses[item_id] >= share[item_id] for item_id in draft.key):
            skipped.append(draft)
            continue
        picked.append(draft)
        uses.update(draft.key)
    return picked + skipped[: count - len(picked)]


def _slot_order(slots: frozenset[str], kinds: Mapping[str, str]) -> list[str]:
    order = list(kinds)
    return sorted(slots, key=lambda slot: (order.index(slot) if slot in order else 99, slot))


def _accessory_fit(item: EngineItem, core: Sequence[EngineItem], scorer: Scorer) -> float:
    """The weighted mean of the accessory's pair scores with the core pieces."""
    total = weight_sum = 0.0
    for piece in core:
        weight = scorer.pair_weight(item, piece)
        _, value = scorer.pair_value(item, piece)
        total += weight * value
        weight_sum += weight
    return total / weight_sum if weight_sum else 0.0


def _fragrance(options: Sequence[EngineItem], context: Context, level: Range) -> EngineItem | None:
    """A fragrance meant for this season and occasion, closest to its level of dress."""
    centre = (level.low + level.high) / 2
    fitting = [
        item
        for item in options
        if (not item.seasons or not context.season or context.season in item.seasons)
        and (
            not item.occasion_ids
            or level.occasion is None
            or level.occasion.id in item.occasion_ids
        )
    ]
    if not fitting:
        return None
    return min(fitting, key=lambda item: (abs(item.formality - centre), item.id))


def _diversify(
    candidates: Sequence[_Candidate],
    anchor_ids: set[str],
    count: int,
    config: EngineConfig,
) -> list[_Candidate]:
    """Maximal marginal relevance: each pick trades score against likeness to earlier
    picks. No core piece (other than an anchor) goes in more than half the results while
    there are other options; when there aren't, the rest are still shown."""
    cap = max(1, math.floor(count * config.max_item_share))
    remaining = sorted(candidates, key=lambda c: (-c.breakdown.score, c.key))
    picked: list[_Candidate] = []
    uses: Counter[str] = Counter()
    strict = True
    while remaining and len(picked) < count:
        best: tuple[float, _Candidate] | None = None
        for candidate in remaining:
            if strict and any(
                uses[item_id] >= cap for item_id in candidate.key if item_id not in anchor_ids
            ):
                continue
            likeness = max((_jaccard(candidate.key, other.key) for other in picked), default=0.0)
            value = (
                config.mmr_relevance * candidate.breakdown.score - config.mmr_similarity * likeness
            )
            # remaining is sorted best first, so the first of equal values wins ties.
            if best is None or value > best[0]:
                best = (value, candidate)
        if best is None:
            strict = False
            continue
        picked.append(best[1])
        remaining = [candidate for candidate in remaining if candidate is not best[1]]
        uses.update(item_id for item_id in best[1].key if item_id not in anchor_ids)
    return picked


def _jaccard(a: Sequence[str], b: Sequence[str]) -> float:
    first, second = set(a), set(b)
    return len(first & second) / len(first | second)


def score_outfit(
    wardrobe: Wardrobe,
    context: Context,
    item_ids: Sequence[str],
    config: EngineConfig = DEFAULT,
    pair_cache: dict[tuple[str, str], PairScore] | None = None,
) -> ScoredOutfit | None:
    """Score and explain one given outfit in this context (a swap the person chose); None if
    the pieces aren't the person's or don't make a whole outfit."""
    owned = {item.id: item for item in wardrobe.items if item.owner_id == context.user_id}
    if any(item_id not in owned for item_id in item_ids):
        return None
    pieces = [owned[item_id] for item_id in item_ids]
    check = check_outfit(
        [Piece(key=item.id, slot=item.slot, category_id=item.category_id) for item in pieces],
        wardrobe.templates,
    )
    if not check.complete or check.template_id is None:
        return None
    core = tuple(item for item in pieces if _is_core(item.slot, wardrobe))
    extras = tuple(item for item in pieces if not _is_core(item.slot, wardrobe))
    if context.occasion is not None:
        level = Range(
            context.occasion.formality_min, context.occasion.formality_max, context.occasion
        )
    else:
        levels = [item.formality for item in core]
        level = Range(min(levels), max(levels))
    scorer = Scorer(context, level, PairScores(config, pair_cache), wardrobe.slot_kinds, config)
    breakdown = scorer.score(core, _scored_extras(extras, scorer))
    order = list(wardrobe.slot_kinds)
    return ScoredOutfit(
        template_id=check.template_id,
        items=tuple(
            sorted(
                pieces,
                key=lambda item: (order.index(item.slot) if item.slot in order else 99, item.id),
            )
        ),
        core_ids=_key(core),
        score=round(breakdown.score, 4),
        components=breakdown.components,
        reasons=explain(breakdown, core, scorer, wardrobe.color_names, wardrobe.group_names),
    )
