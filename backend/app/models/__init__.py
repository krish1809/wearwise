"""SQLAlchemy tables. Import every model here so Alembic's autogenerate can see it."""

from app.models.app_meta import AppMeta
from app.models.base import Base
from app.models.item import Item, ItemImage
from app.models.outfit import Outfit, OutfitItem, WearLog, WearLogItem
from app.models.profile import BrandNote, Profile
from app.models.rate_limit import RateLimitHit
from app.models.reference import (
    Category,
    CategoryGroup,
    ColorFamily,
    Occasion,
    OutfitTemplate,
    StyleProfile,
    VocabularyTerm,
)
from app.models.suggestion import Suggestion, SuggestionFeedback
from app.models.user import User
from app.models.user_session import UserSession

__all__ = [
    "AppMeta",
    "Base",
    "BrandNote",
    "Category",
    "CategoryGroup",
    "ColorFamily",
    "Item",
    "ItemImage",
    "Occasion",
    "Outfit",
    "OutfitItem",
    "OutfitTemplate",
    "Profile",
    "RateLimitHit",
    "StyleProfile",
    "Suggestion",
    "SuggestionFeedback",
    "User",
    "UserSession",
    "VocabularyTerm",
    "WearLog",
    "WearLogItem",
]
