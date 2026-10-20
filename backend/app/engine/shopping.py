"""What a purchase would add (docs/SHOPPING.md, part 1).

A candidate is treated as if it were already owned. The engine counts the good outfits that
need it, measured like the wardrobe graph (section 11 of the engine doc: the steady wardrobe,
each of the person's occasions in each season), and the difference from the wardrobe as it is
is what the candidate adds. Staples from seed/archetypes.json go through the same analysis
for gaps and the starter capsule. Plain data in, plain data out.

Good outfits for one occasion and season are worth log2(1 + n), counting at most ten, so
going from none to two is worth far more than from nine to eleven, and an occasion and
season that already has ten can't gain. That cap is also what keeps this quick: only the
cells with fewer than ten need the engine run again.
"""

import math
from collections import Counter
from collections.abc import Callable, Iterable, Mapping, Sequence
from dataclasses import dataclass, replace
from functools import lru_cache

from app.engine.color import oklch
from app.engine.config import DEFAULT, EngineConfig
from app.engine.generate import accessory_fit, good_cores
from app.engine.insights import Measures, steady, steady_context
from app.engine.pairs import PairScore, PairScores
from app.engine.reasons import mid, season_phrase, text
from app.engine.scoring import Range, Scorer
from app.engine.types import Context, EngineItem, Occasion, Reason, ReasonKind, Wardrobe

# An occasion id and a season.
Cell = tuple[str, str]
Core = tuple[str, ...]
PairCache = dict[tuple[str, str], PairScore]


@dataclass(frozen=True)
class Found:
    """Good outfits that need at least one of the candidates."""

    # For each (occasion, season) looked at: each outfit's core ids, and the candidates in it.
    cells: Mapping[Cell, Mapping[Core, frozenset[str]]]
    # Each outfit's best score over those cells, and its template.
    best: Mapping[Core, tuple[float, str]]

    def distinct(self) -> set[Core]:
        return {core for outfits in self.cells.values() for core in outfits}


@dataclass(frozen=True)
class Analysis:
    # The candidate's slot kind: core, accessory, or finishing.
    kind: str
    # Owned pieces it pairs well with (P at least pair_edge), best first.
    matches: tuple[tuple[str, float], ...]
    # Distinct good outfits it would make (core), or good outfits it would finish (accessory).
    new_outfits: int
    # New good outfits for each (occasion, season); a core piece's only.
    added: Mapping[Cell, int]
    coverage_gain: float
    # The most alike owned piece in the same slot, and how alike (0 to 1).
    closest_id: str | None
    redundancy: float
    # Owned orphans that would reach two good outfits.
    rescued: tuple[str, ...]
    # A few of the new outfits, best first: template and core ids (the candidate included).
    examples: tuple[tuple[str, Core], ...]


@dataclass(frozen=True)
class Verdict:
    # buy, consider, or skip.
    code: str
    reasons: tuple[Reason, ...]


@dataclass(frozen=True)
class Gap:
    """A staple and what it would add; or, for an occasion no single staple can open,
    several that together make a first good outfit."""

    item_ids: tuple[str, ...]
    coverage_gain: float
    new_outfits: int
    added: Mapping[Cell, int]
    reason: str


@dataclass(frozen=True)
class Step:
    """One step of the starter capsule: a piece, or a whole first outfit."""

    item_ids: tuple[str, ...]
    coverage_gain: float
    # Minor units; None when a piece has no typical spend to go by.
    cost: int | None


@dataclass(frozen=True)
class Split:
    chosen: tuple[str, ...]
    coverage_gain: float
    spent: int
    # True when every affordable subset was compared, False for the greedy pick.
    exhaustive: bool


def value(count: int, config: EngineConfig = DEFAULT) -> float:
    """What good outfits for one occasion and season are worth: each more is worth less, and
    past the cap nothing."""
    return math.log2(1 + min(count, config.coverage_cap))


def coverage_gain(
    before: Mapping[Cell, int], added: Mapping[Cell, int], config: EngineConfig = DEFAULT
) -> float:
    return sum(
        value(count + added.get(cell, 0), config) - value(count, config)
        for cell, count in before.items()
    )


# How alike pieces are.


@lru_cache(maxsize=4096)
def _oklab(hex_value: str) -> tuple[float, float, float]:
    lightness, chroma, hue = oklch(hex_value)
    angle = math.radians(hue)
    return (lightness, chroma * math.cos(angle), chroma * math.sin(angle))


def colour_closeness(a: EngineItem, b: EngineItem, config: EngineConfig = DEFAULT) -> float:
    """1 for the same colour, falling to 0 at colour_closeness_distance apart in OKLab.
    Multicolour (no single colour) is close only to multicolour."""
    if a.color_hex is None or b.color_hex is None:
        return 1.0 if a.color_hex is None and b.color_hex is None else 0.0
    distance = math.dist(_oklab(a.color_hex), _oklab(b.color_hex))
    return max(0.0, 1 - distance / config.colour_closeness_distance)


def similarity(a: EngineItem, b: EngineItem, config: EngineConfig = DEFAULT) -> float:
    """How alike two pieces for the same slot are, 0 to 1 (SHOPPING.md, 1.2)."""
    return (
        config.similar_category * (a.category_id == b.category_id)
        + config.similar_colour * colour_closeness(a, b, config)
        + config.similar_pattern * (a.pattern == b.pattern)
        + config.similar_formality * (1 - abs(a.formality - b.formality) / 4)
    )


def closest(
    candidate: EngineItem, owned: Iterable[EngineItem], config: EngineConfig = DEFAULT
) -> tuple[EngineItem | None, float]:
    """The most alike owned piece in the candidate's slot, and how alike."""
    best: tuple[EngineItem | None, float] = (None, 0.0)
    for item in sorted(owned, key=lambda item: item.id):
        if item.slot != candidate.slot or item.id == candidate.id:
            continue
        alike = similarity(candidate, item, config)
        if alike > best[1]:
            best = (item, alike)
    return best


def matches(
    candidate: EngineItem, owned: Iterable[EngineItem], scorer: Scorer, config: EngineConfig
) -> list[tuple[EngineItem, float]]:
    """Owned pieces in other slots it pairs well with, best first. Fragrance isn't matched,
    and two accessories aren't a pair."""
    kinds = scorer.slot_kinds
    candidate_core = kinds.get(candidate.slot) == "core"
    found = []
    for item in owned:
        kind = kinds.get(item.slot)
        if item.slot == candidate.slot or kind not in ("core", "accessory"):
            continue
        if not candidate_core and kind != "core":
            continue
        score, paired = scorer.pair_value(candidate, item)
        if not score.rejected and paired >= config.pair_edge:
            found.append((item, round(paired, 4)))
    return sorted(found, key=lambda entry: (-entry[1], entry[0].id))


# Counting the outfits that need some of the candidates.


def outfits_with(
    wardrobe: Wardrobe,
    base: Context,
    occasions: Sequence[Occasion],
    seasons: Sequence[str],
    candidates: Sequence[EngineItem],
    config: EngineConfig = DEFAULT,
    pair_cache: PairCache | None = None,
    cells: Iterable[Cell] | None = None,
    each: bool = True,
) -> Found:
    """Good outfits in `wardrobe` (which includes the candidates) that need at least one
    candidate, for each occasion and season (or only `cells`). With `each`, the engine runs
    once per candidate with it fixed in place, which finds every such outfit; without, once
    per cell over everything, which is quicker for a long list of candidates on a small
    wardrobe but, past the beam search's limit, finds only the best."""
    whole = steady(wardrobe)
    context = steady_context(base)
    wanted = set(cells) if cells is not None else None
    ids = {candidate.id for candidate in candidates}
    core = [c for c in candidates if whole.slot_kinds.get(c.slot) == "core"]
    present = {item.id: item for item in whole.items}
    fixed = [present[c.id] for c in core if c.id in present]
    found: dict[Cell, dict[Core, frozenset[str]]] = {}
    best: dict[Core, tuple[float, str]] = {}
    for occasion in occasions:
        for season in seasons:
            cell = (occasion.id, season)
            if wanted is not None and cell not in wanted:
                continue
            here: dict[Core, frozenset[str]] = {}
            here_context = replace(context, occasion=occasion, season=season)
            runs = [(anchor,) for anchor in fixed] if each else [()]
            for anchors in runs:
                outfits = good_cores(
                    whole,
                    here_context,
                    config.versatility_min_score,
                    config,
                    pair_cache,
                    anchors=anchors,
                )
                for outfit in outfits:
                    needs = frozenset(i for i in outfit.core_ids if i in ids)
                    if not needs:
                        continue
                    here[outfit.core_ids] = needs
                    if outfit.score > best.get(outfit.core_ids, (-1.0, ""))[0]:
                        best[outfit.core_ids] = (outfit.score, outfit.template_id)
            found[cell] = here
    return Found(found, best)


def analyse(
    wardrobe: Wardrobe,
    base: Context,
    occasions: Sequence[Occasion],
    seasons: Sequence[str],
    before: Measures,
    candidate: EngineItem,
    config: EngineConfig = DEFAULT,
    pair_cache: PairCache | None = None,
) -> Analysis:
    """What the candidate adds to `wardrobe` (which doesn't include it). `before` is the
    wardrobe measured for the same occasions and seasons (insights.measure)."""
    whole = steady(wardrobe)
    kinds = whole.slot_kinds
    kind = kinds.get(candidate.slot, "finishing")
    owned = [item for item in whole.items if item.owner_id == base.user_id]
    pairs = PairScores(config, pair_cache)
    scorer = Scorer(steady_context(base), Range(1, 5), pairs, kinds, config)
    near, redundancy = closest(candidate, owned, config)
    paired = matches(candidate, owned, scorer, config) if kind != "finishing" else []
    added: dict[Cell, int] = {}
    rescued: list[str] = []
    examples: list[tuple[str, Core]] = []
    new_outfits = 0
    gain = 0.0
    if kind == "core":
        found = outfits_with(
            replace(wardrobe, items=(*wardrobe.items, candidate)),
            base,
            occasions,
            seasons,
            [candidate],
            config,
            pair_cache,
        )
        new = found.distinct()
        new_outfits = len(new)
        added = {cell: len(outfits) for cell, outfits in found.cells.items()}
        gain = coverage_gain(before.coverage, added, config)
        rescued = _rescued(new, found, whole, [*owned, candidate], before, scorer, config)
        ranked = sorted(new, key=lambda core: (-found.best[core][0], core))
        examples = [(found.best[core][1], core) for core in ranked[: config.shopping_examples]]
    elif kind == "accessory":
        templates = {template.id: template for template in whole.templates}
        items = {item.id: item for item in owned}
        finished: list[tuple[float, str, Core]] = []
        for core, template_id in before.good.items():
            if candidate.slot not in templates[template_id].optional:
                continue
            fit = accessory_fit(candidate, [items[i] for i in core], scorer)
            if fit >= config.accessory_min:
                finished.append((fit, template_id, core))
        finished.sort(key=lambda entry: (-entry[0], entry[2]))
        new_outfits = len(finished)
        examples = [
            (template_id, tuple(sorted((*core, candidate.id))))
            for _, template_id, core in finished[: config.shopping_examples]
        ]
    return Analysis(
        kind=kind,
        matches=tuple((item.id, score) for item, score in paired),
        new_outfits=new_outfits,
        added=added,
        coverage_gain=round(gain, 4),
        closest_id=near.id if near else None,
        redundancy=round(redundancy, 4),
        rescued=tuple(rescued),
        examples=tuple(examples),
    )


def _rescued(
    new: set[Core],
    found: Found,
    whole: Wardrobe,
    pieces: Sequence[EngineItem],
    before: Measures,
    scorer: Scorer,
    config: EngineConfig,
) -> list[str]:
    """Owned orphans that the new outfits lift to two good outfits or more. `pieces` are
    the owned items and the candidate."""
    items = {item.id: item for item in pieces}
    templates = {template.id: template for template in whole.templates}
    extra: Counter[str] = Counter()
    for core in new:
        extra.update(core)
    rescued = []
    for orphan_id in before.orphans:
        orphan = items.get(orphan_id)
        if orphan is None:
            continue
        gained = extra[orphan_id]
        if scorer.slot_kinds.get(orphan.slot) == "accessory":
            gained = sum(
                1
                for core in new
                if orphan.slot in templates[found.best[core][1]].optional
                and accessory_fit(orphan, [items[i] for i in core], scorer) >= config.accessory_min
            )
        if before.versatility.get(orphan_id, 0) + gained >= config.orphan_below:
            rescued.append(orphan_id)
    return rescued


# The verdict.


def buy_line(gaps: Sequence[Gap], config: EngineConfig = DEFAULT) -> float | None:
    """The coverage gain a candidate needs for Buy: the top third of what single staples
    would add to this wardrobe. None when there are no staples to compare with."""
    gains = sorted((gap.coverage_gain for gap in gaps if len(gap.item_ids) == 1), reverse=True)
    if not gains:
        return None
    return gains[max(0, math.ceil(len(gains) * config.buy_top_share) - 1)]


def verdict(
    analysis: Analysis,
    candidate: EngineItem,
    names: Mapping[str, str],
    occasions: Sequence[Occasion],
    before: Mapping[Cell, int],
    line: float | None,
    within_budget: bool | None,
    budget_group: str,
    avoided: frozenset[str] = frozenset(),
    config: EngineConfig = DEFAULT,
) -> Verdict:
    """Buy, Consider, or Skip, with the reasons behind it (SHOPPING.md, 1.3). `names` gives
    owned pieces' names; `within_budget` is None when there's no price or usual spend to
    compare."""
    positive: list[Reason] = []
    caution: list[Reason] = []

    def add(into: list[Reason], code: str, strength: float, **values: str) -> None:
        kind: ReasonKind = "positive" if into is positive else "caution"
        into.append(Reason(code, kind, strength, text(code, **values)))

    seasons = list(dict.fromkeys(season for _, season in before))
    near = names.get(analysis.closest_id or "", "")
    duplicate = analysis.redundancy >= config.duplicate_at
    if duplicate:
        add(caution, "verdict.duplicate", 1.0, a=mid(near))
    elif analysis.redundancy >= config.buy_similarity_below:
        add(caution, "verdict.similar", analysis.redundancy, a=mid(near))
    if candidate.color_family in avoided:
        add(caution, "verdict.avoided", 0.9)

    few = analysis.new_outfits < config.min_new_outfits
    if analysis.kind == "core":
        if analysis.new_outfits == 0:
            add(caution, "verdict.no_outfits", 0.95)
            if occasions and all(
                candidate.formality <= o.formality_min - config.occasion_filter_steps
                or candidate.formality >= o.formality_max + config.occasion_filter_steps
                for o in occasions
            ):
                add(caution, "rescue.occasions", 0.9)
        elif analysis.new_outfits == 1:
            add(caution, "verdict.one_outfit", 0.9)
        else:
            add(positive, "verdict.outfits", 0.6, count=str(analysis.new_outfits))
        opened = [cell for cell, n in analysis.added.items() if n and not before.get(cell)]
        short = [
            cell
            for cell, n in analysis.added.items()
            if n and 0 < before.get(cell, 0) < config.coverage_cap
        ]
        if opened:
            add(positive, "verdict.opens", 0.9, cells=_cells_phrase(opened, occasions, seasons))
        if short:
            add(positive, "verdict.short", 0.8, cells=_cells_phrase(short, occasions, seasons))
        if analysis.new_outfits and not opened and not short:
            add(caution, "verdict.plenty", 0.5)
        if analysis.rescued:
            listed = [mid(names.get(i, "")) for i in analysis.rescued if names.get(i)]
            add(positive, "verdict.rescues", 0.7, names=_listing(listed, 2))
    elif analysis.kind == "accessory":
        if analysis.new_outfits == 0:
            add(caution, "verdict.finishes_none", 0.95)
        elif analysis.new_outfits == 1:
            add(caution, "verdict.finishes_one", 0.9)
        else:
            add(positive, "verdict.finishes", 0.6, count=str(analysis.new_outfits))
    if within_budget is False:
        add(caution, "verdict.over_budget", 0.6, group=mid(budget_group))

    if analysis.kind == "finishing":
        code = "skip" if duplicate else "consider"
        add(caution, "verdict.finishing", 0.1)
    elif duplicate or few:
        code = "skip"
    elif analysis.kind == "accessory":
        code = "consider"
        add(caution, "verdict.accessory", 0.1)
    elif (
        line is not None
        and analysis.coverage_gain > 0
        and analysis.coverage_gain >= line
        and analysis.redundancy < config.buy_similarity_below
        and within_budget is not False
    ):
        code = "buy"
        add(positive, "verdict.top_third", 0.5)
    else:
        code = "consider"
    good = sorted(positive, key=lambda reason: -reason.strength)
    bad = sorted(caution, key=lambda reason: -reason.strength)
    # Lead with what decided it.
    return Verdict(code, tuple(good + bad if code == "buy" else bad + good))


def _cells_phrase(
    cells: Sequence[Cell], occasions: Sequence[Occasion], seasons: Sequence[str]
) -> str:
    """ "work in summer and the monsoon, and college in every season", in the order of the
    occasions and seasons given."""
    order = [occasion.id for occasion in occasions]
    names = {occasion.id: occasion.name for occasion in occasions}

    def place(cell: Cell) -> tuple[int, int]:
        occasion_id, season = cell
        return (
            order.index(occasion_id) if occasion_id in order else 99,
            seasons.index(season) if season in seasons else 99,
        )

    by_occasion: dict[str, list[str]] = {}
    for occasion_id, season in sorted(cells, key=place):
        by_occasion.setdefault(occasion_id, []).append(season)
    parts = [
        f"{mid(names.get(occasion_id, occasion_id))} in "
        + (
            "every season"
            if len(seasons) > 1 and set(listed) >= set(seasons)
            else _listing([season_phrase(season) for season in listed], 4)
        )
        for occasion_id, listed in by_occasion.items()
    ]
    return _listing(parts, 3, separator=", and " if len(parts) > 1 else " and ")


def _listing(parts: Sequence[str], most: int, separator: str = " and ") -> str:
    shown = list(parts[:most])
    rest = len(parts) - len(shown)
    if rest:
        shown.append(f"{rest} more")
    if len(shown) == 1:
        return shown[0]
    return ", ".join(shown[:-1]) + separator + shown[-1]


# Gaps and the starter capsule.


def gaps(
    wardrobe: Wardrobe,
    base: Context,
    occasions: Sequence[Occasion],
    seasons: Sequence[str],
    before: Measures,
    staples: Sequence[EngineItem],
    config: EngineConfig = DEFAULT,
    pair_cache: PairCache | None = None,
) -> list[Gap]:
    """What would add the most, most first (SHOPPING.md, 1.4): every core staple that doesn't
    duplicate something owned, with what it would add on its own. Only occasions and seasons
    short of the cap can gain. An occasion and season with no good outfit that no single
    staple can open (an interview needs a shirt, trousers, and shoes) gets the fewest
    staples that together make one."""
    whole = steady(wardrobe)
    owned = [item for item in whole.items if item.owner_id == base.user_id]
    short = [cell for cell, n in before.coverage.items() if n < config.coverage_cap]
    pool = [
        staple
        for staple in staples
        if whole.slot_kinds.get(staple.slot) == "core"
        and closest(staple, owned, config)[1] < config.duplicate_at
    ]
    found: list[Gap] = []
    opened: set[Cell] = set()
    for staple in pool:
        added: dict[Cell, int] = {}
        new = 0
        if short:
            outfits = outfits_with(
                replace(wardrobe, items=(*wardrobe.items, staple)),
                base,
                occasions,
                seasons,
                [staple],
                config,
                pair_cache,
                cells=short,
            )
            added = {cell: len(cores) for cell, cores in outfits.cells.items() if cores}
            new = len(outfits.distinct())
            opened.update(added)
        gain = coverage_gain(before.coverage, added, config)
        found.append(
            Gap(
                (staple.id,),
                round(gain, 4),
                new,
                added,
                _gap_reason(new, list(added), occasions, seasons),
            )
        )
    empty = [cell for cell in short if not before.coverage[cell] and cell not in opened]
    bundles = _first_outfits(
        wardrobe, base, occasions, seasons, before, pool, empty, config, pair_cache
    )
    return sorted(
        [*bundles, *found],
        key=lambda gap: (-gap.coverage_gain / len(gap.item_ids), -gap.new_outfits, gap.item_ids),
    )


def _first_outfits(
    wardrobe: Wardrobe,
    base: Context,
    occasions: Sequence[Occasion],
    seasons: Sequence[str],
    before: Measures,
    pool: Sequence[EngineItem],
    empty: Sequence[Cell],
    config: EngineConfig,
    pair_cache: PairCache | None,
) -> list[Gap]:
    """For each occasion and season with nothing good, the fewest staples that together make
    a good outfit there (with what's owned), preferring sets that open the most of them."""
    if not empty or not pool:
        return []
    found = outfits_with(
        replace(wardrobe, items=(*wardrobe.items, *pool)),
        base,
        occasions,
        seasons,
        pool,
        config,
        pair_cache,
        cells=empty,
        each=False,
    )
    reach: dict[frozenset[str], set[Cell]] = {}
    best: dict[frozenset[str], float] = {}
    for cell, outfits in found.cells.items():
        for core, needs in outfits.items():
            reach.setdefault(needs, set()).add(cell)
            best[needs] = max(best.get(needs, 0.0), found.best[core][0])
    bundles: list[Gap] = []
    left = set(empty)
    have: frozenset[str] = frozenset()
    counts = dict(before.coverage)
    while left:
        options = [needs for needs, cells in reach.items() if cells & left]
        if not options:
            break
        pick = min(
            options,
            key=lambda needs: (
                len(needs - have),
                -len(reach[needs] & left),
                -best[needs],
                sorted(needs),
            ),
        )
        now = have | pick
        added = {}
        for cell, outfits in found.cells.items():
            more = sum(1 for needs in outfits.values() if needs <= now and not needs <= have)
            if more:
                added[cell] = more
        code = "gap.with_above" if pick & have else "gap.together"
        bundles.append(
            Gap(
                tuple(sorted(pick - have)),
                round(coverage_gain(counts, added, config), 4),
                sum(added.values()),
                added,
                text(code, cells=_cells_phrase(list(added), occasions, seasons)),
            )
        )
        for cell, more in added.items():
            counts[cell] += more
        left -= set(added)
        have = now
    return bundles


def _gap_reason(
    new: int, cells: Sequence[Cell], occasions: Sequence[Occasion], seasons: Sequence[str]
) -> str:
    if not new:
        return text("gap.nothing")
    code = "gap.one" if new == 1 else "gap.adds"
    return text(code, count=str(new), cells=_cells_phrase(cells, occasions, seasons))


def capsule(
    wardrobe: Wardrobe,
    base: Context,
    occasions: Sequence[Occasion],
    seasons: Sequence[str],
    before: Measures,
    staples: Sequence[EngineItem],
    costs: Mapping[str, int | None],
    budget: int | None,
    config: EngineConfig = DEFAULT,
    pair_cache: PairCache | None = None,
) -> list[Step]:
    """A staged shopping plan for a small wardrobe (SHOPPING.md, 1.5): one staple at a time,
    each the one adding the most coverage given everything before it, within the budget.
    When no single piece adds a good outfit (an empty wardrobe, or one without shoes), the
    step is a whole outfit instead, the one adding the most per piece."""
    whole = steady(wardrobe)
    owned = [item for item in whole.items if item.owner_id == base.user_id]
    pool = [
        staple
        for staple in staples
        if whole.slot_kinds.get(staple.slot) == "core"
        and closest(staple, owned, config)[1] < config.duplicate_at
    ]
    short = [cell for cell, n in before.coverage.items() if n < config.coverage_cap]
    if not pool or not short:
        return []
    found = outfits_with(
        replace(wardrobe, items=(*wardrobe.items, *pool)),
        base,
        occasions,
        seasons,
        pool,
        config,
        pair_cache,
        cells=short,
        each=False,
    )
    bit = {staple.id: 1 << index for index, staple in enumerate(pool)}
    masks = _masks(found, bit)
    counts = {cell: before.coverage[cell] for cell in short}
    chosen = 0
    spent = 0
    steps: list[Step] = []

    def gain(of: int) -> float:
        return sum(
            value(counts[cell] + _covered(masks[cell], of), config) - value(counts[cell], config)
            for cell in short
        )

    def cost(ids: Sequence[str]) -> int | None:
        prices = [costs.get(i) for i in ids]
        return None if any(p is None for p in prices) else sum(p or 0 for p in prices)

    def affordable(ids: Sequence[str]) -> bool:
        if budget is None:
            return True
        price = cost(ids)
        return price is not None and spent + price <= budget

    while bin(chosen).count("1") < config.capsule_limit:
        now = gain(chosen)
        options: list[tuple[float, int, tuple[str, ...]]] = []
        for staple in pool:
            if chosen & bit[staple.id] or not affordable([staple.id]):
                continue
            more = gain(chosen | bit[staple.id]) - now
            if more > 1e-9:
                options.append((more, cost([staple.id]) or 0, (staple.id,)))
        if not options:
            options = _bundles(masks, chosen, bit, pool, gain, now, cost, affordable, config)
        if not options:
            break
        options.sort(key=lambda o: (-o[0] / len(o[2]), o[1], len(o[2]), o[2]))
        more, _, ids = options[0]
        if bin(chosen).count("1") + len(ids) > config.capsule_limit:
            break
        for item_id in ids:
            chosen |= bit[item_id]
        price = cost(ids)
        spent += price or 0
        steps.append(Step(ids, round(more, 4), price))
    return steps


def _bundles(
    masks: Mapping[Cell, Counter[int]],
    chosen: int,
    bit: Mapping[str, int],
    pool: Sequence[EngineItem],
    gain: Callable[[int], float],
    now: float,
    cost: Callable[[Sequence[str]], int | None],
    affordable: Callable[[Sequence[str]], bool],
    config: EngineConfig,
) -> list[tuple[float, int, tuple[str, ...]]]:
    """Whole outfits to add at once, from the outfits good in the most occasions and
    seasons."""
    spread: Counter[int] = Counter()
    for counted in masks.values():
        for mask in counted:
            if mask & ~chosen:
                spread[mask | chosen] += 1
    ranked = sorted(spread, key=lambda mask: (-spread[mask], bin(mask).count("1"), mask))
    options = []
    for mask in ranked[: config.capsule_bundles]:
        ids = tuple(sorted(s.id for s in pool if mask & ~chosen & bit[s.id]))
        if not affordable(ids):
            continue
        more = gain(mask) - now
        if more > 1e-9:
            options.append((more, cost(ids) or 0, ids))
    return options


def _masks(found: Found, bit: Mapping[str, int]) -> dict[Cell, Counter[int]]:
    """For each cell, how many good outfits need each set of candidates (as a bit mask)."""
    masks: dict[Cell, Counter[int]] = {}
    for cell, outfits in found.cells.items():
        counted: Counter[int] = Counter()
        for needs in outfits.values():
            mask = 0
            for item_id in needs:
                mask |= bit[item_id]
            counted[mask] += 1
        masks[cell] = counted
    return masks


def _covered(counted: Counter[int], chosen: int) -> int:
    return sum(n for mask, n in counted.items() if not mask & ~chosen)


# The budget split.


def budget_split(
    wardrobe: Wardrobe,
    base: Context,
    occasions: Sequence[Occasion],
    seasons: Sequence[str],
    before: Measures,
    candidates: Sequence[tuple[EngineItem, int]],
    budget: int,
    config: EngineConfig = DEFAULT,
    pair_cache: PairCache | None = None,
) -> Split:
    """The candidates to buy for the most coverage within the budget (SHOPPING.md, 1.6).
    Candidates are judged together, since a shirt and trousers bought together make outfits
    neither makes alone: up to split_exhaustive_up_to of them, every affordable subset is
    compared; past that, greedy by gain per rupee, kept only if it beats the best single
    piece."""
    short = [cell for cell, n in before.coverage.items() if n < config.coverage_cap]
    items = [item for item, _ in candidates]
    prices = [price for _, price in candidates]
    masks: dict[Cell, Counter[int]] = {cell: Counter() for cell in short}
    if short and items:
        found = outfits_with(
            replace(wardrobe, items=(*wardrobe.items, *items)),
            base,
            occasions,
            seasons,
            items,
            config,
            pair_cache,
            cells=short,
        )
        masks = _masks(found, {item.id: 1 << i for i, item in enumerate(items)})
    counts = {cell: before.coverage[cell] for cell in short}
    if len(items) <= config.split_exhaustive_up_to:
        chosen, gain = best_subset(masks, counts, prices, budget, config)
        exhaustive = True
    else:
        chosen, gain = greedy_subset(masks, counts, prices, budget, config)
        exhaustive = False
    picked = [i for i in range(len(items)) if chosen >> i & 1]
    return Split(
        chosen=tuple(items[i].id for i in picked),
        coverage_gain=round(gain, 4),
        spent=sum(prices[i] for i in picked),
        exhaustive=exhaustive,
    )


def best_subset(
    masks: Mapping[Cell, Counter[int]],
    before: Mapping[Cell, int],
    prices: Sequence[int],
    budget: int,
    config: EngineConfig = DEFAULT,
) -> tuple[int, float]:
    """The affordable subset (as a bit mask) with the largest coverage gain. Ties go to the
    cheaper, then the smaller, then the lower mask. For each cell, the outfits every subset
    makes are summed over its sub-masks in one pass (a sum-over-subsets transform), so all
    2^n subsets cost n * 2^n steps rather than a recount each."""
    n = len(prices)
    size = 1 << n
    cost = [0] * size
    for subset in range(1, size):
        low = subset & -subset
        cost[subset] = cost[subset ^ low] + prices[low.bit_length() - 1]
    gains = [0.0] * size
    for cell, counted in masks.items():
        made = [0] * size
        for mask, count in counted.items():
            made[mask] += count
        for i in range(n):
            step = 1 << i
            for subset in range(size):
                if subset & step:
                    made[subset] += made[subset ^ step]
        start = value(before[cell], config)
        for subset in range(size):
            if made[subset]:
                gains[subset] += value(before[cell] + made[subset], config) - start
    best = 0
    for subset in range(size):
        if cost[subset] > budget:
            continue
        if (gains[subset], -cost[subset], -bin(subset).count("1"), -subset) > (
            gains[best],
            -cost[best],
            -bin(best).count("1"),
            -best,
        ):
            best = subset
    return best, gains[best]


def greedy_subset(
    masks: Mapping[Cell, Counter[int]],
    before: Mapping[Cell, int],
    prices: Sequence[int],
    budget: int,
    config: EngineConfig = DEFAULT,
) -> tuple[int, float]:
    """Add what gives the most gain per rupee until nothing affordable adds anything: one
    piece, or the missing pieces of an outfit that needs several (alone, each of those adds
    nothing). Then keep whichever is better, that or the best single piece. Because pieces
    make outfits together, this has no guarantee; tests compare it with best_subset."""

    def gain(of: int) -> float:
        return sum(
            value(before[cell] + _covered(counted, of), config) - value(before[cell], config)
            for cell, counted in masks.items()
        )

    def price_of(bits: int) -> int:
        return sum(price for i, price in enumerate(prices) if bits >> i & 1)

    outfits = {mask for counted in masks.values() for mask in counted}
    chosen = 0
    spent = 0
    now = 0.0
    while True:
        steps = {1 << i for i in range(len(prices))} | {mask & ~chosen for mask in outfits}
        options = []
        for step in steps:
            if not step or step & chosen:
                continue
            cost = price_of(step)
            if spent + cost > budget:
                continue
            more = gain(chosen | step) - now
            if more > 1e-9:
                options.append((more / max(cost, 1), -cost, -step))
        if not options:
            break
        _, _, step = max(options)
        chosen |= -step
        spent += price_of(-step)
        now = gain(chosen)
    single = max(
        ((gain(1 << i), -price, -i) for i, price in enumerate(prices) if price <= budget),
        default=None,
    )
    if single is not None and single[0] > now + 1e-9:
        return 1 << -single[2], single[0]
    return chosen, now
