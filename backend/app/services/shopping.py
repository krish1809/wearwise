"""Shopping: candidates, what each would add, gaps, the starter capsule, the budget split,
and the Style Guide (docs/SHOPPING.md, part 1).

Candidates are described like items, so the engine can treat each as if it were owned and
measure what it adds (app/engine/shopping.py). Every query filters by the person. A
candidate's analysis is kept on its row with a key of everything it depends on (the
wardrobe, the engine, occasions, styles and colours, reactions, sections, budgets, and the
candidate's own attributes and price) and worked out again when the key changes.
"""

import hashlib
import json
import uuid
from collections import OrderedDict
from dataclasses import dataclass, replace
from datetime import UTC, date, datetime
from threading import Lock
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.engine import shopping as engine
from app.engine import types as engine_types
from app.engine.config import DEFAULT, ENGINE_VERSION
from app.engine.generate import score_outfit
from app.engine.insights import Measures, steady
from app.engine.outfits import Piece, check_outfit
from app.engine.types import Context, EngineItem, Wardrobe
from app.engine.types import Occasion as EngineOccasion
from app.models import (
    Archetype,
    Candidate,
    Category,
    CategoryGroup,
    ColorFamily,
    GuideEntry,
    Item,
    ItemImage,
    Occasion,
    Profile,
    StyleProfile,
    User,
    VocabularyTerm,
    WearLog,
    WearLogItem,
)
from app.services import categories, insights, items, reference, suggestions
from app.services import profile as profiles
from app.services.item_names import ItemNames

STATUSES = ("considering", "buy_next", "later", "skipped", "purchased")
# Statuses a person sets directly; "purchased" comes from buying it.
OPEN_STATUSES = ("considering", "buy_next", "later", "skipped")
# Candidates the budget split weighs.
STILL_WANTED = ("considering", "buy_next", "later")
CANDIDATE = "candidate:"
STAPLE = "archetype:"
MAX_CANDIDATES = 200
# The budget split looks at the most recent this many candidates with a price.
MAX_SPLIT = 30
# A projected cost per wear needs this many days of wear logs, and similar pieces owned
# for at least MIN_DAYS_OWNED of them.
HISTORY_DAYS = 30
MIN_DAYS_OWNED = 14

_CACHED = 8
_gaps: OrderedDict[str, list[engine.Gap]] = OrderedDict()
_lock = Lock()


class CandidateInvalid(Exception):
    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__("Invalid candidate")
        self.fields = fields


class TooManyCandidates(Exception):
    pass


class NotForSale(Exception):
    """The candidate was already bought."""


@dataclass
class Setting:
    """Everything an analysis needs, loaded once per request."""

    user: User
    profile: Profile
    occasions: list[Occasion]
    seasons: list[str]
    wardrobe: Wardrobe
    base: Context
    # None until the person has chosen occasions.
    before: Measures | None
    key: str
    families: dict[str, ColorFamily]
    categories: dict[str, Category]
    groups: dict[str, str]

    @property
    def engine_occasions(self) -> list[EngineOccasion]:
        return [suggestions.engine_occasion(occasion) for occasion in self.occasions]

    def pairs(self) -> dict[tuple[str, str], Any]:
        # A copy: candidates and staples change without the wardrobe version changing, so
        # their pair scores must not stay in the shared cache.
        return dict(suggestions.pair_cache_for(self.user))


def setting(db: Session, user: User, today: date) -> Setting:
    profile = profiles.get_or_create_profile(db, user)
    occasions = insights.occasions_for(db, profile)
    seasons = [term.id for term in reference.terms(db, "season")]
    wardrobe = suggestions.load_wardrobe(db, user, today)
    base = suggestions.base_context(db, user, profile, wardrobe, today)
    before = (
        insights.measures_for(db, user, profile, occasions, seasons, today) if occasions else None
    )
    key = (
        *insights.fingerprint(db, user, profile, occasions),
        tuple(seasons),
        tuple(sorted(profile.sections)),
        tuple(sorted(profile.category_budgets.items())),
    )
    return Setting(
        user=user,
        profile=profile,
        occasions=occasions,
        seasons=seasons,
        wardrobe=wardrobe,
        base=base,
        before=before,
        key=_hash(key),
        families={family.id: family for family in reference.ordered(db, ColorFamily)},
        categories={category.id: category for category in categories.list_categories(db, user)},
        groups={group.id: group.name for group in reference.ordered(db, CategoryGroup)},
    )


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(value, default=str).encode()).hexdigest()[:32]


# Candidates and staples as the engine sees them.


def _engine_item(
    s: Setting,
    item_id: str,
    name: str,
    category_id: str,
    color: str,
    color_hex: str | None,
    pattern: str,
    fabric: str | None,
    fit: str | None,
    formality: int,
    warmth: int,
    seasons: list[str],
) -> EngineItem:
    category = s.categories[category_id]
    family = s.families[color]
    return EngineItem(
        id=item_id,
        owner_id=str(s.user.id),
        name=name,
        slot=category.slot,
        category_id=category_id,
        group_id=category.group_id,
        color_family=color,
        color_neutrality=family.neutrality,
        color_hex=color_hex or family.hex,
        pattern=pattern,
        fabric=fabric,
        fit=fit,
        formality=formality,
        warmth=warmth,
        seasons=frozenset(seasons),
        wears_before_wash=category.wears_before_wash,
        traits=frozenset(category.traits),
    )


def candidate_item(s: Setting, candidate: Candidate, name: str) -> EngineItem:
    return _engine_item(
        s,
        CANDIDATE + str(candidate.id),
        name,
        candidate.category_id,
        candidate.color_primary,
        candidate.color_hex,
        candidate.pattern,
        candidate.fabric,
        candidate.fit,
        candidate.formality,
        candidate.warmth,
        candidate.seasons,
    )


def staple_item(s: Setting, staple: Archetype) -> EngineItem:
    return _engine_item(
        s,
        STAPLE + staple.id,
        staple.name,
        staple.category_id,
        staple.color,
        None,
        staple.pattern,
        staple.fabric,
        None,
        staple.formality,
        staple.warmth,
        staple.seasons,
    )


def staples(db: Session, profile: Profile) -> list[Archetype]:
    """The staples for the person's sections (all of them when none are chosen)."""
    rows = list(db.scalars(select(Archetype).order_by(Archetype.position)))
    if not profile.sections:
        return rows
    return [row for row in rows if set(row.sections) & set(profile.sections)]


# Candidates.


def list_candidates(db: Session, user: User) -> list[Candidate]:
    query = select(Candidate).where(Candidate.user_id == user.id)
    return list(db.scalars(query.order_by(Candidate.created_at.desc(), Candidate.id.desc())))


def find(db: Session, user: User, candidate_id: uuid.UUID) -> Candidate | None:
    query = select(Candidate).where(Candidate.id == candidate_id, Candidate.user_id == user.id)
    return db.scalar(query)


def create(db: Session, user: User, fields: dict[str, Any]) -> Candidate:
    """Add something to consider. Formality and warmth start from the category's defaults."""
    count = db.scalar(select(func.count()).where(Candidate.user_id == user.id)) or 0
    if count >= MAX_CANDIDATES:
        raise TooManyCandidates
    fields = dict(fields)
    photo_id = fields.pop("photo_id", None)
    category = categories.find_category(db, user, fields.get("category_id") or "")
    problems = _check(db, user, fields)
    if category is None:
        problems["category_id"] = items.UNKNOWN_CHOICE
    photo = items.usable_photo(db, user, photo_id, problems)
    if problems or category is None:
        raise CandidateInvalid(problems)
    if fields.get("formality") is None:
        fields["formality"] = category.formality_default
    if fields.get("warmth") is None:
        fields["warmth"] = category.warmth
    for name in ("pattern", "status", "source"):
        if fields.get(name) is None:
            fields.pop(name, None)
    if photo is not None and not fields.get("color_hex"):
        fields["color_hex"] = photo.dominant_hex
    if fields.get("price") is not None:
        fields["price_checked_at"] = datetime.now(UTC)
    candidate = Candidate(user_id=user.id, slot=category.slot, **fields)
    db.add(candidate)
    db.flush()
    if photo is not None:
        photo.candidate_id = candidate.id
    db.flush()
    return candidate


def from_staple(db: Session, user: User, staple_id: str) -> Candidate:
    """Put a staple from gaps or the capsule on the list, as a description to shop for."""
    staple = db.get(Archetype, staple_id)
    if staple is None:
        raise CandidateInvalid({"archetype_id": items.UNKNOWN_CHOICE})
    return create(
        db,
        user,
        {
            "source": "archetype",
            "archetype_id": staple.id,
            "name": staple.name,
            "category_id": staple.category_id,
            "color_primary": staple.color,
            "pattern": staple.pattern,
            "fabric": staple.fabric,
            "formality": staple.formality,
            "warmth": staple.warmth,
            "seasons": staple.seasons,
        },
    )


def update(db: Session, user: User, candidate: Candidate, changes: dict[str, Any]) -> list[str]:
    """Apply the fields given; null clears an optional one. Returns photo files to delete."""
    if candidate.status == "purchased":
        raise NotForSale
    changes = dict(changes)
    problems = {
        name: "This can't be empty."
        for name in items.REQUIRED - {"status"}
        if name in changes and changes[name] is None
    }
    if "status" in changes and changes["status"] is None:
        problems["status"] = "This can't be empty."
    for name in problems:
        del changes[name]
    problems.update(_check(db, user, changes))
    category = None
    if "category_id" in changes:
        category = categories.find_category(db, user, changes["category_id"])
        if category is None:
            problems["category_id"] = items.UNKNOWN_CHOICE
    replacing_photo = "photo_id" in changes
    new_photo_id = changes.pop("photo_id", None)
    new_photo = items.usable_photo(db, user, new_photo_id, problems) if new_photo_id else None
    if problems:
        raise CandidateInvalid(problems)
    if category is not None:
        candidate.slot = category.slot
    if "price" in changes and changes["price"] != candidate.price:
        candidate.price_checked_at = datetime.now(UTC) if changes["price"] is not None else None
    for name, value in changes.items():
        setattr(candidate, name, value)
    if candidate.status not in STILL_WANTED:
        candidate.remind_on = None
    keys: list[str] = []
    if replacing_photo:
        for old in _photos(db, candidate):
            keys += [old.storage_key, old.thumb_key]
            db.delete(old)
        if new_photo is not None:
            new_photo.candidate_id = candidate.id
    db.flush()
    return keys


def reminder_due(candidate: Candidate, today: date) -> bool:
    """Whether to ask "Still want it?": the reminder day has come and it's still wanted."""
    return (
        candidate.remind_on is not None
        and candidate.remind_on <= today
        and candidate.status in STILL_WANTED
    )


def delete(db: Session, candidate: Candidate) -> list[str]:
    keys = [key for image in _photos(db, candidate) for key in (image.storage_key, image.thumb_key)]
    db.delete(candidate)
    db.flush()
    return keys


def purchase(db: Session, user: User, candidate: Candidate, fields: dict[str, Any]) -> Item:
    """Bought: the candidate becomes a wardrobe item, with its photo, and is marked
    purchased. `fields` may give the price paid, the day, and the size."""
    if candidate.status == "purchased":
        raise NotForSale
    price = fields.get("price", candidate.price)
    item = items.create_item(
        db,
        user,
        {
            "name": candidate.name,
            "brand": candidate.brand,
            "size_label": fields.get("size_label", candidate.size_label),
            "category_id": candidate.category_id,
            "color_primary": candidate.color_primary,
            "color_secondary": candidate.color_secondary,
            "color_hex": candidate.color_hex,
            "pattern": candidate.pattern,
            "fabric": candidate.fabric,
            "fit": candidate.fit,
            "formality": candidate.formality,
            "warmth": candidate.warmth,
            "seasons": candidate.seasons,
            "price": price,
            "currency": candidate.currency,
            "purchased_on": fields.get("purchased_on"),
        },
    )
    for image in _photos(db, candidate):
        image.candidate_id = None
        image.item_id = item.id
    candidate.status = "purchased"
    candidate.remind_on = None
    candidate.item_id = item.id
    db.flush()
    return item


def primary_photos(db: Session, candidate_ids: list[uuid.UUID]) -> dict[uuid.UUID, ItemImage]:
    if not candidate_ids:
        return {}
    query = select(ItemImage).where(ItemImage.candidate_id.in_(candidate_ids))
    return {image.candidate_id: image for image in db.scalars(query) if image.candidate_id}


def _photos(db: Session, candidate: Candidate) -> list[ItemImage]:
    return list(db.scalars(select(ItemImage).where(ItemImage.candidate_id == candidate.id)))


def _check(db: Session, user: User, fields: dict[str, Any]) -> dict[str, str]:
    problems = items.check_fields(db, user, {k: v for k, v in fields.items() if k != "status"})
    status = fields.get("status")
    if status is not None and status not in OPEN_STATUSES:
        problems["status"] = items.UNKNOWN_CHOICE
    return problems


# What a candidate would add.


def analysis(db: Session, candidate: Candidate, s: Setting, today: date) -> dict[str, Any] | None:
    """The analysis and verdict, from the candidate's row when its key still matches, else
    worked out and stored. None until the person has chosen occasions."""
    if s.before is None:
        return None
    key = _hash([s.key, _attributes(candidate)])
    if candidate.analysis_key == key and candidate.analysis is not None:
        return candidate.analysis
    names = ItemNames(db, s.user)
    item = candidate_item(s, candidate, names.display_name(candidate))
    occasions = s.engine_occasions
    found = engine.analyse(
        s.wardrobe, s.base, occasions, s.seasons, s.before, item, DEFAULT, s.pairs()
    )
    group_id = s.categories[candidate.category_id].group_id
    usual = s.profile.category_budgets.get(group_id)
    within = None if candidate.price is None or usual is None else candidate.price <= usual
    line = engine.buy_line(gaps(db, s))
    judged = engine.verdict(
        found,
        item,
        {owned.id: owned.name for owned in s.wardrobe.items},
        occasions,
        s.before.coverage,
        line,
        within,
        s.groups.get(group_id, ""),
        frozenset(s.profile.avoided_colors),
    )
    price = candidate.price
    result = {
        "kind": found.kind,
        "verdict": judged.code,
        "reasons": [
            {"code": reason.code, "kind": reason.kind, "text": reason.text}
            for reason in judged.reasons
        ],
        "new_outfits": found.new_outfits,
        "coverage_gain": found.coverage_gain,
        "cells": [
            {
                "occasion_id": occasion.id,
                "season": season,
                "before": s.before.coverage[(occasion.id, season)],
                "added": found.added.get((occasion.id, season), 0),
            }
            for occasion in s.occasions
            for season in s.seasons
        ],
        "matches": [{"item_id": i, "score": score} for i, score in found.matches],
        "closest_id": found.closest_id,
        "redundancy": found.redundancy,
        "rescued": list(found.rescued),
        "examples": [
            {"template_id": template_id, "item_ids": list(core)}
            for template_id, core in found.examples
        ],
        "cost_per_new_outfit": (
            round(price / found.new_outfits)
            if price is not None and found.kind == "core" and found.new_outfits
            else None
        ),
        "projected": _projected(db, s.user, candidate, today),
        "usual_spend": usual,
        "within_budget": within,
        "engine_version": ENGINE_VERSION,
    }
    candidate.analysis = result
    candidate.analysis_key = key
    db.flush()
    return result


def fresh_verdict(candidate: Candidate, s: Setting) -> str | None:
    """The stored verdict if it's still current, for lists; None if it needs working out."""
    if candidate.analysis is None or s.before is None:
        return None
    if candidate.analysis_key != _hash([s.key, _attributes(candidate)]):
        return None
    return str(candidate.analysis["verdict"])


def _attributes(candidate: Candidate) -> list[object]:
    return [
        str(candidate.id),
        candidate.category_id,
        candidate.color_primary,
        candidate.color_hex,
        candidate.pattern,
        candidate.fabric,
        candidate.fit,
        candidate.formality,
        candidate.warmth,
        sorted(candidate.seasons),
        candidate.price,
    ]


def _projected(db: Session, user: User, candidate: Candidate, today: date) -> dict[str, int] | None:
    """An estimate of cost per wear: the price over the wears a year the person's other
    pieces of the same category get. Hidden without a price, a month of wear logs, or
    similar pieces to go by."""
    if candidate.price is None:
        return None
    first, logs = db.execute(
        select(func.min(WearLog.worn_on), func.count()).where(WearLog.user_id == user.id)
    ).one()
    if first is None or logs < insights.MIN_LOGS or (today - first).days < HISTORY_DAYS:
        return None
    similar = list(
        db.scalars(
            select(Item).where(
                Item.user_id == user.id,
                Item.category_id == candidate.category_id,
                Item.archived_at.is_(None),
                Item.status != "retired",
            )
        )
    )
    if not similar:
        return None
    worn = dict(
        db.execute(
            select(WearLogItem.item_id, func.count())
            .where(WearLogItem.item_id.in_([item.id for item in similar]))
            .group_by(WearLogItem.item_id)
        ).all()
    )
    rates = []
    for item in similar:
        days = (today - max(first, item.created_at.date())).days
        if days >= MIN_DAYS_OWNED:
            rates.append(worn.get(item.id, 0) / days)
    if not rates:
        return None
    yearly = sum(rates) / len(rates) * 365
    if yearly < 1:
        return None
    return {
        "wears_a_year": round(yearly),
        "per_wear": round(candidate.price / yearly),
        "similar": len(rates),
    }


# Gaps, the capsule, and the budget split.


def gaps(db: Session, s: Setting) -> list[engine.Gap]:
    """What would add the most, cached per setting. Empty until occasions are chosen."""
    if s.before is None:
        return []
    with _lock:
        cached = _gaps.get(s.key)
        if cached is not None:
            _gaps.move_to_end(s.key)
            return cached
    pool = [staple_item(s, row) for row in staples(db, s.profile)]
    found = engine.gaps(
        s.wardrobe, s.base, s.engine_occasions, s.seasons, s.before, pool, DEFAULT, s.pairs()
    )
    with _lock:
        _gaps[s.key] = found
        while len(_gaps) > _CACHED:
            _gaps.popitem(last=False)
    return found


@dataclass(frozen=True)
class CapsulePlan:
    steps: list[engine.Step]
    staples: dict[str, Archetype]
    # Groups of clothing with no usual spend set, so their staples couldn't be priced.
    unpriced_groups: list[str]


def capsule(db: Session, s: Setting, budget: int | None) -> CapsulePlan | None:
    if s.before is None:
        return None
    rows = {STAPLE + row.id: row for row in staples(db, s.profile)}
    pool = [staple_item(s, row) for row in rows.values()]
    costs = {item.id: s.profile.category_budgets.get(item.group_id) for item in pool}
    steps = engine.capsule(
        s.wardrobe,
        s.base,
        s.engine_occasions,
        s.seasons,
        s.before,
        pool,
        costs,
        budget,
        DEFAULT,
        s.pairs(),
    )
    core = {item.group_id for item in pool if s.wardrobe.slot_kinds.get(item.slot) == "core"}
    unpriced = [
        group for group in s.groups if group in core and group not in s.profile.category_budgets
    ]
    return CapsulePlan(steps, rows, unpriced)


@dataclass(frozen=True)
class SplitPlan:
    split: engine.Split | None
    considered: list[Candidate]
    # Open candidates without a price, which the split can't weigh.
    unpriced: list[Candidate]


def split(db: Session, s: Setting, budget: int) -> SplitPlan | None:
    """Which of the open candidates to buy for the most coverage within the budget."""
    if s.before is None:
        return None
    open_ = [c for c in list_candidates(db, s.user) if c.status in STILL_WANTED]
    priced = [c for c in open_ if c.price is not None][:MAX_SPLIT]
    unpriced = [c for c in open_ if c.price is None]
    if not priced:
        return SplitPlan(None, [], unpriced)
    names = ItemNames(db, s.user)
    pieces = [(candidate_item(s, c, names.display_name(c)), c.price or 0) for c in priced]
    found = engine.budget_split(
        s.wardrobe,
        s.base,
        s.engine_occasions,
        s.seasons,
        s.before,
        pieces,
        budget,
        DEFAULT,
        s.pairs(),
    )
    return SplitPlan(found, priced, unpriced)


def try_on(
    db: Session,
    s: Setting,
    candidate: Candidate,
    item_ids: list[uuid.UUID],
    occasion: Occasion | None,
) -> tuple[engine_types.ScoredOutfit | None, str | None]:
    """Score the candidate with pieces the person owns, as if it were theirs, for an
    occasion (or the pieces' own level of dress): the outfit's score and reasons, or what's
    still needed to make a whole outfit."""
    names = ItemNames(db, s.user)
    item = candidate_item(s, candidate, names.display_name(candidate))
    owned = {i.id: i for i in s.wardrobe.items if i.owner_id == str(s.user.id)}
    chosen = [owned[str(i)] for i in item_ids if str(i) in owned]
    if len(chosen) != len(item_ids):
        return None, "Some of those pieces aren't in your wardrobe."
    pieces = [item, *[p for p in chosen if p.slot != item.slot]]
    check = check_outfit(
        [Piece(key=p.id, slot=p.slot, category_id=p.category_id) for p in pieces],
        s.wardrobe.templates,
    )
    if not check.complete:
        slot_names = s.wardrobe.slot_names
        needed = ", ".join(slot_names.get(slot, slot).lower() for slot in check.missing)
        return None, f"Still needed: {needed}." if needed else "These don't make one outfit."
    wardrobe = replace(s.wardrobe, items=(*s.wardrobe.items, item))
    context = replace(s.base, occasion=suggestions.engine_occasion(occasion) if occasion else None)
    scored = score_outfit(wardrobe, context, [p.id for p in pieces], DEFAULT, s.pairs())
    return scored, None


def without_cache() -> None:
    """For tests: forget cached gaps."""
    with _lock:
        _gaps.clear()


# The Style Guide.


@dataclass(frozen=True)
class StylePiece:
    staple: Archetype
    # The owned piece close enough to count as having it.
    owned: Item | None


@dataclass(frozen=True)
class StyleGuide:
    style: StyleProfile
    pieces: list[StylePiece]


def fabric_guide(db: Session) -> list[tuple[VocabularyTerm, GuideEntry]]:
    terms = {term.id: term for term in reference.terms(db, "fabric")}
    entries = db.scalars(
        select(GuideEntry).where(GuideEntry.kind == "fabric").order_by(GuideEntry.position)
    )
    return [(terms[entry.id], entry) for entry in entries if entry.id in terms]


def colour_guide(db: Session) -> tuple[list[GuideEntry], list[ColorFamily]]:
    entries = list(
        db.scalars(
            select(GuideEntry).where(GuideEntry.kind == "colour").order_by(GuideEntry.position)
        )
    )
    neutrals = [
        family
        for family in reference.ordered(db, ColorFamily)
        if family.neutrality >= DEFAULT.neutral_neutrality
    ]
    return entries, neutrals


def style_guides(db: Session, user: User, today: date) -> list[StyleGuide]:
    """Each style profile with the staples it's built on, and which of them the person
    already has (an owned piece alike enough to count as a duplicate)."""
    s = setting(db, user, today)
    owned = [item for item in steady(s.wardrobe).items if item.owner_id == str(user.id)]
    rows = {str(row.id): row for row in db.scalars(select(Item).where(Item.user_id == user.id))}
    all_staples = list(db.scalars(select(Archetype).order_by(Archetype.position)))
    wanted = set(s.profile.sections)
    guides = []
    for style in reference.ordered(db, StyleProfile):
        pieces = []
        for staple in all_staples:
            if style.id not in staple.styles:
                continue
            if wanted and not set(staple.sections) & wanted:
                continue
            near, alike = engine.closest(staple_item(s, staple), owned)
            have = rows.get(near.id) if near and alike >= DEFAULT.duplicate_at else None
            pieces.append(StylePiece(staple, have))
        guides.append(StyleGuide(style, pieces))
    return guides
