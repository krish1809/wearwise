"""Trends the Trend Scout found on the web (docs/AGENTS.md, section 4): where it may search, the
lists a trend's attributes must come from, recognising a trend found again, and saving what a
run kept.

Shared data: nothing here is about any one person. The scout's brief uses only how many people
chose each section and style, never who.
"""

import json
import re
import uuid
from collections.abc import Iterable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, cast

from sqlalchemy import CursorResult, func, select, update
from sqlalchemy.orm import QueryableAttribute, Session

from app.models import (
    AgentRun,
    Category,
    ColorFamily,
    Profile,
    StyleProfile,
    Trend,
    TrendSource,
    User,
)
from app.services import reference
from app.services.reference_seed import SEED_DIR

# A trend not found again for this long expires; a source older than this doesn't count.
EXPIRES_AFTER = timedelta(weeks=8)
SOURCE_MAX_AGE = timedelta(days=45)
# How alike two trends' attributes must be to be the same trend, when their names differ.
SAME_TREND = 0.6
# Words that say nothing about which trend it is.
FILLER = frozenset(
    {"a", "an", "and", "the", "of", "in", "for", "with", "to"}
    | {"trend", "trends", "look", "looks", "style", "styles"}
)


@dataclass(frozen=True)
class Sites:
    """The only sites searched, and the sites never read."""

    only: tuple[str, ...]
    blocked: tuple[str, ...]


def sites(seed_dir: Path = SEED_DIR) -> Sites:
    data = json.loads((seed_dir / "trend_sites.json").read_text())
    return Sites(tuple(data["only"]), tuple(data["blocked"]))


@dataclass(frozen=True)
class Window:
    """A time of year that changes what people buy, by the months it usually falls in."""

    id: str
    name: str
    about: str
    months: frozenset[int]


def windows(seed_dir: Path = SEED_DIR) -> list[Window]:
    data = json.loads((seed_dir / "calendar.json").read_text())
    return [
        Window(w["id"], w["name"], w.get("about", ""), frozenset(w["months"]))
        for w in data["windows"]
    ]


def upcoming(found: list[Window], today: date, ahead: timedelta) -> list[Window]:
    """The windows that this month or the month `ahead` falls in."""
    months = {today.month, (today + ahead).month}
    return [window for window in found if window.months & months]


@dataclass(frozen=True)
class Allowed:
    """Every value a trend may name, by kind, with the names the model is shown."""

    categories: dict[str, str]
    colors: dict[str, str]
    fabrics: dict[str, str]
    patterns: dict[str, str]
    fits: dict[str, str]
    seasons: dict[str, str]
    sections: dict[str, str]
    styles: dict[str, str]


def allowed(db: Session) -> Allowed:
    def named(kind: str) -> dict[str, str]:
        return {term.id: term.name for term in reference.terms(db, kind)}

    system = select(Category).where(Category.user_id.is_(None)).order_by(Category.position)
    return Allowed(
        categories={c.id: c.name for c in db.scalars(system)},
        colors={c.id: c.name for c in reference.ordered(db, ColorFamily)},
        fabrics=named("fabric"),
        patterns=named("pattern"),
        fits=named("fit"),
        seasons=named("season"),
        sections=named("section"),
        styles={s.id: s.name for s in reference.ordered(db, StyleProfile)},
    )


@dataclass(frozen=True)
class Interest:
    """How many people (not demo accounts) chose each section and style: counts, never who."""

    sections: dict[str, int]
    styles: dict[str, int]


def interest(db: Session) -> Interest:
    def counts(column: QueryableAttribute[list[str]]) -> dict[str, int]:
        chosen = func.unnest(column).label("chosen")
        rows = db.execute(
            select(chosen, func.count())
            .select_from(Profile)
            .join(User, User.id == Profile.user_id)
            .where(User.is_demo.is_(False))
            .group_by(chosen)
            .order_by(func.count().desc(), chosen)
        )
        return {str(name): int(count) for name, count in rows}

    return Interest(counts(Profile.sections), counts(Profile.style_profile_ids))


def credits_used(db: Session, now: datetime) -> int:
    """Search credits the Trend Scout's runs have used this calendar month (UTC)."""
    month = now.astimezone(UTC).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return (
        db.scalar(
            select(func.sum(AgentRun.search_credits)).where(
                AgentRun.kind == "trend_scout", AgentRun.started_at >= month
            )
        )
        or 0
    )


def name_key(name: str) -> str:
    """A trend's name reduced to its meaning: "The Linen Co-ord Trend" and "linen co-ords"
    are the same trend."""
    words = re.findall(r"[a-z0-9]+", name.lower())
    kept = [w.removesuffix("s") if len(w) > 3 else w for w in words if w not in FILLER]
    return " ".join(sorted(kept))


@dataclass(frozen=True)
class KeptSource:
    url: str
    domain: str
    title: str
    published_on: date
    quote: str


@dataclass(frozen=True)
class Kept:
    """A trend that passed every check, ready to save."""

    name: str
    summary: str
    why_now: str
    category_ids: tuple[str, ...]
    color_families: tuple[str, ...] = ()
    fabrics: tuple[str, ...] = ()
    patterns: tuple[str, ...] = ()
    fits: tuple[str, ...] = ()
    seasons: tuple[str, ...] = ()
    sections: tuple[str, ...] = ()
    style_profile_ids: tuple[str, ...] = ()
    sources: tuple[KeptSource, ...] = field(default=())


def _attributes(
    categories: Iterable[str],
    colors: Iterable[str],
    fabrics: Iterable[str],
    patterns: Iterable[str],
    fits: Iterable[str],
) -> set[str]:
    found: set[str] = set()
    for kind, values in (
        ("category", categories),
        ("color", colors),
        ("fabric", fabrics),
        ("pattern", patterns),
        ("fit", fits),
    ):
        found.update(f"{kind}:{value}" for value in values)
    return found


def _kept_attributes(kept: Kept) -> set[str]:
    return _attributes(
        kept.category_ids, kept.color_families, kept.fabrics, kept.patterns, kept.fits
    )


def _trend_attributes(trend: Trend) -> set[str]:
    return _attributes(
        trend.category_ids, trend.color_families, trend.fabrics, trend.patterns, trend.fits
    )


def overlap(a: set[str], b: set[str]) -> float:
    return len(a & b) / len(a | b) if a | b else 0.0


def alike(a: Kept, b: Kept) -> bool:
    """Whether two trends found in one run are the same trend, by the same rule as `match`."""
    if name_key(a.name) == name_key(b.name):
        return True
    shared = set(a.category_ids) & set(b.category_ids)
    return bool(shared) and overlap(_kept_attributes(a), _kept_attributes(b)) >= SAME_TREND


def match(trends: list[Trend], kept: Kept) -> Trend | None:
    """The trend this one is, if any: the same name, or mostly the same attributes with a
    category in common."""
    key = name_key(kept.name)
    for trend in trends:
        if trend.name_key == key:
            return trend
    mine = _kept_attributes(kept)
    best: tuple[float, Trend] | None = None
    for trend in trends:
        if not set(trend.category_ids) & set(kept.category_ids):
            continue
        score = overlap(mine, _trend_attributes(trend))
        if score >= SAME_TREND and (best is None or score > best[0]):
            best = (score, trend)
    return best[1] if best else None


@dataclass
class Saved:
    added: list[str] = field(default_factory=list)
    merged: list[str] = field(default_factory=list)


def save(db: Session, kept: list[Kept], run: AgentRun, now: datetime, approve: bool) -> Saved:
    """Save what a run kept: a trend found before gains the new sources and is seen again
    (its status and attributes stay as they were); anything else is new, pending the owner's
    approval unless `approve`. Safe to repeat: a second pass finds what the first saved."""
    trends = list(db.scalars(select(Trend).where(Trend.status != "expired")))
    saved = Saved()
    for found in kept:
        trend = match(trends, found)
        if trend is None:
            trend = Trend(
                name=found.name,
                name_key=name_key(found.name),
                summary=found.summary,
                why_now=found.why_now,
                category_ids=list(found.category_ids),
                color_families=list(found.color_families),
                fabrics=list(found.fabrics),
                patterns=list(found.patterns),
                fits=list(found.fits),
                seasons=list(found.seasons),
                sections=list(found.sections),
                style_profile_ids=list(found.style_profile_ids),
                status="approved" if approve else "pending",
                first_seen_at=now,
                last_seen_at=now,
                decided_at=now if approve else None,
                run_id=run.id,
            )
            db.add(trend)
            db.flush()
            trends.append(trend)
            saved.added.append(found.name)
        else:
            trend.last_seen_at = now
            saved.merged.append(found.name)
        known = set(db.scalars(select(TrendSource.url).where(TrendSource.trend_id == trend.id)))
        for source in found.sources:
            if source.url in known:
                continue
            known.add(source.url)
            db.add(
                TrendSource(
                    trend_id=trend.id,
                    url=source.url,
                    domain=source.domain,
                    title=source.title,
                    published_on=source.published_on,
                    quote=source.quote,
                    run_id=run.id,
                )
            )
    db.flush()
    return saved


def expire(db: Session, now: datetime) -> int:
    """Trends not found again for 8 weeks expire. Returns how many."""
    result = db.execute(
        update(Trend)
        .where(Trend.status.in_(("pending", "approved")), Trend.last_seen_at < now - EXPIRES_AFTER)
        .values(status="expired")
    )
    return cast(CursorResult[Any], result).rowcount


# For the owner's approval page.

STATUSES = ("pending", "approved", "rejected", "expired")


def listed(db: Session, status: str) -> list[Trend]:
    """Trends with this status, most recently seen first."""
    return list(
        db.scalars(select(Trend).where(Trend.status == status).order_by(Trend.last_seen_at.desc()))
    )


def sources_for(db: Session, trend_ids: list[uuid.UUID]) -> dict[uuid.UUID, list[TrendSource]]:
    found: dict[uuid.UUID, list[TrendSource]] = {trend_id: [] for trend_id in trend_ids}
    if not trend_ids:
        return found
    query = (
        select(TrendSource)
        .where(TrendSource.trend_id.in_(trend_ids))
        .order_by(TrendSource.published_on.desc(), TrendSource.url)
    )
    for source in db.scalars(query):
        found[source.trend_id].append(source)
    return found


def counts(db: Session) -> dict[str, int]:
    rows = db.execute(select(Trend.status, func.count()).group_by(Trend.status))
    found = {status: 0 for status in STATUSES}
    found.update({str(status): int(count) for status, count in rows})
    return found


def find(db: Session, trend_id: uuid.UUID) -> Trend | None:
    return db.get(Trend, trend_id)


def decide(trend: Trend, status: str, now: datetime) -> Trend:
    """The owner approves or rejects a trend, or puts it back to pending. The caller commits."""
    trend.status = status
    trend.decided_at = None if status == "pending" else now
    return trend
