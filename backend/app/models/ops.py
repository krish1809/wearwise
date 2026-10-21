from sqlalchemy import Index
from sqlalchemy.orm import Mapped

from app.models.base import Base, IdMixin, TimestampMixin


class ErrorEvent(IdMixin, TimestampMixin, Base):
    """Something that went wrong, on the server or in someone's browser, for the owner's page.
    Nothing ties it to an account; kept 30 days."""

    __tablename__ = "error_events"

    # server or browser.
    source: Mapped[str]
    request_id: Mapped[str | None]
    method: Mapped[str | None]
    # The route (such as /api/v1/items/{item_id}) or page path, never a query string.
    path: Mapped[str | None]
    status: Mapped[int | None]
    # The exception's type, or "browser".
    kind: Mapped[str]
    message: Mapped[str]
    # The stack trace, shortened.
    detail: Mapped[str | None]


Index("ix_error_events_created_at", ErrorEvent.created_at)
