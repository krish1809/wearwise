"""Packing lists (docs/ENGINE.md, section 13)."""

from collections import Counter
from datetime import date, timedelta

from engine_support import COLORS, OCCASIONS, context, make, wardrobe
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from app.engine.config import DEFAULT
from app.engine.packing import TripDay, pack
from app.engine.types import EngineItem, Weather

START = date(2026, 11, 2)


def trip(count: int, occasion: str = "casual_outing") -> list[TripDay]:
    return [
        TripDay(
            day=START + timedelta(days=n),
            occasion=OCCASIONS[occasion],
            weather=Weather(feels_like=26.0, rain_chance=10),
            season="mild",
        )
        for n in range(count)
    ]


def test_every_day_gets_a_good_outfit_from_the_packed_pieces() -> None:
    items = [
        *(make("casual_shirt", c, wears_before_wash=1) for c in ("white", "navy", "olive", "grey")),
        *(make("chinos", c) for c in ("beige", "navy")),
        make("loafers", "brown"),
        make("sneakers", "white"),
    ]

    packing = pack(wardrobe(*items), context(), trip(3))

    assert all(day.outfit is not None for day in packing.days)
    packed = set(packing.item_ids)
    for day in packing.days:
        assert day.outfit is not None and day.outfit.score >= DEFAULT.packing_min_score
        assert {item.id for item in day.outfit.items} <= packed


def test_pieces_that_take_two_wears_cover_two_days() -> None:
    # Five tops that each go two wears between washes: two days need just one of them.
    tops = [
        make("polo", c, wears_before_wash=2) for c in ("white", "navy", "olive", "grey", "black")
    ]
    rest = [make("chinos", "beige"), make("loafers", "brown")]

    packing = pack(wardrobe(*tops, *rest), context(), trip(2))

    packed_tops = [item for item in tops if item.id in packing.item_ids]
    assert len(packed_tops) == 1


def test_nothing_is_packed_for_more_wears_than_it_has_left() -> None:
    shirts = [make("casual_shirt", c, wears_before_wash=1) for c in ("white", "navy")]
    rest = [make("chinos", "beige", wears_before_wash=5), make("loafers", "brown")]

    packing = pack(wardrobe(*shirts, *rest), context(), trip(4))

    worn = Counter(item.id for day in packing.days if day.outfit for item in day.outfit.items)
    assert all(worn[shirt.id] <= 1 for shirt in shirts)
    assert [day.outfit is not None for day in packing.days] == [True, True, False, False]
    assert [m.code for m in packing.days[2].missing] == ["packing.not_enough"]


def test_a_missing_piece_is_named_for_the_day() -> None:
    items = [make("casual_shirt", "white"), make("chinos", "navy")]

    packing = pack(wardrobe(*items), context(), trip(1))

    assert packing.days[0].outfit is None
    assert [m.code for m in packing.days[0].missing] == ["missing.none_owned"]


CATEGORIES = ["casual_shirt", "tshirt", "polo", "chinos", "jeans", "sneakers", "loafers", "watch"]


@st.composite
def closets(draw: st.DrawFn) -> list[EngineItem]:
    return [
        make(
            draw(st.sampled_from(CATEGORIES)),
            draw(st.sampled_from(sorted(COLORS))),
            wears_before_wash=draw(st.sampled_from([None, 1, 2, 3])),
            wears_since_wash=draw(st.integers(0, 1)),
        )
        for _ in range(draw(st.integers(2, 16)))
    ]


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(items=closets(), days=st.integers(1, 6))
def test_packing_random_wardrobes_never_breaks_the_rules(
    items: list[EngineItem], days: int
) -> None:
    packing = pack(wardrobe(*items), context(), trip(days))

    by_id = {item.id: item for item in items}
    worn = Counter(item.id for day in packing.days if day.outfit for item in day.outfit.items)
    for item_id, times in worn.items():
        item = by_id[item_id]
        if item.wears_before_wash is not None:
            assert times <= item.wears_before_wash - item.wears_since_wash
    for day in packing.days:
        assert (day.outfit is None) == bool(day.missing)
        if day.outfit:
            assert day.outfit.score >= DEFAULT.packing_min_score
            assert {item.id for item in day.outfit.items} <= set(packing.item_ids)
    assert set(packing.item_ids) <= set(worn)
