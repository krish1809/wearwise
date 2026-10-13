from datetime import datetime

from sqlalchemy import DateTime, false
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class User(IdMixin, TimestampMixin, Base):
    __tablename__ = "users"

    # Lower-cased and trimmed before it is stored or compared.
    email: Mapped[str] = mapped_column(unique=True)
    # Argon2id: the password itself is never stored.
    password_hash: Mapped[str]
    name: Mapped[str | None]
    # Bumped whenever the wardrobe changes, so cached outfit scores know they're stale (M3, M5).
    wardrobe_version: Mapped[int] = mapped_column(default=0, server_default="0")
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    # Only the demo script creates demo accounts, and it touches no other account.
    is_demo: Mapped[bool] = mapped_column(default=False, server_default=false())

    @property
    def onboarding_completed(self) -> bool:
        """Answered or skipped: either way, log in goes straight to Home."""
        return self.onboarding_completed_at is not None
