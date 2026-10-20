"""Insights: wear, value, versatility, coverage, worn style, and what might go."""

import uuid
from datetime import date

from fastapi import APIRouter, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, SessionDep
from app.api.errors import ApiError, error_responses
from app.api.item_views import ItemBrief, Names, briefs
from app.api.shopping import StapleOut, staple_outs
from app.engine.config import DEFAULT, ENGINE_VERSION
from app.models import ColorFamily, Item, StyleProfile, User
from app.services import insights, reference, shopping, wear
from app.services import items as items_service
from app.services import profile as profiles

router = APIRouter(tags=["insights"])

# Coverage counts are shown up to this, then as "10+".
COVERAGE_CAP = 10


class WornOut(BaseModel):
    item: ItemBrief
    wears: int
    last_worn_on: date | None


class CostOut(BaseModel):
    item: ItemBrief
    # Minor units (paise), with the item's currency.
    price: int
    currency: str
    wears: int
    per_wear: int


class TallyOut(BaseModel):
    id: str
    name: str
    wears: int
    hex: str | None = None


class MonthOut(BaseModel):
    # YYYY-MM.
    month: str
    days: int


class VersatileOut(BaseModel):
    item: ItemBrief
    outfits: int


class OrphanOut(BaseModel):
    item: ItemBrief
    outfits: int
    # Why it's stranded and what would help, in one sentence.
    rescue: str


class CellOut(BaseModel):
    occasion_id: str
    season: str
    # Distinct good outfits, at most COVERAGE_CAP; capped is true when there are more.
    outfits: int
    capped: bool


class CoverageOut(BaseModel):
    occasion_ids: list[str]
    seasons: list[str]
    cells: list[CellOut]


class ShareOut(BaseModel):
    id: str
    name: str
    # Of the core pieces worn, weighted by wears, 0 to 1.
    share: float
    hex: str | None = None
    chosen: bool = False


class StyleOut(BaseModel):
    wears: int
    palette: list[ShareOut]
    formality: list[ShareOut]
    styles: list[ShareOut]


class DeclutterOut(BaseModel):
    item: ItemBrief
    last_worn_on: date | None
    added_on: date
    outfits: int


class InsightsOut(BaseModel):
    items: int
    # Days of wear logged, in all and in the last 30 days.
    logs: int
    days_logged_30: int
    # Rankings appear once this many days are logged.
    needed_logs: int
    enough: bool
    most_worn: list[WornOut]
    least_worn: list[WornOut]
    by_month: list[MonthOut]
    by_group: list[TallyOut]
    by_color: list[TallyOut]
    cheapest: list[CostOut]
    dearest: list[CostOut]
    # Worn items without a price: "add a price".
    needs_price: list[ItemBrief]
    # Null until the person has chosen occasions (Settings, or the usual week).
    versatile: list[VersatileOut] | None
    orphans: list[OrphanOut] | None
    coverage: CoverageOut | None
    style: StyleOut | None
    declutter: list[DeclutterOut]
    engine_version: str


def _view(db: Session, user: User, found: insights.Insights) -> InsightsOut:
    cards = briefs(db, Names(db, user), list(found.items_by_id))
    measures = found.measures
    versatile = orphans = None
    coverage = None
    if measures is not None:
        ranked = sorted(
            (
                (uuid.UUID(item_id), count)
                for item_id, count in measures.versatility.items()
                if count >= DEFAULT.orphan_below
            ),
            key=lambda entry: (-entry[1], str(entry[0])),
        )
        versatile = [VersatileOut(item=cards[i], outfits=n) for i, n in ranked[: insights.TOP]]
        orphans = [
            OrphanOut(
                item=cards[uuid.UUID(item_id)],
                outfits=measures.versatility[item_id],
                rescue=measures.rescues[item_id].text,
            )
            for item_id in measures.orphans
            if uuid.UUID(item_id) in cards
        ]
        coverage = CoverageOut(
            occasion_ids=[occasion.id for occasion in found.occasions],
            seasons=found.seasons,
            cells=[
                CellOut(
                    occasion_id=occasion.id,
                    season=season,
                    outfits=min(measures.coverage[(occasion.id, season)], COVERAGE_CAP),
                    capped=measures.coverage[(occasion.id, season)] > COVERAGE_CAP,
                )
                for occasion in found.occasions
                for season in found.seasons
            ],
        )
    style = None
    if found.style is not None and found.style.wears:
        families = {row.id: row for row in reference.ordered(db, ColorFamily)}
        names = {row.id: row.name for row in reference.ordered(db, StyleProfile)}
        levels = {term.id: term.name for term in reference.terms(db, "formality")}
        style = StyleOut(
            wears=found.style.wears,
            palette=[
                ShareOut(id=f, name=families[f].name, share=round(s, 4), hex=families[f].hex)
                for f, s in found.style.palette
            ],
            formality=[
                ShareOut(id=str(level), name=levels.get(str(level), str(level)), share=round(s, 4))
                for level, s in found.style.formality
            ],
            styles=[
                ShareOut(
                    id=style_id,
                    name=names.get(style_id, style_id),
                    share=round(s, 4),
                    chosen=style_id in found.chosen_styles,
                )
                for style_id, s in found.style.styles
            ],
        )
    return InsightsOut(
        items=found.items,
        logs=found.logs,
        days_logged_30=found.days_logged_30,
        needed_logs=insights.MIN_LOGS,
        enough=found.enough,
        most_worn=[
            WornOut(item=cards[e.item.id], wears=e.wears, last_worn_on=e.last_worn_on)
            for e in found.most_worn
        ],
        least_worn=[
            WornOut(item=cards[e.item.id], wears=e.wears, last_worn_on=e.last_worn_on)
            for e in found.least_worn
        ],
        by_month=[MonthOut(month=month, days=days) for month, days in found.by_month],
        by_group=[TallyOut(id=t.id, name=t.name, wears=t.wears) for t in found.by_group],
        by_color=[TallyOut(id=t.id, name=t.name, wears=t.wears, hex=t.hex) for t in found.by_color],
        cheapest=[_cost(cards, entry) for entry in found.cheapest],
        dearest=[_cost(cards, entry) for entry in found.dearest],
        needs_price=[cards[item.id] for item in found.needs_price],
        versatile=versatile,
        orphans=orphans,
        coverage=coverage,
        style=style,
        declutter=[
            DeclutterOut(
                item=cards[entry.item.id],
                last_worn_on=entry.last_worn_on,
                added_on=entry.item.created_at.date(),
                outfits=entry.versatility,
            )
            for entry in found.declutter
        ],
        engine_version=ENGINE_VERSION,
    )


def _cost(cards: dict[uuid.UUID, ItemBrief], entry: insights.CostPerWear) -> CostOut:
    return CostOut(
        item=cards[entry.item.id],
        price=entry.item.price or 0,
        currency=entry.item.currency,
        wears=entry.wears,
        per_wear=entry.per_wear,
    )


@router.get("/insights", response_model=InsightsOut, responses=error_responses(401))
def get_insights(user: CurrentUser, db: SessionDep) -> InsightsOut:
    """Every number here is counted from the person's own rows; nothing is estimated."""
    found = insights.gather(db, user, wear.today())
    db.commit()
    return _view(db, user, found)


class CellOutfitOut(BaseModel):
    items: list[ItemBrief]
    score: float


class CellDetailOut(BaseModel):
    occasion_id: str
    season: str
    # Good outfits here, best first (at most ten).
    outfits: list[CellOutfitOut]
    # With none: why, and the closest there are (not good enough to count).
    missing: list[str]
    closest: list[CellOutfitOut]
    # Staples that would add good outfits here.
    staples: list[StapleOut]


@router.get(
    "/insights/coverage/{occasion_id}/{season}",
    response_model=CellDetailOut,
    responses=error_responses(401, 404),
)
def coverage_cell(
    occasion_id: str, season: str, user: CurrentUser, db: SessionDep
) -> CellDetailOut:
    """One square of the coverage map, opened: its good outfits, or what's missing."""
    profile = profiles.get_or_create_profile(db, user)
    occasion = next((o for o in insights.occasions_for(db, profile) if o.id == occasion_id), None)
    seasons = [term.id for term in reference.terms(db, "season")]
    if occasion is None or season not in seasons:
        raise ApiError(404, "cell_not_found", "That isn't one of your occasions and seasons.")
    found = insights.cell(db, user, occasion, season, wear.today())
    ids = {i for outfit, _ in [*found.outfits, *found.closest] for i in outfit}
    rows = (
        list(db.scalars(select(Item).where(Item.user_id == user.id, Item.id.in_(ids))))
        if ids
        else []
    )
    names = Names(db, user)
    photos = items_service.primary_photos(db, [row.id for row in rows])
    cards = {row.id: names.brief(row, photos.get(row.id)) for row in rows}

    def outfit_out(entry: tuple[list[uuid.UUID], float]) -> CellOutfitOut:
        outfit, score = entry
        return CellOutfitOut(items=[cards[i] for i in outfit if i in cards], score=score)

    s = shopping.setting(db, user, wear.today())
    rows_by_id = {row.id: row for row in shopping.staples(db, s.profile)}
    staples = staple_outs(db, user, s, [rows_by_id[i] for i in found.staples if i in rows_by_id])
    db.commit()
    return CellDetailOut(
        occasion_id=occasion.id,
        season=season,
        outfits=[outfit_out(entry) for entry in found.outfits],
        missing=found.missing,
        closest=[outfit_out(entry) for entry in found.closest],
        staples=[staples[i] for i in found.staples if i in staples],
    )


class ChallengeOut(BaseModel):
    started_on: date
    ends_on: date
    day: int
    days: int
    finished: bool
    total: int
    worn: int
    # Not worn since it began, oldest first (at most UNWORN_SHOWN; the count is all of them).
    unworn: list[ItemBrief]
    unworn_count: int


class ChallengeStatus(BaseModel):
    # Null when no challenge is running.
    challenge: ChallengeOut | None
    days: int


UNWORN_SHOWN = 24


def _challenge_status(db: Session, user: User) -> ChallengeStatus:
    found = insights.challenge(db, user, wear.today())
    if found is None:
        return ChallengeStatus(challenge=None, days=insights.CHALLENGE_DAYS)
    shown = found.unworn[:UNWORN_SHOWN]
    cards = briefs(db, Names(db, user), [item.id for item in shown])
    return ChallengeStatus(
        challenge=ChallengeOut(
            started_on=found.started_on,
            ends_on=found.ends_on,
            day=found.day,
            days=insights.CHALLENGE_DAYS,
            finished=found.finished,
            total=found.total,
            worn=found.worn,
            unworn=[cards[item.id] for item in shown],
            unworn_count=len(found.unworn),
        ),
        days=insights.CHALLENGE_DAYS,
    )


@router.get("/insights/challenge", response_model=ChallengeStatus, responses=error_responses(401))
def get_challenge(user: CurrentUser, db: SessionDep) -> ChallengeStatus:
    """Wear what you own: progress counted from the wear log since the challenge began."""
    return _challenge_status(db, user)


@router.post(
    "/insights/challenge", response_model=ChallengeStatus, responses=error_responses(401, 403)
)
def start_challenge(user: CurrentUser, db: SessionDep) -> ChallengeStatus:
    """Start the challenge from today (or start it again)."""
    insights.start_challenge(db, user, wear.today())
    db.commit()
    return _challenge_status(db, user)


@router.delete(
    "/insights/challenge",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 403),
)
def stop_challenge(user: CurrentUser, db: SessionDep) -> None:
    insights.stop_challenge(db, user)
    db.commit()
