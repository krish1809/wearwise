"""A packing list (docs/ENGINE.md, section 13): a compact set of items that gives every day of
a trip an outfit scoring 0.65 or more, within the day's level of dress when the wardrobe
allows, with no laundry on the way.

Greedy, so "a compact list", not "the smallest possible": start empty; repeatedly add the
outfit that covers the most still-uncovered days for the fewest new pieces; then try leaving
each piece out, least useful first, and keep the removal if every day is still covered. Days
are then given outfits from the packed pieces, never wearing anything more often than it can
go between washes.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from datetime import date

from app.engine.config import DEFAULT, ENGINE_VERSION, EngineConfig
from app.engine.generate import rank
from app.engine.pairs import PairScore
from app.engine.reasons import text
from app.engine.types import Context, EngineItem, Missing, Occasion, ScoredOutfit, Wardrobe, Weather


@dataclass(frozen=True)
class TripDay:
    day: date
    occasion: Occasion
    weather: Weather | None
    season: str


@dataclass(frozen=True)
class PackedDay:
    day: date
    outfit: ScoredOutfit | None
    missing: tuple[Missing, ...] = ()


@dataclass(frozen=True)
class Packing:
    # Every item to pack: core pieces, and the accessories the day outfits use.
    item_ids: tuple[str, ...]
    days: tuple[PackedDay, ...]
    engine_version: str = ENGINE_VERSION


def pack(
    wardrobe: Wardrobe,
    base: Context,
    days: Sequence[TripDay],
    config: EngineConfig = DEFAULT,
    pair_cache: dict[tuple[str, str], PairScore] | None = None,
) -> Packing:
    items = {item.id: item for item in wardrobe.items if item.owner_id == base.user_id}
    pools: list[list[ScoredOutfit]] = []
    missing: list[tuple[Missing, ...]] = []
    for day in days:
        context = replace(
            base,
            today=day.day,
            occasion=day.occasion,
            weather=day.weather,
            season=day.season,
            anchor_ids=(),
            exclude_ids=frozenset(),
            count=config.plan_pool,
        )
        ranked = rank(wardrobe, context, config, pair_cache, item_cap=config.plan_pool_item_cap)
        good = [outfit for outfit in ranked.outfits if outfit.score >= config.packing_min_score]
        # A day is dressed for its occasion when it can be: a wedding gets the outfits within
        # its level of dress, even if a casual one scores well enough.
        fitting = [outfit for outfit in good if outfit.components.occasion >= 1]
        good = fitting or good
        pools.append(good)
        missing.append(
            ranked.missing
            if not ranked.outfits
            else ()
            if good
            else (Missing("", "", "packing.no_good_outfit", text("packing.no_good_outfit")),)
        )

    chosen = _cover(pools, items)
    chosen = _prune(chosen, pools, items)
    assigned = _assign(chosen, pools, items)
    packed_days = []
    used: set[str] = set()
    for index, day in enumerate(days):
        outfit = assigned[index]
        if outfit is not None:
            used.update(item.id for item in outfit.items)
            packed_days.append(PackedDay(day.day, outfit))
        else:
            reason = missing[index] or (
                Missing("", "", "packing.not_enough", text("packing.not_enough")),
            )
            packed_days.append(PackedDay(day.day, None, reason))
    order = list(wardrobe.slot_kinds)
    return Packing(
        item_ids=tuple(
            sorted(
                used,
                key=lambda item_id: (
                    order.index(items[item_id].slot) if items[item_id].slot in order else 99,
                    item_id,
                ),
            )
        ),
        days=tuple(packed_days),
    )


# Each greedy step tries this many of an uncovered day's best outfits.
COVER_TRIES = 15


def _core(outfit: ScoredOutfit) -> frozenset[str]:
    return frozenset(outfit.core_ids)


def _cover(pools: Sequence[Sequence[ScoredOutfit]], items: Mapping[str, EngineItem]) -> set[str]:
    """Greedy cover: each step adds the outfit that lets the most extra days be dressed (within
    every piece's wears before a wash) per new piece."""
    chosen: set[str] = set()
    coverable = sum(1 for pool in pools if pool)
    current = 0
    while current < coverable:
        assigned = _assign(chosen, pools, items)
        uncovered = [i for i, pool in enumerate(pools) if pool and assigned[i] is None]
        best: tuple[float, float, tuple[str, ...]] | None = None
        best_outfit: ScoredOutfit | None = None
        for index in uncovered:
            for outfit in pools[index][:COVER_TRIES]:
                new = _core(outfit) - chosen
                if not new:
                    continue
                gain = _assigned_days(_assign(chosen | new, pools, items)) - current
                if gain <= 0:
                    continue
                key = (gain / len(new), outfit.score, tuple(sorted(outfit.core_ids)))
                if best is None or key[:2] > best[:2] or (key[:2] == best[:2] and key[2] < best[2]):
                    best, best_outfit = key, outfit
        if best_outfit is None:
            return chosen
        chosen |= _core(best_outfit)
        current = _assigned_days(_assign(chosen, pools, items))
    return chosen


def _prune(
    chosen: set[str],
    pools: Sequence[Sequence[ScoredOutfit]],
    items: Mapping[str, EngineItem],
) -> set[str]:
    """Leave out each piece, least useful first, while every coverable day stays covered with
    no piece worn more often than it can go between washes."""
    target = _assigned_days(_assign(chosen, pools, items))
    usefulness = {
        item_id: sum(1 for pool in pools for outfit in pool if item_id in outfit.core_ids)
        for item_id in chosen
    }
    for item_id in sorted(chosen, key=lambda item_id: (usefulness[item_id], item_id)):
        trial = chosen - {item_id}
        if _assigned_days(_assign(trial, pools, items)) >= target:
            chosen = trial
    return chosen


def _assigned_days(assigned: Sequence[ScoredOutfit | None]) -> int:
    return sum(1 for outfit in assigned if outfit is not None)


def _assign(
    chosen: set[str],
    pools: Sequence[Sequence[ScoredOutfit]],
    items: Mapping[str, EngineItem],
) -> list[ScoredOutfit | None]:
    """An outfit per day from the chosen pieces, best first, within each piece's wears left
    before a wash. Accessories that have run out simply stay off."""
    left = {
        item_id: (
            None
            if item.wears_before_wash is None
            else max(0, item.wears_before_wash - item.wears_since_wash)
        )
        for item_id, item in items.items()
    }
    found: list[ScoredOutfit | None] = []
    for pool in pools:
        pick = None
        for outfit in pool:
            if not _core(outfit) <= chosen:
                continue
            if all(
                left[item_id] is None or (left[item_id] or 0) > 0 for item_id in outfit.core_ids
            ):
                pick = outfit
                break
        if pick is not None:
            core = set(pick.core_ids)
            kept = tuple(
                item
                for item in pick.items
                if item.id in core or left[item.id] is None or (left[item.id] or 0) > 0
            )
            pick = replace(pick, items=kept)
            for item in kept:
                if left[item.id] is not None:
                    left[item.id] = (left[item.id] or 0) - 1
        found.append(pick)
    return found
