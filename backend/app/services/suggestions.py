"""Outfit suggestions: load the wardrobe, call the engine, keep what was shown, and learn
from what the person does with it.

The engine works on plain data (app/engine). This module turns rows into that data, stores
each suggestion with the engine version that made it, and records reactions. Pair scores
depend only on the items, so they are cached per user and wardrobe version in this process.
"""

import uuid
from collections import OrderedDict
from dataclasses import asdict, dataclass, replace
from datetime import date, timedelta
from threading import Lock
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.adapters.weather import WeatherProvider
from app.engine import feedback as learning
from app.engine.config import DEFAULT, ENGINE_VERSION
from app.engine.generate import season_for, suggest
from app.engine.pairs import PairScore
from app.engine.types import (
    Context,
    EngineItem,
    Preferences,
    Style,
    Suggestions,
    Wardrobe,
)
from app.engine.types import (
    Occasion as EngineOccasion,
)
from app.models import (
    Category,
    CategoryGroup,
    ColorFamily,
    Item,
    Occasion,
    Outfit,
    Profile,
    StyleProfile,
    Suggestion,
    SuggestionFeedback,
    User,
    WearLog,
    WearLogItem,
)
from app.services import outfits, reference, wear
from app.services import weather as weather_service
from app.services.item_names import ItemNames

MAX_ANCHORS = 6
MAX_COUNT = 12
RATINGS = ("like", "dislike", "skip")
DISLIKE_REASONS = ("item", "colors", "formality", "occasion", "other")
# Pair score caches kept in memory, one per user and wardrobe version.
_CACHED_WARDROBES = 8
_pair_caches: OrderedDict[tuple[uuid.UUID, int, str], dict[tuple[str, str], PairScore]] = (
    OrderedDict()
)
_cache_lock = Lock()


class SuggestInvalid(Exception):
    def __init__(
        self,
        fields: dict[str, str],
        message: str = "Check the highlighted fields.",
        code: str = "invalid_input",
    ) -> None:
        super().__init__(message)
        self.fields = fields
        self.message = message
        self.code = code


class SuggestionStale(Exception):
    """A piece of the suggestion has been deleted or archived since it was shown."""


@dataclass(frozen=True)
class Request:
    occasion_id: str | None
    season: str | None
    style_id: str | None
    anchor_ids: list[uuid.UUID]
    exclude_ids: list[uuid.UUID]
    count: int


@dataclass
class Result:
    engine: Suggestions
    rows: list[Suggestion]
    season: str


def kind_for(anchors: int) -> str:
    if anchors == 0:
        return "occasion"
    return "with_item" if anchors == 1 else "complete"


def run(
    db: Session,
    user: User,
    request: Request,
    provider: WeatherProvider,
    today: date | None = None,
) -> Result:
    """Suggest outfits and keep each one shown, so reactions can refer to it."""
    day = today or wear.today()
    problems = _check(db, user, request)
    if problems:
        raise SuggestInvalid(problems)
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    # Today's weather, unless a season was chosen; first, since it may end the transaction.
    weather = (
        weather_service.for_days(db, provider, profile, [day])[day].for_engine()
        if request.season is None
        else None
    )
    wardrobe = load_wardrobe(db, user, day)
    occasion = db.get(Occasion, request.occasion_id) if request.occasion_id else None
    season = request.season or season_for(day)
    context = replace(
        base_context(db, user, profile, wardrobe, day),
        occasion=engine_occasion(occasion) if occasion else None,
        season=season,
        weather=weather,
        style=_style(db.get_one(StyleProfile, request.style_id)) if request.style_id else None,
        anchor_ids=tuple(str(anchor) for anchor in request.anchor_ids),
        exclude_ids=frozenset(str(item_id) for item_id in request.exclude_ids),
        count=request.count,
    )
    result = suggest(wardrobe, context, DEFAULT, pair_cache_for(user))
    rows = []
    for outfit in result.outfits:
        row = Suggestion(
            user_id=user.id,
            kind=kind_for(len(request.anchor_ids)),
            occasion_id=request.occasion_id,
            season=season,
            template_id=outfit.template_id,
            item_ids=[uuid.UUID(item.id) for item in outfit.items],
            core_ids=[uuid.UUID(item_id) for item_id in outfit.core_ids],
            score=outfit.score,
            components=asdict(outfit.components),
            reasons=[
                {"code": reason.code, "kind": reason.kind, "text": reason.text}
                for reason in outfit.reasons
            ],
            compromise=outfit.compromise,
            engine_version=result.engine_version,
        )
        db.add(row)
        rows.append(row)
    db.flush()
    return Result(engine=result, rows=rows, season=season)


def base_context(
    db: Session, user: User, profile: Profile | None, wardrobe: Wardrobe, day: date
) -> Context:
    """Everything about the person that every request shares: their styles, what they wore
    lately, and what their reactions taught the engine."""
    return Context(
        user_id=str(user.id),
        today=day,
        season=season_for(day),
        profile_styles=_profile_styles(db, profile),
        recent_outfits=_recent_outfits(db, user, day, wardrobe),
        preferences=_preferences(db, user, profile, wardrobe),
    )


def _check(db: Session, user: User, request: Request) -> dict[str, str]:
    problems: dict[str, str] = {}
    if request.occasion_id is None and not request.anchor_ids:
        problems["occasion_id"] = "Choose an occasion."
    elif request.occasion_id is not None and request.occasion_id not in reference.known_ids(
        db, Occasion
    ):
        problems["occasion_id"] = "Choose one of the options shown."
    if request.season is not None and request.season not in reference.known_terms(db, "season"):
        problems["season"] = "Choose one of the options shown."
    if request.style_id is not None and request.style_id not in reference.known_ids(
        db, StyleProfile
    ):
        problems["style_id"] = "Choose one of the options shown."
    if not 1 <= request.count <= MAX_COUNT:
        problems["count"] = f"Ask for 1 to {MAX_COUNT} outfits."
    anchors = list(dict.fromkeys(request.anchor_ids))
    if len(anchors) > MAX_ANCHORS:
        problems["anchor_item_ids"] = f"Start from up to {MAX_ANCHORS} pieces."
    elif anchors:
        found = outfits.owned_items(db, user, anchors)
        live = [item for item in found if item.archived_at is None]
        if len(live) != len(anchors):
            problems["anchor_item_ids"] = "Some of those items don't exist."
        elif len({item.slot for item in live}) != len(live):
            problems["anchor_item_ids"] = "Choose one item per slot."
    return problems


def load_wardrobe(db: Session, user: User, today: date) -> Wardrobe:
    """The person's items as the engine sees them, with the reference data around them."""
    rows = list(db.scalars(select(Item).where(Item.user_id == user.id, Item.archived_at.is_(None))))
    families = {family.id: family for family in db.scalars(select(ColorFamily))}
    categories = {
        category.id: category
        for category in db.scalars(
            select(Category).where(Category.id.in_({row.category_id for row in rows}))
        )
    }
    last_worn = {
        item_id: day
        for item_id, day in db.execute(
            select(WearLogItem.item_id, func.max(WearLog.worn_on))
            .join(WearLog, WearLog.id == WearLogItem.wear_log_id)
            .where(WearLog.user_id == user.id, WearLogItem.item_id.is_not(None))
            .group_by(WearLogItem.item_id)
        )
        if item_id is not None
    }
    names = ItemNames(db, user)
    items = tuple(
        _engine_item(
            row, names.display_name(row), families[row.color_primary], categories, last_worn
        )
        for row in rows
    )
    slots = reference.terms(db, "slot")
    return Wardrobe(
        items=items,
        templates=tuple(outfits.templates(db)),
        slot_kinds={slot.id: slot.role or "accessory" for slot in slots},
        group_names={group.id: group.name for group in reference.ordered(db, CategoryGroup)},
        slot_names={slot.id: slot.name for slot in slots},
        color_names={family.id: family.name for family in families.values()},
    )


def _engine_item(
    row: Item,
    name: str,
    family: ColorFamily,
    categories: dict[str, Category],
    last_worn: dict[uuid.UUID, date],
) -> EngineItem:
    category = categories.get(row.category_id)
    return EngineItem(
        id=str(row.id),
        owner_id=str(row.user_id),
        name=name,
        slot=row.slot,
        category_id=row.category_id,
        group_id=category.group_id if category else "",
        color_family=row.color_primary,
        color_neutrality=family.neutrality,
        color_hex=row.color_hex or family.hex,
        pattern=row.pattern,
        fabric=row.fabric,
        fit=row.fit,
        formality=row.formality,
        warmth=row.warmth,
        seasons=frozenset(row.seasons),
        style_tags=frozenset(row.style_tags),
        occasion_ids=frozenset(row.occasion_ids),
        status=row.status,
        archived=row.archived_at is not None,
        wears_before_wash=row.wears_before_wash,
        wears_since_wash=row.wears_since_wash,
        set_id=str(row.set_id) if row.set_id else None,
        last_worn_on=last_worn.get(row.id),
        traits=frozenset(category.traits) if category else frozenset(),
    )


def engine_occasion(row: Occasion) -> EngineOccasion:
    return EngineOccasion(
        id=row.id,
        name=row.name,
        formality_min=row.formality_min,
        formality_max=row.formality_max,
        prefers_groups=frozenset(row.prefers_groups),
    )


def _style(row: StyleProfile) -> Style:
    signals = row.signals
    return Style(
        id=row.id,
        name=row.name,
        colors=frozenset(signals.get("colors", [])),
        fabrics=frozenset(signals.get("fabrics", [])),
        patterns=frozenset(signals.get("patterns", [])),
        fits=frozenset(signals.get("fits", [])),
        categories=frozenset(signals.get("categories", [])),
        formality_center=signals.get("formality_center", 3),
    )


def _profile_styles(db: Session, profile: Profile | None) -> tuple[Style, ...]:
    if profile is None or not profile.style_profile_ids:
        return ()
    rows = {
        row.id: row
        for row in db.scalars(
            select(StyleProfile).where(StyleProfile.id.in_(profile.style_profile_ids))
        )
    }
    return tuple(_style(rows[id_]) for id_ in profile.style_profile_ids if id_ in rows)


def _recent_outfits(
    db: Session, user: User, today: date, wardrobe: Wardrobe
) -> tuple[tuple[date, frozenset[str]], ...]:
    """The core pieces of everything worn in the last week."""
    since = today - timedelta(days=DEFAULT.repeat_outfit_days)
    rows = db.execute(
        select(WearLog.id, WearLog.worn_on, WearLogItem.item_id, WearLogItem.slot)
        .join(WearLogItem, WearLogItem.wear_log_id == WearLog.id)
        .where(WearLog.user_id == user.id, WearLog.worn_on >= since)
        .order_by(WearLog.worn_on, WearLog.id)
    ).all()
    logs: dict[uuid.UUID, tuple[date, set[str]]] = {}
    for log_id, worn_on, item_id, slot in rows:
        entry = logs.setdefault(log_id, (worn_on, set()))
        if item_id is not None and wardrobe.slot_kinds.get(slot) == "core":
            entry[1].add(str(item_id))
    return tuple((worn_on, frozenset(core)) for worn_on, core in logs.values() if core)


def reactions(db: Session, user: User) -> list[learning.Reaction]:
    rows = db.scalars(
        select(SuggestionFeedback)
        .where(SuggestionFeedback.user_id == user.id)
        .order_by(SuggestionFeedback.created_at, SuggestionFeedback.id)
    )
    return [
        learning.Reaction(
            core_ids=tuple(str(item_id) for item_id in row.item_ids),
            verdict=row.verdict,
            reason=row.reason,
            item_id=str(row.item_id) if row.item_id else None,
        )
        for row in rows
    ]


def _preferences(
    db: Session, user: User, profile: Profile | None, wardrobe: Wardrobe
) -> Preferences:
    history = reactions(db, user)
    by_id = {item.id: item for item in wardrobe.items}
    groups, singles = learning.like_counts(history, by_id)
    return Preferences(
        avoided_colors=frozenset(profile.avoided_colors) if profile else frozenset(),
        preferred_colors=frozenset(profile.preferred_colors) if profile else frozenset(),
        fit_preference=profile.fit_preference if profile else None,
        pair_prefs=learning.pair_preferences(history),
        family_category_counts=groups,
        item_counts=singles,
    )


def pair_cache_for(user: User) -> dict[tuple[str, str], PairScore]:
    key = (user.id, user.wardrobe_version, ENGINE_VERSION)
    with _cache_lock:
        cache = _pair_caches.get(key)
        if cache is None:
            # An older version of this person's wardrobe is never needed again.
            for old in [k for k in _pair_caches if k[0] == user.id]:
                del _pair_caches[old]
            cache = {}
            _pair_caches[key] = cache
            while len(_pair_caches) > _CACHED_WARDROBES:
                _pair_caches.popitem(last=False)
        else:
            _pair_caches.move_to_end(key)
        return cache


# Reactions.


def find(db: Session, user: User, suggestion_id: uuid.UUID) -> Suggestion | None:
    return db.scalar(
        select(Suggestion).where(Suggestion.id == suggestion_id, Suggestion.user_id == user.id)
    )


def rate(
    db: Session,
    user: User,
    suggestion: Suggestion,
    verdict: str,
    reason: str | None,
    item_id: uuid.UUID | None,
) -> None:
    """Like, dislike, or skip, replacing any earlier rating of the same suggestion."""
    problems: dict[str, str] = {}
    if reason is not None and verdict != "dislike":
        problems["reason"] = "Only a dislike takes a reason."
    if reason == "item":
        if item_id is None:
            problems["item_id"] = "Choose the piece you don't like."
        elif item_id not in suggestion.item_ids:
            problems["item_id"] = "That piece isn't in this outfit."
    elif item_id is not None:
        problems["item_id"] = 'A piece goes with the reason "I don\'t like this piece".'
    if problems:
        raise SuggestInvalid(problems)
    clear_rating(db, suggestion)
    _record(db, user, suggestion, verdict, reason, item_id)
    suggestion.rating = verdict
    db.flush()


def clear_rating(db: Session, suggestion: Suggestion) -> None:
    for row in db.scalars(
        select(SuggestionFeedback).where(
            SuggestionFeedback.suggestion_id == suggestion.id,
            SuggestionFeedback.verdict.in_(RATINGS),
        )
    ):
        db.delete(row)
    suggestion.rating = None
    db.flush()


def save(db: Session, user: User, suggestion: Suggestion, fields: dict[str, Any]) -> Outfit:
    """Save the suggestion as an outfit, once; saving again returns the same outfit."""
    if suggestion.saved_outfit_id is not None:
        existing = outfits.find_outfit(db, user, suggestion.saved_outfit_id)
        if existing is not None:
            return existing
    values = {
        "item_ids": list(suggestion.item_ids),
        "name": fields.get("name"),
        "occasion_id": fields.get("occasion_id", suggestion.occasion_id),
        "is_favorite": bool(fields.get("is_favorite")),
        "source": "engine",
        "engine_version": suggestion.engine_version,
        "score": suggestion.score,
        "reasons": suggestion.reasons,
    }
    _require_fresh(db, user, suggestion)
    outfit = outfits.create_outfit(db, user, values)
    suggestion.saved_outfit_id = outfit.id
    if not _has_event(db, suggestion, "saved"):
        _record(db, user, suggestion, "saved", None, None)
    db.flush()
    return outfit


def wear_today(
    db: Session, user: User, suggestion: Suggestion, worn_on: date, note: str | None
) -> WearLog:
    """Log the suggestion as worn, once; logging again returns the same entry."""
    if suggestion.wear_log_id is not None:
        existing = wear.find_log(db, user, suggestion.wear_log_id)
        if existing is not None:
            return existing
    _require_fresh(db, user, suggestion)
    saved = (
        outfits.find_outfit(db, user, suggestion.saved_outfit_id)
        if suggestion.saved_outfit_id
        else None
    )
    log, _ = wear.log_wear(
        db,
        user,
        worn_on=worn_on,
        outfit_id=saved.id if saved else None,
        item_ids=None if saved else list(suggestion.item_ids),
        occasion_id=suggestion.occasion_id,
        note=note,
    )
    suggestion.wear_log_id = log.id
    suggestion.worn_on = log.worn_on
    if not _has_event(db, suggestion, "worn"):
        _record(db, user, suggestion, "worn", None, None)
    db.flush()
    return log


def _require_fresh(db: Session, user: User, suggestion: Suggestion) -> None:
    found = outfits.owned_items(db, user, list(suggestion.item_ids))
    if len(found) != len(suggestion.item_ids) or any(item.archived_at for item in found):
        raise SuggestionStale


def _has_event(db: Session, suggestion: Suggestion, verdict: str) -> bool:
    return (
        db.scalar(
            select(SuggestionFeedback.id).where(
                SuggestionFeedback.suggestion_id == suggestion.id,
                SuggestionFeedback.verdict == verdict,
            )
        )
        is not None
    )


def _record(
    db: Session,
    user: User,
    suggestion: Suggestion,
    verdict: str,
    reason: str | None,
    item_id: uuid.UUID | None,
) -> None:
    db.add(
        SuggestionFeedback(
            user_id=user.id,
            suggestion_id=suggestion.id,
            item_ids=sorted(suggestion.core_ids),
            occasion_id=suggestion.occasion_id,
            verdict=verdict,
            reason=reason,
            item_id=item_id,
            engine_version=suggestion.engine_version,
        )
    )


@dataclass(frozen=True)
class Acceptance:
    engine_version: str
    shown: int
    accepted: int

    @property
    def rate(self) -> float:
        return self.accepted / self.shown if self.shown else 0.0


def acceptance(db: Session) -> list[Acceptance]:
    """Saved, liked, or worn, divided by shown, per engine version (docs/ENGINE.md, 9)."""
    shown = dict(
        db.execute(
            select(Suggestion.engine_version, func.count()).group_by(Suggestion.engine_version)
        ).all()
    )
    accepted = dict(
        db.execute(
            select(
                SuggestionFeedback.engine_version,
                func.count(SuggestionFeedback.suggestion_id.distinct()),
            )
            .where(SuggestionFeedback.verdict.in_(learning.POSITIVE))
            .group_by(SuggestionFeedback.engine_version)
        ).all()
    )
    return [
        Acceptance(version, count, accepted.get(version, 0))
        for version, count in sorted(shown.items())
    ]
