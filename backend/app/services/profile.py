"""The person's profile: sizes, measurements, style, budget, and where onboarding got to."""

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import CategoryGroup, ColorFamily, Occasion, Profile, StyleProfile, User
from app.services import reference

# Clearing one of these stores an empty list or object rather than null, so readers never
# have to tell "not answered" apart from "answered with nothing".
LIST_FIELDS = {
    "sections",
    "style_profile_ids",
    "preferred_colors",
    "avoided_colors",
    "occasion_ids",
}
OBJECT_FIELDS = {"measurements", "sizes", "category_budgets", "weekday_occasions"}
WEEKDAYS = {str(day) for day in range(7)}

ONBOARDING_STEPS = 6

UNKNOWN_CHOICE = "Choose one of the options shown."


class ProfileInvalid(Exception):
    """Some values refer to options that don't exist, or contradict each other."""

    def __init__(self, fields: dict[str, str]) -> None:
        super().__init__("Invalid profile")
        self.fields = fields


def get_or_create_profile(db: Session, user: User) -> Profile:
    profile = db.scalar(select(Profile).where(Profile.user_id == user.id))
    if profile is not None:
        return profile
    # Two first requests at once would both get here; the second insert quietly does nothing.
    db.execute(
        insert(Profile)
        .values(id=uuid.uuid7(), user_id=user.id)
        .on_conflict_do_nothing(index_elements=[Profile.user_id])
    )
    return db.scalars(select(Profile).where(Profile.user_id == user.id)).one()


def update_profile(db: Session, user: User, changes: dict[str, Any]) -> Profile:
    """Apply only the fields given. Null clears a field."""
    profile = get_or_create_profile(db, user)
    changes = dict(changes)
    for name in LIST_FIELDS & changes.keys():
        if changes[name] is None:
            changes[name] = []
    for name in OBJECT_FIELDS & changes.keys():
        if changes[name] is None:
            changes[name] = {}

    problems = _unknown_choices(db, changes)
    _place(changes, problems)
    loved = changes.get("preferred_colors", profile.preferred_colors)
    avoided = changes.get("avoided_colors", profile.avoided_colors)
    if set(loved) & set(avoided):
        problems["avoided_colors"] = (
            "A colour can't be both loved and avoided. Remove it from one of the lists."
        )
    if problems:
        raise ProfileInvalid(problems)

    for name, value in changes.items():
        setattr(profile, name, value)
    db.flush()
    return profile


def finish_onboarding(db: Session, user: User, *, skipped: bool) -> None:
    profile = get_or_create_profile(db, user)
    if user.onboarding_completed_at is None:
        user.onboarding_completed_at = datetime.now(UTC)
    profile.onboarding_skipped = skipped
    if not skipped:
        profile.onboarding_step = ONBOARDING_STEPS
    db.flush()


def dismiss_onboarding_reminder(db: Session, user: User) -> None:
    profile = get_or_create_profile(db, user)
    profile.onboarding_reminder_dismissed_at = datetime.now(UTC)
    db.flush()


def _unknown_choices(db: Session, changes: dict[str, Any]) -> dict[str, str]:
    """Field name -> message, for every id that isn't in the reference data."""
    problems: dict[str, str] = {}

    def check(field: str, values: Any, allowed: set[str]) -> None:
        if any(value not in allowed for value in values):
            problems[field] = UNKNOWN_CHOICE

    if "sections" in changes:
        check("sections", changes["sections"], reference.known_terms(db, "section"))
    if changes.get("fit_preference") is not None:
        check("fit_preference", [changes["fit_preference"]], reference.known_terms(db, "fit"))
    if "sizes" in changes:
        systems = reference.known_terms(db, "sizing_system")
        for slot, size in changes["sizes"].items():
            if size.get("system") is not None:
                check(f"sizes.{slot}.system", [size["system"]], systems)
    if "style_profile_ids" in changes:
        styles = reference.known_ids(db, StyleProfile)
        check("style_profile_ids", changes["style_profile_ids"], styles)
    if "preferred_colors" in changes or "avoided_colors" in changes:
        colors = reference.known_ids(db, ColorFamily)
        check("preferred_colors", changes.get("preferred_colors", []), colors)
        check("avoided_colors", changes.get("avoided_colors", []), colors)
    if "occasion_ids" in changes:
        check("occasion_ids", changes["occasion_ids"], reference.known_ids(db, Occasion))
    if "category_budgets" in changes:
        groups = reference.known_ids(db, CategoryGroup)
        for group in changes["category_budgets"]:
            check(f"category_budgets.{group}", [group], groups)
    if "weekday_occasions" in changes:
        occasions = reference.known_ids(db, Occasion)
        for day, occasion in changes["weekday_occasions"].items():
            if day not in WEEKDAYS or occasion not in occasions:
                problems["weekday_occasions"] = UNKNOWN_CHOICE
    return problems


def _place(changes: dict[str, Any], problems: dict[str, str]) -> None:
    """A place comes as a pair of coordinates, rounded to about a kilometre. Clearing the
    city clears them too."""
    if "city" in changes and changes["city"] is None:
        changes["latitude"] = changes["longitude"] = None
        return
    given = [name for name in ("latitude", "longitude") if changes.get(name) is not None]
    if len(given) == 1:
        problems["city"] = "Choose the place from the search results."
    for name in given:
        changes[name] = round(changes[name], 2)
