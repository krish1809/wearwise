"""The plain data the outfit engine takes and returns. No database rows, no web types."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date
from typing import Literal

from app.engine.outfits import Template


@dataclass(frozen=True)
class EngineItem:
    """One thing the person owns, with what the engine needs to know about it."""

    id: str
    owner_id: str
    name: str
    slot: str
    category_id: str
    group_id: str
    color_family: str
    # 1 for a colour that goes with anything, 0 for a colour (from the colour family).
    color_neutrality: float
    # The measured colour, else the family's; None for multicolour.
    color_hex: str | None
    pattern: str = "solid"
    fabric: str | None = None
    fit: str | None = None
    formality: int = 3
    warmth: int = 1
    # Empty means every season.
    seasons: frozenset[str] = frozenset()
    style_tags: frozenset[str] = frozenset()
    occasion_ids: frozenset[str] = frozenset()
    status: str = "available"
    archived: bool = False
    wears_before_wash: int | None = None
    wears_since_wash: int = 0
    set_id: str | None = None
    last_worn_on: date | None = None


@dataclass(frozen=True)
class Occasion:
    id: str
    name: str
    formality_min: int
    formality_max: int
    prefers_groups: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Style:
    """A style profile's signals (seed/style_profiles.json)."""

    id: str
    name: str
    colors: frozenset[str] = frozenset()
    fabrics: frozenset[str] = frozenset()
    patterns: frozenset[str] = frozenset()
    fits: frozenset[str] = frozenset()
    categories: frozenset[str] = frozenset()
    formality_center: int = 3


@dataclass(frozen=True)
class Preferences:
    """What the person told us, and what their feedback taught us."""

    avoided_colors: frozenset[str] = frozenset()
    preferred_colors: frozenset[str] = frozenset()
    fit_preference: str | None = None
    # Learned adjustments for pairs of items, keyed by the two ids in sorted order.
    pair_prefs: Mapping[tuple[str, str], float] = field(default_factory=dict)
    # (likes, dislikes) for a colour family and category, and for single items.
    family_category_counts: Mapping[tuple[str, str], tuple[int, int]] = field(default_factory=dict)
    item_counts: Mapping[str, tuple[int, int]] = field(default_factory=dict)


@dataclass(frozen=True)
class Wardrobe:
    """Everything the engine works from: the items and the reference data around them."""

    items: tuple[EngineItem, ...]
    templates: tuple[Template, ...]
    # Slot id to its kind: core, accessory, or finishing (seed/taxonomy.json).
    slot_kinds: Mapping[str, str]
    # Names for reasons, such as "ethnic wear suits a festival".
    group_names: Mapping[str, str] = field(default_factory=dict)
    slot_names: Mapping[str, str] = field(default_factory=dict)
    color_names: Mapping[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class Context:
    """One request: who is asking, for what, and which pieces are fixed."""

    user_id: str
    today: date
    # None only when anchors set the level of dress ("what goes with this?").
    occasion: Occasion | None = None
    season: str | None = None
    # A style asked for in this request, otherwise the profile's styles.
    style: Style | None = None
    profile_styles: tuple[Style, ...] = ()
    anchor_ids: tuple[str, ...] = ()
    exclude_ids: frozenset[str] = frozenset()
    # The core pieces of outfits worn recently, with the day they were worn.
    recent_outfits: tuple[tuple[date, frozenset[str]], ...] = ()
    preferences: Preferences = field(default_factory=Preferences)
    count: int = 10


ReasonKind = Literal["positive", "caution"]


@dataclass(frozen=True)
class Reason:
    code: str
    kind: ReasonKind
    # How strongly this reason shaped the score; reasons are shown strongest first.
    strength: float
    text: str


@dataclass(frozen=True)
class Components:
    base: float
    occasion: float
    weather: float
    rotation: float
    preference: float
    style: float


@dataclass(frozen=True)
class ScoredOutfit:
    template_id: str
    # Every piece, core first, in slot order.
    items: tuple[EngineItem, ...]
    # The ids of the core pieces (required slots and the layer), sorted.
    core_ids: tuple[str, ...]
    score: float
    components: Components
    reasons: tuple[Reason, ...] = ()
    # True when no outfit fit the occasion and this one relaxes it by a step.
    compromise: bool = False


@dataclass(frozen=True)
class Missing:
    """A slot nothing could fill, and why."""

    slot: str
    template_id: str
    code: str
    text: str


@dataclass(frozen=True)
class Suggestions:
    outfits: tuple[ScoredOutfit, ...]
    # Set when no outfit fits as asked: what's missing (outfits, if any, are compromises).
    missing: tuple[Missing, ...] = ()
    compromise: bool = False
    # A plain sentence when there are fewer outfits than asked for.
    note: str | None = None
    engine_version: str = ""
