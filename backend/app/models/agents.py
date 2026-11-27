from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, Index, Integer
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class AgentRun(IdMixin, TimestampMixin, Base):
    """One run of a scheduled agent, for the owner's run log (docs/AGENTS.md, section 6).
    Shared: it holds counts, queries, and sources, never who a digest went to."""

    __tablename__ = "agent_runs"

    # trend_scout or weekly_digest.
    kind: Mapped[str]
    # schedule or manual.
    trigger: Mapped[str]
    # running, done (finished), stopped (a limit was reached; what was valid is kept), or failed.
    status: Mapped[str]
    # The checkpointer's thread, while the run can still be resumed.
    thread_id: Mapped[str | None]
    started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Each step's counts and time: the queries, the sources read, and every trend dropped with
    # its reason, or a digest run's sent, held, and failed counts.
    steps: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    search_credits: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tokens_in: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    tokens_out: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    cost_micro_usd: Mapped[int] = mapped_column(BigInteger, default=0, server_default="0")
    # The limit that stopped it, or "lapsed" for a run that never said it had finished.
    stopped_by: Mapped[str | None]
    errors: Mapped[list[str]] = mapped_column(JSONB, default=list, server_default="[]")


# At most one running row per kind: a second run of the same job can't start (D56).
Index(
    "uq_agent_runs_kind_running",
    AgentRun.kind,
    unique=True,
    postgresql_where=AgentRun.status == "running",
)
Index("ix_agent_runs_kind_started_at", AgentRun.kind, AgentRun.started_at)
