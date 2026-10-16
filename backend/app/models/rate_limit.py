from datetime import datetime

from sqlalchemy import DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class RateLimitHit(IdMixin, TimestampMixin, Base):
    """How many times a bucket (such as "login:email:sam@example.com") was hit in one window."""

    __tablename__ = "rate_limit_hits"
    __table_args__ = (UniqueConstraint("bucket", "window_start"),)

    bucket: Mapped[str]
    window_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    count: Mapped[int] = mapped_column(default=1)
