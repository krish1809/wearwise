"""The weekly picks (docs/AGENTS.md, section 5): the latest digest, working out this week's now
without emailing it, and "not for me"."""

import uuid
from datetime import UTC, datetime, timedelta
from typing import Literal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.deps import CurrentUser, SessionDep
from app.api.errors import ApiError, error_responses
from app.api.item_views import ItemBrief, Names, briefs
from app.models import ColorFamily, Digest, DigestPick, Item, User
from app.services import digests, rate_limit

router = APIRouter(tags=["digests"])

# Working the picks out runs the purchase analysis several times, so it's limited.
PREVIEWS_PER_USER = rate_limit.Limit(attempts=10, window=timedelta(hours=1))


class PickReasonOut(BaseModel):
    code: str
    kind: Literal["positive", "caution"]
    text: str


class ShopLinkOut(BaseModel):
    shop_id: str
    shop: str
    url: str


class PickOut(BaseModel):
    id: uuid.UUID
    position: int
    # buy: a piece worth looking for; owned: one the person already has.
    kind: Literal["buy", "owned"]
    trend_name: str
    trend_summary: str
    name: str
    category_id: str
    color_primary: str
    color_hex: str | None
    # The sentence for it, from its numbers.
    text: str
    # A piece to buy: the purchase analysis's verdict and reasons.
    verdict: Literal["buy", "consider"] | None
    new_outfits: int | None
    reasons: list[PickReasonOut]
    # The person's own pieces it names (an owned pick first), with their photos.
    items: list[ItemBrief]
    query: str | None
    links: list[ShopLinkOut]
    # The person's usual spend for its kind of clothing, in paise.
    usual_spend: int | None
    not_for_me: bool


class DigestOut(BaseModel):
    id: uuid.UUID
    week: str
    # built, nothing, sent, held, or failed.
    status: str
    # Why there are no picks, as a sentence.
    note: str | None
    season: str
    subject: str
    intro: str
    worked_out_at: datetime
    sent_at: datetime | None
    picks: list[PickOut]


def _pick_out(
    pick: DigestPick,
    found: dict[uuid.UUID, ItemBrief],
    hexes: dict[str, str | None],
) -> PickOut:
    analysis = pick.analysis or {}
    verdict = analysis.get("verdict")
    return PickOut(
        id=pick.id,
        position=pick.position,
        kind="owned" if pick.kind == "owned" else "buy",
        trend_name=pick.trend_name,
        trend_summary=pick.trend_summary,
        name=pick.name,
        category_id=pick.category_id,
        color_primary=pick.color_primary,
        color_hex=hexes.get(pick.color_primary),
        text=pick.text,
        verdict=verdict if verdict in ("buy", "consider") else None,
        new_outfits=analysis.get("new_outfits"),
        reasons=[PickReasonOut(**reason) for reason in analysis.get("reasons", [])],
        items=[found[i] for i in pick.item_ids if i in found],
        query=pick.query,
        links=[ShopLinkOut(**link) for link in pick.links],
        usual_spend=pick.usual_spend,
        not_for_me=pick.verdict == "not_for_me",
    )


def _digest_out(db: Session, user: User, digest: Digest) -> DigestOut:
    picks = digests.picks_of(db, digest)
    wanted = [i for pick in picks for i in pick.item_ids]
    # Only the person's own pieces, however the ids got there.
    mine = list(db.scalars(select(Item.id).where(Item.id.in_(wanted), Item.user_id == user.id)))
    found = briefs(db, Names(db, user), mine)
    hexes = {c.id: c.hex for c in db.scalars(select(ColorFamily))}
    return DigestOut(
        id=digest.id,
        week=digest.week,
        status=digest.status,
        note=digests.note_text(digest.note),
        season=digest.season,
        subject=digest.subject,
        intro=digest.intro,
        worked_out_at=digest.updated_at,
        sent_at=digest.sent_at,
        picks=[_pick_out(pick, found, hexes) for pick in picks],
    )


@router.get("/digests/latest", response_model=DigestOut, responses=error_responses(401, 404))
def get_latest_digest(user: CurrentUser, db: SessionDep) -> DigestOut:
    """The person's latest weekly picks."""
    found = digests.latest(db, user)
    if found is None:
        raise ApiError(404, "no_digest", "No weekly picks yet.")
    return _digest_out(db, user, found)


@router.post("/digests/preview", response_model=DigestOut, responses=error_responses(401, 403, 429))
def preview_digest(user: CurrentUser, db: SessionDep) -> DigestOut:
    """Work out this week's picks now and show them, without emailing anything. Once this
    week's email has gone, it shows what was sent."""
    try:
        rate_limit.hit(db, f"digest-preview:user:{user.id}", PREVIEWS_PER_USER)
    except rate_limit.RateLimited as error:
        db.commit()
        raise ApiError(
            429, "rate_limited", "That's a lot of working out in an hour. Try again later."
        ) from error
    digest = digests.build(db, user, datetime.now(UTC))
    db.commit()
    return _digest_out(db, user, digest)


def _own_pick(db: Session, user: User, pick_id: uuid.UUID) -> DigestPick:
    found = digests.find_pick(db, user, pick_id)
    if found is None:
        raise ApiError(404, "pick_not_found", "That pick doesn't exist.")
    return found


@router.post(
    "/digest-picks/{pick_id}/not-for-me",
    response_model=DigestOut,
    responses=error_responses(401, 403, 404),
)
def not_for_me(pick_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> DigestOut:
    """ "Not for me": the trend isn't picked again, and the same kind and colour count for
    less for eight weeks."""
    pick = _own_pick(db, user, pick_id)
    digests.react(pick, True, datetime.now(UTC))
    db.commit()
    return _digest_out(db, user, db.get_one(Digest, pick.digest_id))


@router.delete(
    "/digest-picks/{pick_id}/not-for-me",
    response_model=DigestOut,
    responses=error_responses(401, 403, 404),
)
def undo_not_for_me(pick_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> DigestOut:
    """Take "not for me" back."""
    pick = _own_pick(db, user, pick_id)
    digests.react(pick, False, datetime.now(UTC))
    db.commit()
    return _digest_out(db, user, db.get_one(Digest, pick.digest_id))
