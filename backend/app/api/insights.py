"""Insights: wear, value, versatility, coverage, worn style, and what might go."""

import uuid
from datetime import date

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, SessionDep
from app.api.errors import error_responses
from app.api.item_views import ItemBrief, Names, briefs
from app.engine.config import DEFAULT, ENGINE_VERSION
from app.models import ColorFamily, StyleProfile, User
from app.services import insights, reference, wear

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
