"""The weekly digest's picks (docs/AGENTS.md, section 5; ENGINE.md, section 14): which of the
trends in fashion now are worth acting on for one person, judged against what they own. Plain
data in, plain data out.

A trend becomes a candidate piece (the service builds it from the trend and the category's
defaults). One very like something the person owns isn't a purchase: it becomes "already in your
wardrobe", with a good outfit that piece is part of. Otherwise the purchase analyzer judges it
exactly as a purchase check would, and a Skip is dropped. What's left is scored mostly on what it
would add:

    pick = 0.60 * value + 0.25 * trend fit + 0.15 * season fit

and up to three are chosen, each from a different category and a different trend. A trend the
person said "not for me" to is never picked again; the same category and colour scores half for
eight weeks. Nothing worth it means no picks, which is a real answer.
"""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from app.engine.config import DEFAULT, EngineConfig
from app.engine.insights import Measures, steady
from app.engine.shopping import Analysis, PairCache, Verdict, analyse, closest, verdict
from app.engine.types import Context, EngineItem, Occasion, Wardrobe


@dataclass(frozen=True)
class TrendOption:
    """One way to follow a trend: a piece of one of its categories, in one of its colours."""

    trend_id: str
    candidate: EngineItem
    styles: frozenset[str]
    colors: frozenset[str]
    # Empty means every season.
    seasons: frozenset[str]


@dataclass(frozen=True)
class Declined:
    """A pick the person said "not for me" to."""

    trend_id: str
    category_id: str
    color_family: str
    days_ago: int


@dataclass(frozen=True)
class Person:
    styles: frozenset[str]
    preferred_colors: frozenset[str]
    avoided_colors: frozenset[str]
    season_now: str
    season_ahead: str
    declined: tuple[Declined, ...] = ()


@dataclass(frozen=True)
class Pick:
    trend_id: str
    # buy: the candidate piece; owned: a piece the person already has.
    kind: str
    item: EngineItem
    score: float
    value: float
    trend_fit: float
    season_fit: float
    # A good outfit with it (core ids): one the owned piece is in, or the best one the
    # candidate would make. Empty when there's none.
    outfit: tuple[str, ...]
    # The purchase analysis and verdict, for a piece to buy.
    analysis: Analysis | None = None
    verdict: Verdict | None = None


def trend_fit(styles: frozenset[str], colors: frozenset[str], person: Person) -> float:
    """How well the trend suits the person's own taste: the share of its styles they chose
    and of its colours they like, averaged over what both name. 0.5 when there's nothing to
    compare."""
    parts = []
    if styles and person.styles:
        parts.append(len(styles & person.styles) / len(styles))
    if colors and person.preferred_colors:
        parts.append(len(colors & person.preferred_colors) / len(colors))
    return sum(parts) / len(parts) if parts else 0.5


def season_fit(seasons: frozenset[str], person: Person, config: EngineConfig = DEFAULT) -> float:
    """1 for a trend in season now (or for every season), less for the season ahead, else 0."""
    if not seasons or person.season_now in seasons:
        return 1.0
    if person.season_ahead in seasons:
        return config.pick_next_season
    return 0.0


def pick(
    options: Sequence[TrendOption],
    person: Person,
    wardrobe: Wardrobe,
    base: Context,
    occasions: Sequence[Occasion],
    seasons: Sequence[str],
    before: Measures,
    line: float | None,
    names: Mapping[str, str],
    config: EngineConfig = DEFAULT,
    pair_cache: PairCache | None = None,
) -> list[Pick]:
    """Up to config.picks picks, best first. `before` is the wardrobe measured for the
    person's occasions and seasons; `line` is the coverage gain a Buy needs (shopping.buy_line),
    used to put gains on one scale; `names` names the owned pieces, for the verdicts."""
    owned = [item for item in steady(wardrobe).items if item.owner_id == base.user_id]
    never = {declined.trend_id for declined in person.declined}
    scored: list[Pick] = []
    to_analyse: list[tuple[float, TrendOption, float, float]] = []
    for option in options:
        item = option.candidate
        if option.trend_id in never or item.color_family in person.avoided_colors:
            continue
        fits = trend_fit(option.styles, option.colors, person)
        season = season_fit(option.seasons, person, config)
        if season == 0:
            continue
        near, likeness = closest(item, owned, config)
        if near is not None and likeness >= config.duplicate_at:
            if near.color_family in person.avoided_colors:
                # Like a piece the person avoids wearing: neither a purchase nor a pick.
                continue
            # Already in the wardrobe: worth as much as the good outfits it's part of.
            value = min(1.0, before.versatility.get(near.id, 0) / config.coverage_cap)
            scored.append(
                _scored(
                    option,
                    "owned",
                    near,
                    value,
                    fits,
                    season,
                    _outfit_with(near.id, before),
                    person,
                    config,
                )
            )
            continue
        promise = config.pick_trend_fit * fits + config.pick_season_fit * season
        to_analyse.append((promise, option, fits, season))

    # The analysis is the slow part, so only the most promising get one.
    to_analyse.sort(key=lambda entry: (-entry[0], entry[1].trend_id, entry[1].candidate.id))
    judged: list[tuple[TrendOption, float, float, Analysis, Verdict]] = []
    for _, option, fits, season in to_analyse[: config.pick_analysed]:
        found = analyse(
            wardrobe, base, occasions, seasons, before, option.candidate, config, pair_cache
        )
        outcome = verdict(
            found,
            option.candidate,
            names,
            occasions,
            before.coverage,
            line,
            None,
            "",
            person.avoided_colors,
            config,
        )
        if outcome.code != "skip":
            judged.append((option, fits, season, found, outcome))
    # Gains on one scale: what a Buy needs, or the best gain here when there's no line.
    scale = line or max((found.coverage_gain for *_, found, _ in judged), default=0.0) or 1.0
    for option, fits, season, found, outcome in judged:
        if found.kind == "core":
            gain = min(1.0, found.coverage_gain / scale)
        else:
            # An accessory adds no outfits of its own; it's worth the outfits it finishes.
            gain = min(1.0, found.new_outfits / config.coverage_cap)
        value = gain * (1 - found.redundancy)
        example = found.examples[0][1] if found.examples else ()
        scored.append(
            _scored(
                option,
                "buy",
                option.candidate,
                value,
                fits,
                season,
                example,
                person,
                config,
                found,
                outcome,
            )
        )
    return _choose(scored, config)


def _scored(
    option: TrendOption,
    kind: str,
    item: EngineItem,
    value: float,
    fits: float,
    season: float,
    outfit: tuple[str, ...],
    person: Person,
    config: EngineConfig,
    analysis: Analysis | None = None,
    outcome: Verdict | None = None,
) -> Pick:
    score = (
        config.pick_value * value + config.pick_trend_fit * fits + config.pick_season_fit * season
    )
    weeks = config.pick_declined_weeks * 7
    if any(
        d.category_id == item.category_id
        and d.color_family == item.color_family
        and d.days_ago < weeks
        for d in person.declined
    ):
        score *= config.pick_declined_factor
    return Pick(
        trend_id=option.trend_id,
        kind=kind,
        item=item,
        score=round(score, 4),
        value=round(value, 4),
        trend_fit=round(fits, 4),
        season_fit=round(season, 4),
        outfit=outfit,
        analysis=analysis,
        verdict=outcome,
    )


def _outfit_with(item_id: str, before: Measures) -> tuple[str, ...]:
    """A good outfit the piece is part of; the same one every time."""
    return min((core for core in before.good if item_id in core), default=())


def _choose(scored: list[Pick], config: EngineConfig) -> list[Pick]:
    chosen: list[Pick] = []
    categories: set[str] = set()
    trends: set[str] = set()
    for found in sorted(scored, key=lambda p: (-p.score, p.kind != "buy", p.trend_id, p.item.id)):
        if found.item.category_id in categories or found.trend_id in trends:
            continue
        chosen.append(found)
        categories.add(found.item.category_id)
        trends.add(found.trend_id)
        if len(chosen) == config.picks:
            break
    return chosen
