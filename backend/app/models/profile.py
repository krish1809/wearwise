import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, SmallInteger, String, false, func
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.models.base import Base, IdMixin, TimestampMixin


class Profile(IdMixin, TimestampMixin, Base):
    """Everything a person chose to tell WearWise. Every answer is optional and can be cleared."""

    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    # Sections they shop (menswear, womenswear). Not a gender: it only sets default categories.
    sections: Mapped[list[str]] = mapped_column(ARRAY(String), default=list, server_default="{}")
    city: Mapped[str | None]
    # How measurements are shown. They are always stored in centimetres.
    units: Mapped[str] = mapped_column(default="cm", server_default="cm")
    currency: Mapped[str] = mapped_column(default="INR", server_default="INR")
    height_cm: Mapped[float | None]
    # chest, waist, hips, shoulder, inseam, in centimetres.
    measurements: Mapped[dict[str, float]] = mapped_column(JSONB, default=dict, server_default="{}")
    # top, bottom, shoe: each {"label": "M", "system": "in_uk"}. Labels are never converted.
    sizes: Mapped[dict[str, Any]] = mapped_column(JSONB, default=dict, server_default="{}")
    fit_preference: Mapped[str | None]
    style_profile_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    preferred_colors: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    avoided_colors: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    occasion_ids: Mapped[list[str]] = mapped_column(
        ARRAY(String), default=list, server_default="{}"
    )
    # Money in minor units (paise for INR).
    budget_monthly: Mapped[int | None] = mapped_column(BigInteger)
    # Category group id -> typical spend, in minor units.
    category_budgets: Mapped[dict[str, int]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    # How many onboarding steps were passed, so closing the tab loses nothing.
    onboarding_step: Mapped[int] = mapped_column(SmallInteger, default=0, server_default="0")
    # True when the person chose "Skip all"; Home then offers to finish, once.
    onboarding_skipped: Mapped[bool] = mapped_column(default=False, server_default=false())
    onboarding_reminder_dismissed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    # Where the weather comes from: the place chosen for `city`, rounded to about a kilometre.
    latitude: Mapped[float | None]
    longitude: Mapped[float | None]
    # Used when there's no city or no forecast: hot, mild, cold, or rainy. Null: go by the
    # season.
    manual_weather: Mapped[str | None]
    # The usual occasion for each weekday, "0" (Monday) to "6" (Sunday).
    weekday_occasions: Mapped[dict[str, str]] = mapped_column(
        JSONB, default=dict, server_default="{}"
    )
    # The weekday the washing gets done, 0 (Monday) to 6; the planner counts everything clean
    # again from that day. Null: no fixed day.
    laundry_weekday: Mapped[int | None] = mapped_column(SmallInteger)


class BrandNote(IdMixin, TimestampMixin, Base):
    """The person's own notes on a brand: "M in H&M, L in Zara"."""

    __tablename__ = "brand_notes"

    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    brand: Mapped[str]
    size_notes: Mapped[str | None]
    quality_notes: Mapped[str | None]
    price_notes: Mapped[str | None]


# One note per brand per person, whatever the capitalisation. It also serves lookups by user.
Index("uq_brand_notes_user_id_brand", BrandNote.user_id, func.lower(BrandNote.brand), unique=True)
