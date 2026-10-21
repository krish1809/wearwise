"""The owner's pages for the agents (docs/AGENTS.md): new trends to approve or reject, with their
sources, and the log of every run. For the accounts in ADMIN_EMAILS; everyone else gets the same
404 as a page that isn't there (D51)."""

import uuid
from datetime import UTC, date, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict
from sqlalchemy import select

from app.api.deps import CurrentUser, SessionDep, SettingsDep
from app.api.errors import ApiError, error_responses
from app.models import ColorFamily, Trend, TrendSource, User
from app.services import agent_runs, trends

router = APIRouter(prefix="/admin", tags=["admin"])

TrendStatus = Literal["pending", "approved", "rejected", "expired"]
RunKind = Literal["trend_scout", "weekly_digest"]


def owner(user: CurrentUser, settings: SettingsDep) -> User:
    if user.email not in settings.admins:
        raise ApiError(404, "not_found", "Not Found")
    return user


OwnerDep = Annotated[User, Depends(owner)]


class Named(BaseModel):
    id: str
    name: str


class ColorOut(Named):
    hex: str | None


class SourceOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    url: str
    domain: str
    title: str
    published_on: date
    quote: str


class TrendOut(BaseModel):
    id: uuid.UUID
    name: str
    summary: str
    why_now: str
    status: str
    first_seen_at: datetime
    last_seen_at: datetime
    decided_at: datetime | None
    categories: list[Named]
    colors: list[ColorOut]
    fabrics: list[Named]
    patterns: list[Named]
    fits: list[Named]
    seasons: list[Named]
    sections: list[Named]
    styles: list[Named]
    sources: list[SourceOut]


class TrendsOut(BaseModel):
    trends: list[TrendOut]
    # How many trends have each status, for the page's tabs.
    counts: dict[str, int]


class TrendDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    status: Literal["approved", "rejected", "pending"]


class RunOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    kind: str
    trigger: str
    status: str
    started_at: datetime
    finished_at: datetime | None
    search_credits: int
    tokens_in: int
    tokens_out: int
    cost_micro_usd: int
    stopped_by: str | None
    errors: list[str]
    # Each step's counts: the queries, what was read and skipped, what was kept and dropped.
    steps: dict[str, Any]


class RunsOut(BaseModel):
    runs: list[RunOut]
    credits_this_month: int
    credit_cap: int


def _trend_out(
    trend: Trend,
    sources: list[TrendSource],
    allowed: trends.Allowed,
    hexes: dict[str, str | None],
) -> TrendOut:
    def named(ids: list[str], names: dict[str, str]) -> list[Named]:
        return [Named(id=i, name=names.get(i, i)) for i in ids]

    return TrendOut(
        id=trend.id,
        name=trend.name,
        summary=trend.summary,
        why_now=trend.why_now,
        status=trend.status,
        first_seen_at=trend.first_seen_at,
        last_seen_at=trend.last_seen_at,
        decided_at=trend.decided_at,
        categories=named(trend.category_ids, allowed.categories),
        colors=[
            ColorOut(id=c, name=allowed.colors.get(c, c), hex=hexes.get(c))
            for c in trend.color_families
        ],
        fabrics=named(trend.fabrics, allowed.fabrics),
        patterns=named(trend.patterns, allowed.patterns),
        fits=named(trend.fits, allowed.fits),
        seasons=named(trend.seasons, allowed.seasons),
        sections=named(trend.sections, allowed.sections),
        styles=named(trend.style_profile_ids, allowed.styles),
        sources=[SourceOut.model_validate(s) for s in sources],
    )


def _hexes(db: SessionDep) -> dict[str, str | None]:
    return {c.id: c.hex for c in db.scalars(select(ColorFamily))}


@router.get("/trends", response_model=TrendsOut, responses=error_responses(401, 404))
def list_trends(_: OwnerDep, db: SessionDep, status: TrendStatus = "pending") -> TrendsOut:
    """Trends the Trend Scout found, with every source and quote, to approve or reject."""
    found = trends.listed(db, status)
    sources = trends.sources_for(db, [t.id for t in found])
    allowed = trends.allowed(db)
    hexes = _hexes(db)
    return TrendsOut(
        trends=[_trend_out(t, sources[t.id], allowed, hexes) for t in found],
        counts=trends.counts(db),
    )


@router.patch(
    "/trends/{trend_id}",
    response_model=TrendOut,
    responses=error_responses(401, 403, 404, 422),
)
def decide_trend(trend_id: uuid.UUID, body: TrendDecision, _: OwnerDep, db: SessionDep) -> TrendOut:
    """Approve or reject a trend (only approved ones reach a digest), or put it back."""
    trend = trends.find(db, trend_id)
    if trend is None:
        raise ApiError(404, "trend_not_found", "That trend doesn't exist.")
    trends.decide(trend, body.status, datetime.now(UTC))
    db.commit()
    sources = trends.sources_for(db, [trend.id])[trend.id]
    return _trend_out(trend, sources, trends.allowed(db), _hexes(db))


@router.get("/runs", response_model=RunsOut, responses=error_responses(401, 404))
def list_runs(
    _: OwnerDep, db: SessionDep, settings: SettingsDep, kind: RunKind = "trend_scout"
) -> RunsOut:
    """The latest runs of one agent, newest first, with what each step did."""
    return RunsOut(
        runs=[RunOut.model_validate(r) for r in agent_runs.latest(db, kind)],
        credits_this_month=trends.credits_used(db, datetime.now(UTC)),
        credit_cap=settings.search_monthly_credit_cap,
    )
