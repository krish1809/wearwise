"""Limits and spend for the stylist chat, photo tagging, and the agents (docs/AI.md, section 5).

A global daily spend cap (from the provider's token counts and the prices in the settings),
and per-person limits on messages and tagged photos, much lower for the demo account. The
Trend Scout belongs to nobody, so its spend is counted from its runs (D55).
"""

from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.adapters.ai import AIProvider, Usage
from app.core.config import get_settings
from app.models import AgentRun, AIUsage, User
from app.services import rate_limit

DAILY_MESSAGES = 40
DEMO_MESSAGES = 10
DAILY_IMAGES = 20
# Agent runs whose model calls aren't anyone's, so they're counted from the run log. A digest's
# calls are counted against its person, in ai_usage, like the stylist's.
UNOWNED_RUNS = ("trend_scout",)
DEMO_IMAGES = 3
PER_MINUTE = rate_limit.Limit(attempts=6, window=timedelta(minutes=1))


class AIOff(Exception):
    """AI features can't be used right now: off, over the day's spend, or the person's
    limit reached."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


def today() -> datetime:
    return datetime.now(UTC)


def spent_today(db: Session) -> int:
    """Everyone's spend today, and the Trend Scout's, in millionths of a US dollar."""
    now = today()
    people = db.scalar(select(func.sum(AIUsage.cost_micro_usd)).where(AIUsage.day == now.date()))
    midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
    runs = db.scalar(
        select(func.sum(AgentRun.cost_micro_usd)).where(
            AgentRun.kind.in_(UNOWNED_RUNS), AgentRun.started_at >= midnight
        )
    )
    return (people or 0) + (runs or 0)


def cost_micro_usd(usage: Usage) -> int:
    """What a call cost, from its tokens and the prices in the settings."""
    settings = get_settings()
    # Prices are US dollars per million tokens, so a token costs `price` millionths of one.
    return round(
        usage.input_tokens * settings.ai_price_input_per_mtok
        + usage.output_tokens * settings.ai_price_output_per_mtok
    )


def over_cap(db: Session) -> bool:
    """Whether today's spend has reached the daily cap, which the agents share (D55)."""
    cap = round(get_settings().ai_daily_spend_cap_usd * 1_000_000)
    return spent_today(db) >= cap


def status(db: Session, ai: AIProvider | None) -> str | None:
    """None when AI features can be used; otherwise why not: off or spend_cap."""
    if ai is None:
        return "off"
    if over_cap(db):
        return "spend_cap"
    return None


def _row(db: Session, user: User) -> AIUsage | None:
    day = today().date()
    return db.scalar(select(AIUsage).where(AIUsage.user_id == user.id, AIUsage.day == day))


def check_message(db: Session, user: User, ai: AIProvider | None) -> None:
    reason = status(db, ai)
    if reason:
        raise AIOff(reason)
    try:
        rate_limit.hit(db, f"stylist:user:{user.id}", PER_MINUTE)
    except rate_limit.RateLimited as error:
        raise AIOff("too_fast") from error
    row = _row(db, user)
    if row and row.messages >= (DEMO_MESSAGES if user.is_demo else DAILY_MESSAGES):
        raise AIOff("daily_limit")


def check_image(db: Session, user: User, ai: AIProvider | None) -> None:
    reason = status(db, ai)
    if reason:
        raise AIOff(reason)
    row = _row(db, user)
    if row and row.images >= (DEMO_IMAGES if user.is_demo else DAILY_IMAGES):
        raise AIOff("daily_limit")


def check_spend(db: Session, ai: AIProvider | None) -> None:
    """Before each call to the provider: a long conversation can cross the cap midway."""
    reason = status(db, ai)
    if reason:
        raise AIOff(reason)


def record(db: Session, user: User, usage: Usage, messages: int = 0, images: int = 0) -> None:
    cost = cost_micro_usd(usage)
    values = {
        "messages": messages,
        "images": images,
        "tokens_in": usage.input_tokens,
        "tokens_out": usage.output_tokens,
        "cost_micro_usd": cost,
    }
    statement = insert(AIUsage).values(user_id=user.id, day=today().date(), **values)
    db.execute(
        statement.on_conflict_do_update(
            index_elements=["user_id", "day"],
            set_={name: getattr(AIUsage, name) + statement.excluded[name] for name in values}
            | {"updated_at": func.now()},
        )
    )
    db.flush()
