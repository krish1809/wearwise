"""Planning a week (docs/ENGINE.md, section 12): an outfit per day that respects the laundry,
doesn't repeat a top too soon, and keeps locked days as they are.

Each day's candidates come from the same engine as suggestions (rank(), best first). A beam
search then walks the days in order, simulating wears so nothing is planned past its wash
limit, and keeps the best partial weeks. The result is never worse than picking the best valid
outfit day by day (the greedy plan), because both are computed and the better one returned.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field, replace
from datetime import date

from app.engine.config import DEFAULT, ENGINE_VERSION, EngineConfig
from app.engine.generate import rank
from app.engine.pairs import PairScore
from app.engine.reasons import text
from app.engine.types import (
    Context,
    EngineItem,
    Missing,
    Occasion,
    ScoredOutfit,
    Suggestions,
    Wardrobe,
    Weather,
)


@dataclass(frozen=True)
class Locked:
    """An outfit kept as it is: its pieces, and which of them are core."""

    item_ids: tuple[str, ...]
    core_ids: tuple[str, ...]


@dataclass(frozen=True)
class DaySpec:
    day: date
    occasion: Occasion | None
    weather: Weather | None
    season: str
    locked: Locked | None = None


@dataclass(frozen=True)
class DayPlan:
    day: date
    # None for a locked day (it keeps its outfit) and for a day nothing could fill.
    outfit: ScoredOutfit | None
    locked: bool
    missing: tuple[Missing, ...] = ()


@dataclass(frozen=True)
class WeekPlan:
    days: tuple[DayPlan, ...]
    objective: float
    engine_version: str = ENGINE_VERSION


@dataclass(frozen=True)
class Worn:
    """What a day puts on: every piece, and the core ones (for checking a week's rules)."""

    item_ids: tuple[str, ...]
    core_ids: tuple[str, ...]


@dataclass
class _State:
    """The simulated week so far."""

    wears: dict[str, int]
    # Day index each top was last planned.
    last_top: dict[str, int] = field(default_factory=dict)
    # The footwear of the previous days, most recent last.
    shoes: list[str | None] = field(default_factory=list)
    used: set[str] = field(default_factory=set)
    families: set[str] = field(default_factory=set)

    def copy(self) -> _State:
        return _State(
            dict(self.wears),
            dict(self.last_top),
            list(self.shoes),
            set(self.used),
            set(self.families),
        )


@dataclass(frozen=True)
class _Partial:
    choices: tuple[ScoredOutfit | None, ...]
    state: _State
    # Sum of the days' scores, less repeat penalties.
    total: float

    def value(self, config: EngineConfig) -> float:
        return self.total + config.plan_variety_bonus * len(self.state.families)

    def key(self) -> tuple[tuple[str, ...], ...]:
        return tuple(choice.core_ids if choice else () for choice in self.choices)


def plan_week(
    wardrobe: Wardrobe,
    base: Context,
    specs: Sequence[DaySpec],
    config: EngineConfig = DEFAULT,
    pair_cache: dict[tuple[str, str], PairScore] | None = None,
    laundry_weekday: int | None = None,
) -> WeekPlan:
    """The best week found: a beam search over days, never worse than the greedy plan."""
    items = {item.id: item for item in wardrobe.items if item.owner_id == base.user_id}
    pools, missing = _pools(wardrobe, base, specs, config, pair_cache, laundry_weekday)
    beam = _search(specs, pools, items, config, laundry_weekday, config.plan_beam_width)
    greedy = _search(specs, pools, items, config, laundry_weekday, 1, per_day=1)
    best = beam if beam.value(config) >= greedy.value(config) else greedy
    days = []
    for index, spec in enumerate(specs):
        chosen = best.choices[index]
        if spec.locked is not None:
            days.append(DayPlan(spec.day, None, locked=True))
        elif chosen is None:
            days.append(
                DayPlan(spec.day, None, locked=False, missing=_why(missing[index], pools[index]))
            )
        else:
            days.append(DayPlan(spec.day, chosen, locked=False))
    return WeekPlan(days=tuple(days), objective=round(best.value(config), 4))


def alternatives(
    wardrobe: Wardrobe,
    base: Context,
    specs: Sequence[DaySpec],
    target: date,
    count: int,
    config: EngineConfig = DEFAULT,
    pair_cache: dict[tuple[str, str], PairScore] | None = None,
    laundry_weekday: int | None = None,
) -> list[ScoredOutfit]:
    """Other outfits for one day that keep the whole week within the rules, with every other
    day as planned (pass them as locked)."""
    index = next(i for i, spec in enumerate(specs) if spec.day == target)
    items = {item.id: item for item in wardrobe.items if item.owner_id == base.user_id}
    pool = _day_pool(wardrobe, base, specs[index], config, pair_cache, laundry_weekday, specs)
    worn = [_locked_worn(spec) for spec in specs]
    # The week as it stands up to that day, to know which accessories are due a wash by then.
    before = _initial(items)
    for earlier in range(index):
        if laundry_weekday is not None and specs[earlier].day.weekday() == laundry_weekday:
            _wash(before, items)
        _apply(before, worn[earlier], earlier, items)
    if laundry_weekday is not None and specs[index].day.weekday() == laundry_weekday:
        _wash(before, items)
    found = []
    for pooled in pool.outfits:
        outfit = _without_due_extras(pooled, before)
        week = list(worn)
        week[index] = Worn(tuple(item.id for item in outfit.items), outfit.core_ids)
        if not violations(week, [spec.day for spec in specs], items, config, laundry_weekday):
            found.append(outfit)
        if len(found) == count:
            break
    return found


def violations(
    week: Sequence[Worn | None],
    days: Sequence[date],
    items: Mapping[str, EngineItem],
    config: EngineConfig = DEFAULT,
    laundry_weekday: int | None = None,
) -> list[str]:
    """Every broken rule in a planned week, in words; empty when the week is fine."""
    state = _initial(items)
    found = []
    for index, worn in enumerate(week):
        if laundry_weekday is not None and days[index].weekday() == laundry_weekday:
            _wash(state, items)
        if worn is not None:
            problem = _invalid(worn, index, state, items, config)
            if problem:
                found.append(f"{days[index].isoformat()}: {problem}")
        _apply(state, worn, index, items)
    return found


def _pools(
    wardrobe: Wardrobe,
    base: Context,
    specs: Sequence[DaySpec],
    config: EngineConfig,
    pair_cache: dict[tuple[str, str], PairScore] | None,
    laundry_weekday: int | None,
) -> tuple[list[tuple[ScoredOutfit, ...]], list[tuple[Missing, ...]]]:
    pools: list[tuple[ScoredOutfit, ...]] = []
    missing: list[tuple[Missing, ...]] = []
    for spec in specs:
        if spec.locked is not None:
            pools.append(())
            missing.append(())
            continue
        if spec.occasion is None:
            pools.append(())
            missing.append((Missing("", "", "plan.no_occasion", text("plan.no_occasion")),))
            continue
        ranked = _day_pool(wardrobe, base, spec, config, pair_cache, laundry_weekday, specs)
        pools.append(ranked.outfits)
        missing.append(ranked.missing)
    return pools, missing


def _day_pool(
    wardrobe: Wardrobe,
    base: Context,
    spec: DaySpec,
    config: EngineConfig,
    pair_cache: dict[tuple[str, str], PairScore] | None,
    laundry_weekday: int | None,
    specs: Sequence[DaySpec],
) -> Suggestions:
    after_laundry = laundry_weekday is not None and any(
        other.day <= spec.day and other.day.weekday() == laundry_weekday for other in specs
    )
    context = replace(
        base,
        today=spec.day,
        occasion=spec.occasion,
        weather=spec.weather,
        season=spec.season,
        anchor_ids=(),
        exclude_ids=frozenset(),
        count=config.plan_pool,
    )
    return rank(
        _washed(wardrobe) if after_laundry else wardrobe,
        context,
        config,
        pair_cache,
        item_cap=config.plan_pool_item_cap,
    )


def _washed(wardrobe: Wardrobe) -> Wardrobe:
    """The wardrobe after laundry day: the laundry is back and nothing is due a wash."""
    return replace(
        wardrobe,
        items=tuple(
            replace(item, status="available", wears_since_wash=0)
            if item.status in ("available", "laundry")
            else item
            for item in wardrobe.items
        ),
    )


def _search(
    specs: Sequence[DaySpec],
    pools: Sequence[Sequence[ScoredOutfit]],
    items: Mapping[str, EngineItem],
    config: EngineConfig,
    laundry_weekday: int | None,
    width: int,
    per_day: int | None = None,
) -> _Partial:
    per_day = per_day or config.plan_per_day
    # Whether any later day is locked: then each choice must also leave those days valid.
    locked_ahead = [
        any(later.locked is not None for later in specs[index + 1 :]) for index in range(len(specs))
    ]
    partials = [_Partial((), _initial(items), 0.0)]
    for index, spec in enumerate(specs):
        grown: list[_Partial] = []
        for partial in partials:
            state = partial.state
            if laundry_weekday is not None and spec.day.weekday() == laundry_weekday:
                state = state.copy()
                _wash(state, items)
            if spec.locked is not None:
                after = state.copy()
                _apply(after, _locked_worn(spec), index, items)
                grown.append(_Partial((*partial.choices, None), after, partial.total))
                continue
            options = []
            baseline = (
                _locked_violations(state, None, index, specs, items, config, laundry_weekday)
                if locked_ahead[index]
                else 0
            )
            for pooled in pools[index]:
                outfit = _without_due_extras(pooled, state)
                worn = Worn(tuple(item.id for item in outfit.items), outfit.core_ids)
                if _invalid(worn, index, state, items, config) is not None:
                    continue
                if (
                    locked_ahead[index]
                    and _locked_violations(
                        state, worn, index, specs, items, config, laundry_weekday
                    )
                    > baseline
                ):
                    continue
                options.append((outfit, worn))
                if len(options) == per_day:
                    break
            if not options:
                after = state.copy()
                _apply(after, None, index, items)
                grown.append(_Partial((*partial.choices, None), after, partial.total))
            for outfit, worn in options:
                repeats = sum(1 for item_id in outfit.core_ids if item_id in state.used)
                after = state.copy()
                _apply(after, worn, index, items)
                grown.append(
                    _Partial(
                        (*partial.choices, outfit),
                        after,
                        partial.total + outfit.score - config.plan_repeat_penalty * repeats,
                    )
                )
        grown.sort(key=lambda p: (-p.value(config), p.key()))
        partials = grown[:width]
    return partials[0]


def _locked_violations(
    state: _State,
    worn: Worn | None,
    index: int,
    specs: Sequence[DaySpec],
    items: Mapping[str, EngineItem],
    config: EngineConfig,
    laundry_weekday: int | None,
) -> int:
    """How many locked days later in the week would break the rules if this day wore `worn`
    (later unlocked days left empty for now; each is checked when its turn comes)."""
    ahead = state.copy()
    _apply(ahead, worn, index, items)
    broken = 0
    for later in range(index + 1, len(specs)):
        spec = specs[later]
        if laundry_weekday is not None and spec.day.weekday() == laundry_weekday:
            _wash(ahead, items)
        locked = _locked_worn(spec)
        if locked is not None and _invalid(locked, later, ahead, items, config) is not None:
            broken += 1
        _apply(ahead, locked, later, items)
    return broken


def _without_due_extras(outfit: ScoredOutfit, state: _State) -> ScoredOutfit:
    """The outfit without any accessory that's due a wash by then (socks, mostly): a
    finishing touch comes off rather than ruling the outfit out."""
    core = set(outfit.core_ids)
    kept = tuple(
        item
        for item in outfit.items
        if item.id in core
        or item.wears_before_wash is None
        or state.wears.get(item.id, 0) < item.wears_before_wash
    )
    return outfit if len(kept) == len(outfit.items) else replace(outfit, items=kept)


def _initial(items: Mapping[str, EngineItem]) -> _State:
    return _State(wears={item_id: item.wears_since_wash for item_id, item in items.items()})


def _wash(state: _State, items: Mapping[str, EngineItem]) -> None:
    for item_id in state.wears:
        state.wears[item_id] = 0


def _invalid(
    worn: Worn,
    index: int,
    state: _State,
    items: Mapping[str, EngineItem],
    config: EngineConfig,
) -> str | None:
    """Why this outfit can't be worn on this day of the simulated week, or None."""
    for item_id in worn.item_ids:
        item = items.get(item_id)
        if item is None:
            continue
        limit = item.wears_before_wash
        if limit is not None and state.wears.get(item_id, 0) >= limit:
            return f"{item.name} is due a wash"
        last = state.last_top.get(item_id) if item.slot == "top" else None
        if last is not None and index - last < config.plan_top_gap_days:
            return f"{item.name} was worn within {config.plan_top_gap_days} days"
        if item.slot == "footwear":
            streak = config.plan_footwear_streak
            recent = state.shoes[-streak:]
            if len(recent) == streak and all(shoe == item_id for shoe in recent):
                return f"{item.name} would be worn {streak + 1} days running"
    return None


def _apply(state: _State, worn: Worn | None, index: int, items: Mapping[str, EngineItem]) -> None:
    shoes = None
    if worn is not None:
        for item_id in worn.item_ids:
            state.wears[item_id] = state.wears.get(item_id, 0) + 1
            item = items.get(item_id)
            if item is None:
                continue
            if item.slot == "top":
                state.last_top[item_id] = index
            if item.slot == "footwear":
                shoes = item_id
        for item_id in worn.core_ids:
            state.used.add(item_id)
            item = items.get(item_id)
            if item is not None:
                state.families.add(item.color_family)
    state.shoes.append(shoes)


def _locked_worn(spec: DaySpec) -> Worn | None:
    if spec.locked is None:
        return None
    return Worn(spec.locked.item_ids, spec.locked.core_ids)


def _why(missing: tuple[Missing, ...], pool: Sequence[ScoredOutfit]) -> tuple[Missing, ...]:
    """Why a day stayed empty: the engine's reason, or the week's rules if outfits existed."""
    if not pool and missing:
        return missing
    return (Missing("", "", "plan.blocked", text("plan.blocked")),)
