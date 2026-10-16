"""Counting attempts per time window, in Postgres, so limits survive restarts and deploys."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models.rate_limit import RateLimitHit


@dataclass(frozen=True)
class Limit:
    attempts: int
    window: timedelta


class RateLimited(Exception):
    def __init__(self, retry_after_seconds: int) -> None:
        super().__init__(f"Too many attempts; retry in {retry_after_seconds} seconds")
        self.retry_after_seconds = retry_after_seconds


def hit(db: Session, bucket: str, limit: Limit, now: datetime | None = None) -> None:
    """Count one attempt in the bucket's current window, and raise RateLimited past the limit."""
    now = now or datetime.now(UTC)
    window_seconds = int(limit.window.total_seconds())
    epoch = int(now.timestamp())
    window_start = datetime.fromtimestamp(epoch - epoch % window_seconds, UTC)

    count = db.scalar(
        insert(RateLimitHit)
        .values(bucket=bucket, window_start=window_start, count=1)
        .on_conflict_do_update(
            index_elements=["bucket", "window_start"],
            set_={"count": RateLimitHit.count + 1, "updated_at": func.now()},
        )
        .returning(RateLimitHit.count)
    )
    # Earlier windows for this bucket no longer matter.
    db.execute(
        delete(RateLimitHit).where(
            RateLimitHit.bucket == bucket, RateLimitHit.window_start < window_start
        )
    )

    if count is not None and count > limit.attempts:
        retry_after = window_start + limit.window - now
        raise RateLimited(retry_after_seconds=int(retry_after.total_seconds()) + 1)
