import uuid
from datetime import date
from typing import Any

from sqlalchemy import BigInteger, Date, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class ChatThread(IdMixin, TimestampMixin, Base):
    """One conversation with the stylist."""

    __tablename__ = "chat_threads"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    title: Mapped[str]


Index("ix_chat_threads_user_id_updated_at", ChatThread.user_id, ChatThread.updated_at)


class ChatMessage(IdMixin, TimestampMixin, Base):
    __tablename__ = "chat_messages"

    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_threads.id", ondelete="CASCADE"), index=True
    )
    # user or assistant.
    role: Mapped[str]
    content: Mapped[str]
    # What the reply shows: outfits, items, candidates, gaps, and actions to confirm.
    cards: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list, server_default="[]")
    # The tools called for this reply, with their arguments (for checking, not shown).
    tool_calls: Mapped[list[dict[str, Any]]] = mapped_column(
        JSONB, default=list, server_default="[]"
    )
    # Ids the tools returned for this reply: later replies in the thread may refer to them.
    seen: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class ChatAction(IdMixin, TimestampMixin, Base):
    """Something the stylist proposed to change. Nothing happens until the person confirms."""

    __tablename__ = "chat_actions"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    thread_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("chat_threads.id", ondelete="CASCADE"), index=True
    )
    # save_outfit, plan_outfit, add_to_wishlist, or log_wear.
    kind: Mapped[str]
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB)
    # pending, done, or cancelled.
    status: Mapped[str] = mapped_column(default="pending", server_default="pending")
    # What confirming made (an outfit id, a wear log id...).
    result: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")


class AIUsage(IdMixin, TimestampMixin, Base):
    """Requests, images, tokens, and their cost per person per day: for the limits and the
    daily spend cap."""

    __tablename__ = "ai_usage"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    day: Mapped[date] = mapped_column(Date)
    messages: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    images: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tokens_in: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    tokens_out: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    # Millionths of a US dollar, from the provider's prices in the settings.
    cost_micro_usd: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")


Index("ix_chat_actions_user_id", ChatAction.user_id)
Index("uq_ai_usage_user_id_day", AIUsage.user_id, AIUsage.day, unique=True)
Index("ix_ai_usage_day", AIUsage.day)
