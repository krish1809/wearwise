"""Insights: what's worn, what's good value, what the wardrobe can do, and what might go.

Every number here comes from rows in the database: wear counts from the wear log, prices from
items, and the graph measures from the engine over the current wardrobe. Nothing is projected
or estimated. Rankings wait until there are enough wear logs to mean something.
"""

import uuid
from collections import OrderedDict
from dataclasses import dataclass, replace
from datetime import date, timedelta
from threading import Lock

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.engine.config import DEFAULT, ENGINE_VERSION
from app.engine.generate import good_cores, season_for, suggest
from app.engine.insights import (
    Family,
    Measures,
    WornStyle,
    measure,
    steady,
    steady_context,
    worn_style,
)
from app.models import (
    Category,
    CategoryGroup,
    ColorFamily,
    Item,
    Occasion,
    Profile,
    StyleProfile,
    SuggestionFeedback,
    User,
    WearLog,
    WearLogItem,
)
from app.services import profile as profiles
from app.services import reference, suggestions

# Rankings and the worn style need at least this many days of wear logged.
MIN_LOGS = 5
TOP = 5
COST_LIST = 3
MONTHS = 6
# "Least worn" only counts things owned at least this long; declutter suggestions wait longer.
SETTLED_DAYS = 30
UNWORN_DAYS = 182

_CACHED = 8
_measures: OrderedDict[tuple[object, ...], Measures] = OrderedDict()
_lock = Lock()


@dataclass(frozen=True)
class Worn:
    item: Item
    wears: int
    last_worn_on: date | None


@dataclass(frozen=True)
class CostPerWear:
    item: Item
    wears: int
    # Minor units (paise), rounded to the nearest one.
    per_wear: int


@dataclass(frozen=True)
class Tally:
    id: str
    name: str
    wears: int
    hex: str | None = None


@dataclass(frozen=True)
class Declutter:
    item: Item
    last_worn_on: date | None
    versatility: int


@dataclass
class Insights:
    items: int
    logs: int
    days_logged_30: int
    enough: bool
    most_worn: list[Worn]
    least_worn: list[Worn]
    by_month: list[tuple[str, int]]
    by_group: list[Tally]
    by_color: list[Tally]
    cheapest: list[CostPerWear]
    dearest: list[CostPerWear]
    needs_price: list[Item]
    occasions: list[Occasion]
    seasons: list[str]
    measures: Measures | None
    items_by_id: dict[uuid.UUID, Item]
    style: WornStyle | None
    chosen_styles: list[str]
    declutter: list[Declutter]


def gather(db: Session, user: User, today: date) -> Insights:
    profile = profiles.get_or_create_profile(db, user)
    items = list(
        db.scalars(
            select(Item)
            .where(Item.user_id == user.id, Item.archived_at.is_(None))
            .order_by(Item.created_at, Item.id)
        )
    )
    by_id = {item.id: item for item in items}
    counts = _wear_counts(db, user)
    logs = db.scalar(select(func.count()).where(WearLog.user_id == user.id)) or 0
    enough = logs >= MIN_LOGS
    days_30 = (
        db.scalar(
            select(func.count(WearLog.worn_on.distinct())).where(
                WearLog.user_id == user.id, WearLog.worn_on > today - timedelta(days=30)
            )
        )
        or 0
    )
    worn = [
        Worn(item, counts.get(item.id, (0, None))[0], counts.get(item.id, (0, None))[1])
        for item in items
        if item.status != "retired"
    ]
    most = sorted(
        (entry for entry in worn if entry.wears),
        key=lambda entry: (-entry.wears, -(entry.last_worn_on or date.min).toordinal()),
    )[:TOP]
    settled = today - timedelta(days=SETTLED_DAYS)
    least = sorted(
        (entry for entry in worn if entry.item.created_at.date() <= settled),
        key=lambda entry: (entry.wears, entry.last_worn_on or date.min, entry.item.created_at),
    )[:TOP]

    priced = [
        CostPerWear(entry.item, entry.wears, round(entry.item.price / entry.wears))
        for entry in worn
        if entry.item.price is not None and entry.wears
    ]
    by_value = sorted(priced, key=lambda entry: (entry.per_wear, -entry.wears))
    cheapest = by_value[:COST_LIST]
    dearest = [entry for entry in reversed(by_value) if entry not in cheapest][:COST_LIST]
    needs_price = [entry.item for entry in worn if entry.wears and entry.item.price is None]

    occasions = occasions_for(db, profile)
    seasons = [term.id for term in reference.terms(db, "season")]
    measures = measures_for(db, user, profile, occasions, seasons, today) if items else None
    style = _worn_style(db, user, profile, worn, today) if enough else None

    return Insights(
        items=len(items),
        logs=logs,
        days_logged_30=days_30,
        enough=enough,
        most_worn=most if enough else [],
        least_worn=least if enough else [],
        by_month=_by_month(db, user, today),
        by_group=_by_group(db, user),
        by_color=_by_color(db, user),
        cheapest=cheapest,
        dearest=dearest,
        needs_price=needs_price,
        occasions=occasions,
        seasons=seasons,
        measures=measures,
        items_by_id=by_id,
        style=style,
        chosen_styles=list(profile.style_profile_ids),
        declutter=_declutter(worn, measures, today),
    )


def _wear_counts(db: Session, user: User) -> dict[uuid.UUID, tuple[int, date | None]]:
    rows = db.execute(
        select(WearLogItem.item_id, func.count(), func.max(WearLog.worn_on))
        .join(WearLog, WearLog.id == WearLogItem.wear_log_id)
        .where(WearLog.user_id == user.id, WearLogItem.item_id.is_not(None))
        .group_by(WearLogItem.item_id)
    ).all()
    return {item_id: (count, last) for item_id, count, last in rows if item_id is not None}


def _by_month(db: Session, user: User, today: date) -> list[tuple[str, int]]:
    """Days logged in each of the last six months, oldest first."""
    months = []
    year, month = today.year, today.month
    for _ in range(MONTHS):
        months.append((year, month))
        year, month = (year, month - 1) if month > 1 else (year - 1, 12)
    months.reverse()
    first = date(months[0][0], months[0][1], 1)
    rows = db.execute(
        select(WearLog.worn_on).where(WearLog.user_id == user.id, WearLog.worn_on >= first)
    ).scalars()
    counts: dict[tuple[int, int], int] = {}
    for worn_on in rows:
        key = (worn_on.year, worn_on.month)
        counts[key] = counts.get(key, 0) + 1
    return [(f"{year:04d}-{month:02d}", counts.get((year, month), 0)) for year, month in months]


def _by_group(db: Session, user: User) -> list[Tally]:
    """Wears of each category group (a piece worn in a log counts once)."""
    rows = db.execute(
        select(CategoryGroup.id, CategoryGroup.name, func.count())
        .select_from(WearLogItem)
        .join(WearLog, WearLog.id == WearLogItem.wear_log_id)
        .join(Item, Item.id == WearLogItem.item_id)
        .join(Category, Category.id == Item.category_id)
        .join(CategoryGroup, CategoryGroup.id == Category.group_id)
        .where(WearLog.user_id == user.id)
        .group_by(CategoryGroup.id, CategoryGroup.name, CategoryGroup.position)
        .order_by(func.count().desc(), CategoryGroup.position)
    ).all()
    return [Tally(group, name, count) for group, name, count in rows]


def _by_color(db: Session, user: User) -> list[Tally]:
    rows = db.execute(
        select(ColorFamily.id, ColorFamily.name, ColorFamily.hex, func.count())
        .select_from(WearLogItem)
        .join(WearLog, WearLog.id == WearLogItem.wear_log_id)
        .join(Item, Item.id == WearLogItem.item_id)
        .join(ColorFamily, ColorFamily.id == Item.color_primary)
        .where(WearLog.user_id == user.id)
        .group_by(ColorFamily.id, ColorFamily.name, ColorFamily.hex, ColorFamily.position)
        .order_by(func.count().desc(), ColorFamily.position)
    ).all()
    return [Tally(color, name, count, hex_) for color, name, hex_, count in rows]


def occasions_for(db: Session, profile: Profile) -> list[Occasion]:
    """The occasions the person dresses for: chosen in onboarding, or in their usual week."""
    wanted = set(profile.occasion_ids) | set(profile.weekday_occasions.values())
    return [occasion for occasion in reference.ordered(db, Occasion) if occasion.id in wanted]


def fingerprint(
    db: Session, user: User, profile: Profile, occasions: list[Occasion]
) -> tuple[object, ...]:
    """Everything the wardrobe's measures depend on: when any of it changes, they're worked
    out again. The wardrobe (its version), the engine, the occasions, the styles and colours
    chosen in the profile, and the reactions to suggestions."""
    reactions = db.scalar(select(func.count()).where(SuggestionFeedback.user_id == user.id)) or 0
    return (
        user.id,
        user.wardrobe_version,
        ENGINE_VERSION,
        tuple(occasion.id for occasion in occasions),
        tuple(sorted(profile.style_profile_ids)),
        tuple(sorted(profile.preferred_colors)),
        tuple(sorted(profile.avoided_colors)),
        profile.fit_preference,
        reactions,
    )


def measures_for(
    db: Session,
    user: User,
    profile: Profile,
    occasions: list[Occasion],
    seasons: list[str],
    today: date,
) -> Measures | None:
    """The wardrobe graph for these occasions and seasons, cached per fingerprint."""
    if not occasions:
        return None
    key = (*fingerprint(db, user, profile, occasions), tuple(seasons))
    with _lock:
        cached = _measures.get(key)
        if cached is not None:
            _measures.move_to_end(key)
            return cached
    wardrobe = suggestions.load_wardrobe(db, user, today)
    base = suggestions.base_context(db, user, profile, wardrobe, today)
    families = [
        Family(family.id, family.name, family.hex, family.neutrality)
        for family in reference.ordered(db, ColorFamily)
    ]
    found = measure(
        wardrobe,
        base,
        [suggestions.engine_occasion(occasion) for occasion in occasions],
        seasons,
        families,
        DEFAULT,
        suggestions.pair_cache_for(user),
    )
    with _lock:
        for old in [k for k in _measures if k[0] == user.id]:
            del _measures[old]
        _measures[key] = found
        while len(_measures) > _CACHED:
            _measures.popitem(last=False)
    return found


def _worn_style(
    db: Session, user: User, profile: Profile, worn: list[Worn], today: date
) -> WornStyle:
    wardrobe = suggestions.load_wardrobe(db, user, today)
    engine_items = {item.id: item for item in wardrobe.items}
    styles = [suggestions.engine_style(row) for row in reference.ordered(db, StyleProfile)]
    pairs = [
        (engine_items[str(entry.item.id)], entry.wears)
        for entry in worn
        if str(entry.item.id) in engine_items
    ]
    return worn_style(pairs, styles, wardrobe.slot_kinds, DEFAULT)


def _declutter(worn: list[Worn], measures: Measures | None, today: date) -> list[Declutter]:
    """Pieces not worn for six months (or never, in six months owned) that go with little."""
    if measures is None:
        return []
    cutoff = today - timedelta(days=UNWORN_DAYS)
    found = []
    for entry in worn:
        versatility = measures.versatility.get(str(entry.item.id))
        if versatility is None or versatility >= DEFAULT.orphan_below:
            continue
        last = entry.last_worn_on
        stale = last <= cutoff if last else entry.item.created_at.date() <= cutoff
        if stale:
            found.append(Declutter(entry.item, last, versatility))
    return sorted(found, key=lambda entry: (entry.versatility, entry.last_worn_on or date.min))


def without_cache() -> None:
    """For tests: forget cached measures."""
    with _lock:
        _measures.clear()


@dataclass(frozen=True)
class CellDetail:
    """One occasion and season of the coverage map, opened."""

    # Good outfits there, best first (at most ten), as core item ids.
    outfits: list[tuple[list[uuid.UUID], float]]
    # When there are none: why, and the closest outfits there are.
    missing: list[str]
    closest: list[tuple[list[uuid.UUID], float]]
    # Staples (ids) that would add good outfits there, most first.
    staples: list[str]


def cell(db: Session, user: User, occasion: Occasion, season: str, today: date) -> CellDetail:
    """The good outfits for one occasion and season, counted the same way as the coverage
    map (the steady wardrobe, the season's weather); with none, what's missing."""
    # Shopping builds on this module, so it's imported here, not at the top.
    from app.services import shopping

    profile = profiles.get_or_create_profile(db, user)
    wardrobe = steady(suggestions.load_wardrobe(db, user, today))
    base = suggestions.base_context(db, user, profile, wardrobe, today)
    context = replace(
        steady_context(base),
        occasion=suggestions.engine_occasion(occasion),
        season=season,
        count=3,
    )
    pairs = suggestions.pair_cache_for(user)
    found = good_cores(wardrobe, context, DEFAULT.versatility_min_score, DEFAULT, pairs)
    outfits = [([uuid.UUID(i) for i in o.core_ids], o.score) for o in found[:10]]
    missing: list[str] = []
    closest: list[tuple[list[uuid.UUID], float]] = []
    if not outfits:
        near = suggest(wardrobe, context, DEFAULT, pairs)
        missing = [m.text for m in near.missing]
        closest = [([uuid.UUID(i) for i in o.core_ids], o.score) for o in near.outfits[:2]]
    s = shopping.setting(db, user, today)
    staples = [
        gap.item_ids[0].removeprefix(shopping.STAPLE)
        for gap in shopping.gaps(db, s)
        if len(gap.item_ids) == 1 and gap.added.get((occasion.id, season))
    ][:3]
    return CellDetail(outfits, missing, closest, staples)


CHALLENGE_DAYS = 60


@dataclass(frozen=True)
class Challenge:
    """The "wear what you own" challenge: wear every piece at least once in 60 days."""

    started_on: date
    # The last day that counts.
    ends_on: date
    # Today's day of the challenge, 1 to 60; past 60 once it's over.
    day: int
    finished: bool
    # Pieces in the wardrobe now (not archived or retired), and how many of them were worn
    # between the start and the end (or today).
    total: int
    worn: int
    # The ones not worn yet, oldest first.
    unworn: list[Item]


def challenge(db: Session, user: User, today: date) -> Challenge | None:
    """The running challenge, counted from wear logs since it began; None when none runs."""
    profile = profiles.get_or_create_profile(db, user)
    start = profile.challenge_started_on
    if start is None:
        return None
    ends_on = start + timedelta(days=CHALLENGE_DAYS - 1)
    pieces = list(
        db.scalars(
            select(Item)
            .where(Item.user_id == user.id, Item.archived_at.is_(None), Item.status != "retired")
            .order_by(Item.created_at, Item.id)
        )
    )
    worn = set(
        db.scalars(
            select(WearLogItem.item_id)
            .join(WearLog, WearLog.id == WearLogItem.wear_log_id)
            .where(
                WearLog.user_id == user.id,
                WearLog.worn_on >= start,
                WearLog.worn_on <= min(today, ends_on),
                WearLogItem.item_id.is_not(None),
            )
            .distinct()
        )
    )
    return Challenge(
        started_on=start,
        ends_on=ends_on,
        day=(today - start).days + 1,
        finished=today > ends_on,
        total=len(pieces),
        worn=sum(1 for item in pieces if item.id in worn),
        unworn=[item for item in pieces if item.id not in worn],
    )


def start_challenge(db: Session, user: User, today: date) -> None:
    """Start (or start again) from today."""
    profiles.get_or_create_profile(db, user).challenge_started_on = today
    db.flush()


def stop_challenge(db: Session, user: User) -> None:
    profiles.get_or_create_profile(db, user).challenge_started_on = None
    db.flush()


REMIX_MAX = 10
REMIX_SHOWN = 6


@dataclass(frozen=True)
class Remix:
    """What a handful of pieces can do on their own: the good outfits from only them, for
    each occasion the person dresses for, this season."""

    season: str
    # Each occasion, its best good outfits (core item ids and score), and how many in all.
    by_occasion: list[tuple[Occasion, list[tuple[list[uuid.UUID], float]], int]]
    # Distinct good outfits across every occasion.
    total: int


def remix(db: Session, user: User, item_ids: list[uuid.UUID], today: date) -> Remix:
    """Scored the same way as the coverage map (the steady wardrobe, the season's weather),
    over the chosen pieces alone."""
    profile = profiles.get_or_create_profile(db, user)
    chosen = {str(item_id) for item_id in item_ids}
    full = steady(suggestions.load_wardrobe(db, user, today))
    wardrobe = replace(full, items=tuple(item for item in full.items if item.id in chosen))
    season = season_for(today)
    base = replace(
        steady_context(suggestions.base_context(db, user, profile, wardrobe, today)),
        season=season,
    )
    pairs = suggestions.pair_cache_for(user)
    groups = []
    seen: set[tuple[str, ...]] = set()
    for occasion in occasions_for(db, profile):
        context = replace(base, occasion=suggestions.engine_occasion(occasion), count=3)
        found = good_cores(wardrobe, context, DEFAULT.versatility_min_score, DEFAULT, pairs)
        seen.update(outfit.core_ids for outfit in found)
        best = [([uuid.UUID(i) for i in o.core_ids], o.score) for o in found[:REMIX_SHOWN]]
        groups.append((occasion, best, len(found)))
    return Remix(season=season, by_occasion=groups, total=len(seen))
