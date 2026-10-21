"""The stylist chat and photo tagging (docs/AI.md). Both say plainly when they're
unavailable; nothing else in the app depends on them."""

import uuid
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, status
from pydantic import AfterValidator, BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters.ai import AIUnavailable
from app.agents import stylist as agent
from app.api.deps import AIDep, CheckpointerDep, CurrentUser, SessionDep, StorageDep, WeatherDep
from app.api.errors import ApiError, error_responses
from app.api.fields import required_text
from app.api.item_views import ItemBrief, Names
from app.api.shopping import CandidateOut, candidate_outs
from app.models import Archetype, ChatAction, ChatMessage, ChatThread, ColorFamily, Item, User
from app.services import ai_usage, categories, checkpoints, items, shopping, stylist, tagging, wear

router = APIRouter(tags=["stylist"])

MESSAGES = {
    "off": (503, "ai_off", "The stylist isn't switched on in this copy of WearWise."),
    "spend_cap": (
        503,
        "ai_resting",
        "The stylist has used today's allowance and is back tomorrow. Everything else works.",
    ),
    "down": (
        503,
        "ai_down",
        "The stylist didn't respond. Try again in a minute; everything else works as usual.",
    ),
    "daily_limit": (429, "ai_daily_limit", "That's all the stylist can do for you today."),
    "too_fast": (429, "rate_limited", "That's a lot of messages in a minute. Wait a moment."),
}


def _unavailable(reason: str) -> ApiError:
    code, key, message = MESSAGES.get(reason, MESSAGES["down"])
    return ApiError(code, key, message)


class AIStatusOut(BaseModel):
    available: bool
    # off, spend_cap: why not, when not.
    reason: str | None


class TaggedOut(BaseModel):
    """Suggestions from the photo, to be checked: only ids from the app's own lists."""

    fields: dict[str, str]


class SendRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Leave out to start a new conversation.
    thread_id: uuid.UUID | None = None
    text: Annotated[str, AfterValidator(required_text(1000, "Write a message first."))]


class StapleCardOut(BaseModel):
    id: str
    name: str
    hex: str | None
    slot: str


class ActionOut(BaseModel):
    id: uuid.UUID
    # save_outfit, plan_outfit, add_to_list, or log_wear.
    kind: str
    # pending, done, or cancelled.
    status: str
    summary: str
    items: list[ItemBrief]
    # What confirming made: outfit_id, date, candidate_id, or wear_log_id.
    result: dict[str, str]


class CardOut(BaseModel):
    type: Literal["outfit", "item", "candidate", "staple", "action"]
    items: list[ItemBrief] = []
    # True when something the card showed has since been deleted.
    removed: bool = False
    candidate: CandidateOut | None = None
    staple: StapleCardOut | None = None
    action: ActionOut | None = None


class MessageOut(BaseModel):
    id: uuid.UUID
    role: str
    text: str
    cards: list[CardOut]
    created_at: datetime


class ThreadOut(BaseModel):
    id: uuid.UUID
    title: str
    updated_at: datetime


class ThreadDetailOut(ThreadOut):
    messages: list[MessageOut]


class SentOut(BaseModel):
    thread: ThreadOut
    messages: list[MessageOut]


# Resolving cards.


def _views(db: Session, user: User, rows: list[ChatMessage]) -> list[MessageOut]:
    cards = [card for row in rows for card in row.cards]
    action_ids = [_uuid(c.get("action_id")) for c in cards if c.get("type") == "action"]
    actions = (
        {
            a.id: a
            for a in db.scalars(
                select(ChatAction).where(
                    ChatAction.user_id == user.id,
                    ChatAction.id.in_([i for i in action_ids if i]),
                )
            )
        }
        if action_ids
        else {}
    )
    item_ids = {
        i
        for c in cards
        for i in [*c.get("item_ids", []), c.get("item_id")]
        + [i for a in actions.values() for i in a.payload.get("item_ids", [])]
        if i
    }
    parsed = [u for u in (_uuid(i) for i in item_ids) if u]
    found = (
        list(db.scalars(select(Item).where(Item.user_id == user.id, Item.id.in_(parsed))))
        if parsed
        else []
    )
    names = Names(db, user)
    photos = items.primary_photos(db, [row.id for row in found])
    briefs = {str(row.id): names.brief(row, photos.get(row.id)) for row in found}
    candidate_ids = [_uuid(c.get("candidate_id")) for c in cards if c.get("type") == "candidate"]
    candidates = {
        str(row.id): row
        for row in shopping.list_candidates(db, user)
        if row.id in {i for i in candidate_ids if i}
    }
    candidate_views = {
        str(out.id): out for out in candidate_outs(db, user, list(candidates.values()))
    }
    families = {f.id: f.hex for f in db.scalars(select(ColorFamily))}
    found_categories = {c.id: c for c in categories.list_categories(db, user)}

    def card(raw: dict[str, Any]) -> CardOut | None:
        kind = raw.get("type")
        if kind in ("outfit", "item"):
            ids = raw.get("item_ids") or [raw.get("item_id")]
            shown = [briefs[i] for i in ids if i in briefs]
            return CardOut(type=kind, items=shown, removed=len(shown) < len(ids))
        if kind == "candidate":
            out = candidate_views.get(raw.get("candidate_id", ""))
            return CardOut(type="candidate", candidate=out, removed=out is None)
        if kind == "staple":
            staple = db.get(Archetype, raw.get("archetype_id", ""))
            if staple is None:
                return CardOut(type="staple", removed=True)
            category = found_categories.get(staple.category_id)
            return CardOut(
                type="staple",
                staple=StapleCardOut(
                    id=staple.id,
                    name=staple.name,
                    hex=families.get(staple.color),
                    slot=category.slot if category else "",
                ),
            )
        if kind == "action":
            action = actions.get(_uuid(raw.get("action_id")) or uuid.UUID(int=0))
            if action is None:
                return None
            return CardOut(type="action", action=_action_out(action, briefs))
        return None

    return [
        MessageOut(
            id=row.id,
            role=row.role,
            text=row.content,
            cards=[c for c in (card(raw) for raw in row.cards) if c is not None],
            created_at=row.created_at,
        )
        for row in rows
    ]


def _action_out(action: ChatAction, briefs: dict[str, ItemBrief]) -> ActionOut:
    return ActionOut(
        id=action.id,
        kind=action.kind,
        status=action.status,
        summary=str(action.payload.get("summary", "")),
        items=[briefs[i] for i in action.payload.get("item_ids", []) if i in briefs],
        result={key: str(value) for key, value in action.result.items()},
    )


def _uuid(value: Any) -> uuid.UUID | None:
    try:
        return uuid.UUID(str(value))
    except ValueError:
        return None


def _thread(db: Session, user: User, thread_id: uuid.UUID) -> ChatThread:
    thread = stylist.find_thread(db, user, thread_id)
    if thread is None:
        raise ApiError(404, "thread_not_found", "That conversation doesn't exist.")
    return thread


def _messages(db: Session, thread: ChatThread) -> list[ChatMessage]:
    return list(
        db.scalars(
            select(ChatMessage)
            .where(ChatMessage.thread_id == thread.id)
            .order_by(ChatMessage.created_at, ChatMessage.id)
        )
    )


# Routes.


@router.get("/ai/status", response_model=AIStatusOut, responses=error_responses(401))
def ai_status(user: CurrentUser, db: SessionDep, ai: AIDep) -> AIStatusOut:
    """Whether the stylist and photo tagging can be used now, and why not if they can't."""
    reason = ai_usage.status(db, ai)
    return AIStatusOut(available=reason is None, reason=reason)


@router.post(
    "/photos/{photo_id}/tag",
    response_model=TaggedOut,
    responses=error_responses(401, 403, 404, 429, 503),
)
def tag_photo(
    photo_id: uuid.UUID, user: CurrentUser, db: SessionDep, storage: StorageDep, ai: AIDep
) -> TaggedOut:
    """Suggest a category, colours, pattern, fabric, and fit from an uploaded photo. Only
    the image is sent. Nothing is saved: the form shows the suggestions to check."""
    try:
        found = tagging.tag(db, user, storage, ai, photo_id)
    except tagging.PhotoMissing as error:
        raise ApiError(404, "photo_not_found", "That photo isn't available.") from error
    except ai_usage.AIOff as error:
        db.commit()
        raise _unavailable(error.reason) from error
    except AIUnavailable as error:
        db.commit()
        raise _unavailable("down") from error
    db.commit()
    return TaggedOut(fields=found.fields)


@router.get("/chat/threads", response_model=list[ThreadOut], responses=error_responses(401))
def list_threads(user: CurrentUser, db: SessionDep) -> list[ThreadOut]:
    rows = db.scalars(
        select(ChatThread)
        .where(ChatThread.user_id == user.id)
        .order_by(ChatThread.updated_at.desc())
        .limit(30)
    )
    return [ThreadOut(id=t.id, title=t.title, updated_at=t.updated_at) for t in rows]


@router.get(
    "/chat/threads/{thread_id}", response_model=ThreadDetailOut, responses=error_responses(401, 404)
)
def get_thread(thread_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> ThreadDetailOut:
    thread = _thread(db, user, thread_id)
    return ThreadDetailOut(
        id=thread.id,
        title=thread.title,
        updated_at=thread.updated_at,
        messages=_views(db, user, _messages(db, thread)),
    )


@router.delete(
    "/chat/threads/{thread_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    responses=error_responses(401, 403, 404),
)
def delete_thread(thread_id: uuid.UUID, user: CurrentUser, db: SessionDep) -> None:
    thread = _thread(db, user, thread_id)
    # A turn still waiting for a confirmation goes with its conversation.
    checkpoints.forget(db, thread_ids=[checkpoints.chat_thread(thread.id)])
    db.delete(thread)
    db.commit()


@router.post(
    "/chat/messages",
    response_model=SentOut,
    responses=error_responses(401, 403, 404, 422, 429, 503),
)
def send_message(
    body: SendRequest,
    user: CurrentUser,
    db: SessionDep,
    ai: AIDep,
    weather: WeatherDep,
    saver: CheckpointerDep,
) -> SentOut:
    """Ask the stylist. It answers from tool results only; anything it proposes to change
    waits for the person to confirm. Earlier proposals still waiting become "not now"."""
    is_new = body.thread_id is None
    thread = (
        _thread(db, user, body.thread_id)
        if body.thread_id
        else stylist.new_thread(db, user, body.text)
    )
    try:
        asked, answer = agent.send(db, user, ai, weather, thread, body.text, wear.today(), saver)
    except (ai_usage.AIOff, AIUnavailable) as error:
        if is_new:
            db.delete(thread)
        db.commit()
        raise _unavailable(stylist.unavailable_reason(error)) from error
    db.commit()
    db.refresh(thread)
    return SentOut(
        thread=ThreadOut(id=thread.id, title=thread.title, updated_at=thread.updated_at),
        messages=_views(db, user, [asked, answer]),
    )


def _action(db: Session, user: User, action_id: uuid.UUID) -> ChatAction:
    action = stylist.find_action(db, user, action_id)
    if action is None:
        raise ApiError(404, "action_not_found", "That proposal doesn't exist.")
    return action


def _action_view(db: Session, user: User, action: ChatAction) -> ActionOut:
    ids = [u for u in (_uuid(i) for i in action.payload.get("item_ids", [])) if u]
    found = (
        list(db.scalars(select(Item).where(Item.user_id == user.id, Item.id.in_(ids))))
        if ids
        else []
    )
    names = Names(db, user)
    photos = items.primary_photos(db, [row.id for row in found])
    briefs = {str(row.id): names.brief(row, photos.get(row.id)) for row in found}
    return _action_out(action, briefs)


@router.post(
    "/chat/actions/{action_id}/confirm",
    response_model=ActionOut,
    responses=error_responses(401, 403, 404, 409),
)
def confirm_action(
    action_id: uuid.UUID,
    user: CurrentUser,
    db: SessionDep,
    weather: WeatherDep,
    saver: CheckpointerDep,
) -> ActionOut:
    """Do what the stylist proposed, through the same code as the app's own buttons."""
    action = _action(db, user, action_id)
    try:
        stylist.confirm(db, user, action, weather)
    except stylist.ActionFailed as error:
        db.rollback()
        raise ApiError(409, "action_failed", str(error)) from error
    db.commit()
    agent.decided(action, saver)
    return _action_view(db, user, action)


@router.post(
    "/chat/actions/{action_id}/cancel",
    response_model=ActionOut,
    responses=error_responses(401, 403, 404),
)
def cancel_action(
    action_id: uuid.UUID, user: CurrentUser, db: SessionDep, saver: CheckpointerDep
) -> ActionOut:
    action = stylist.cancel(db, _action(db, user, action_id))
    db.commit()
    agent.decided(action, saver)
    return _action_view(db, user, action)
