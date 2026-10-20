"""SQLAlchemy tables. Import every model here so Alembic's autogenerate can see it."""

from app.models.app_meta import AppMeta
from app.models.base import Base
from app.models.chat import AIUsage, ChatAction, ChatMessage, ChatThread
from app.models.item import Item, ItemImage
from app.models.outfit import Outfit, OutfitItem, WearLog, WearLogItem
from app.models.planning import Event, PlanDay, Trip, TripItem, WeatherForecast
from app.models.profile import BrandNote, Profile
from app.models.rate_limit import RateLimitHit
from app.models.reference import (
    Archetype,
    Category,
    CategoryGroup,
    ColorFamily,
    GuideEntry,
    Occasion,
    OutfitTemplate,
    StyleProfile,
    VocabularyTerm,
)
from app.models.shopping import Candidate, CatalogProduct, LinkPreview
from app.models.suggestion import Suggestion, SuggestionFeedback
from app.models.user import User
from app.models.user_session import UserSession

__all__ = [
    "AIUsage",
    "AppMeta",
    "Archetype",
    "Base",
    "BrandNote",
    "Candidate",
    "CatalogProduct",
    "Category",
    "CategoryGroup",
    "ChatAction",
    "ChatMessage",
    "ChatThread",
    "ColorFamily",
    "Event",
    "GuideEntry",
    "Item",
    "ItemImage",
    "LinkPreview",
    "Occasion",
    "Outfit",
    "OutfitItem",
    "OutfitTemplate",
    "PlanDay",
    "Profile",
    "RateLimitHit",
    "StyleProfile",
    "Suggestion",
    "SuggestionFeedback",
    "Trip",
    "TripItem",
    "User",
    "UserSession",
    "VocabularyTerm",
    "WeatherForecast",
    "WearLog",
    "WearLogItem",
]
