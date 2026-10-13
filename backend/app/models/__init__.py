"""SQLAlchemy tables. Import every model here so Alembic's autogenerate can see it."""

from app.models.app_meta import AppMeta
from app.models.base import Base
from app.models.profile import BrandNote, Profile
from app.models.rate_limit import RateLimitHit
from app.models.reference import (
    CategoryGroup,
    ColorFamily,
    Occasion,
    StyleProfile,
    VocabularyTerm,
)
from app.models.user import User
from app.models.user_session import UserSession

__all__ = [
    "AppMeta",
    "Base",
    "BrandNote",
    "CategoryGroup",
    "ColorFamily",
    "Occasion",
    "Profile",
    "RateLimitHit",
    "StyleProfile",
    "User",
    "UserSession",
    "VocabularyTerm",
]
