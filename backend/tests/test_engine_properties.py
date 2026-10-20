"""Rules that hold for any wardrobe, checked on random ones (hypothesis)."""

from collections import Counter

from engine_support import CATEGORIES, COLORS, OCCASIONS, USER, context, make, wardrobe
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.engine.config import DEFAULT
from app.engine.generate import suggest
from app.engine.pairs import PairScores
from app.engine.scoring import Range, Scorer
from app.engine.types import Context, EngineItem

# Clothes and shoes most of the time, so outfits can be built; accessories now and then.
WEARABLE = sorted(
    c for c, spec in CATEGORIES.items() if spec["slot"] in ("top", "bottom", "footwear", "layer")
)
OTHER = sorted(c for c in CATEGORIES if c not in WEARABLE)
STATUSES = ["available", "available", "available", "laundry", "repair", "lent", "retired"]
PATTERNS = ["solid", "stripe", "check", "print", "graphic", "texture"]
FABRICS = [None, "cotton", "linen", "denim", "wool", "polyester", "silk", "leather", "suede"]
SEASONS = ["summer", "monsoon", "winter", "mild"]


@st.composite
def items(draw: st.DrawFn) -> EngineItem:
    category = draw(st.sampled_from(WEARABLE) | st.sampled_from(OTHER))
    wears_before = draw(st.sampled_from([None, 1, 2, 3]))
    return make(
        category,
        draw(st.sampled_from(sorted(COLORS))),
        owner_id=draw(st.sampled_from([USER, USER, USER, "user-b"])),
        status=draw(st.sampled_from(STATUSES)),
        archived=draw(st.booleans() | st.just(False)),
        formality=draw(st.integers(1, 5)),
        warmth=draw(st.integers(0, 5)),
        pattern=draw(st.sampled_from(PATTERNS)),
        fabric=draw(st.sampled_from(FABRICS)),
        seasons=frozenset(draw(st.lists(st.sampled_from(SEASONS), max_size=2))),
        wears_before_wash=wears_before,
        wears_since_wash=draw(st.integers(0, 3)),
        set_id=draw(st.sampled_from([None, None, None, "set-1"])),
    )


def usable_for(item: EngineItem, ctx: Context) -> bool:
    if item.owner_id != ctx.user_id or item.archived or item.status != "available":
        return False
    return item.wears_before_wash is None or item.wears_since_wash < item.wears_before_wash


@settings(max_examples=150, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    found=st.lists(items(), max_size=40),
    occasion=st.sampled_from(sorted(OCCASIONS)),
    season=st.sampled_from(SEASONS),
    count=st.integers(1, 12),
)
def test_suggestions_never_break_the_rules(
    found: list[EngineItem], occasion: str, season: str, count: int
) -> None:
    ctx = context(occasion, season=season, count=count)

    result = suggest(wardrobe(*found), ctx)

    assert len(result.outfits) <= count
    for outfit in result.outfits:
        assert all(usable_for(item, ctx) for item in outfit.items)
        slots = Counter(item.slot for item in outfit.items)
        assert max(slots.values()) == 1
        assert 0 <= outfit.score <= 1
        for value in vars(outfit.components).values():
            assert 0 <= value <= 1.1
    if not result.outfits:
        assert result.missing


@settings(max_examples=100, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(found=st.lists(items(), min_size=1, max_size=30), data=st.data())
def test_anchored_suggestions_keep_the_anchor_and_the_rules(
    found: list[EngineItem], data: st.DataObject
) -> None:
    mine = [item for item in found if item.owner_id == USER and not item.archived]
    if not mine:
        return
    anchor = data.draw(st.sampled_from(mine))
    occasion = data.draw(st.sampled_from([None, *sorted(OCCASIONS)]))
    ctx = context(occasion, anchor_ids=(anchor.id,))

    result = suggest(wardrobe(*found), ctx)

    for outfit in result.outfits:
        assert anchor in outfit.items
        assert all(usable_for(item, ctx) for item in outfit.items)
        assert max(Counter(item.slot for item in outfit.items).values()) == 1


@settings(max_examples=200, deadline=None)
@given(core=st.lists(items(), min_size=2, max_size=4, unique_by=lambda item: item.slot))
def test_the_quick_score_equals_the_detailed_score(core: list[EngineItem]) -> None:
    occasion = OCCASIONS["college"]
    scorer = Scorer(
        context(),
        Range(occasion.formality_min, occasion.formality_max, occasion),
        PairScores(DEFAULT),
        wardrobe().slot_kinds,
        DEFAULT,
    )

    assert scorer.quick(core) == scorer.score(core).score
