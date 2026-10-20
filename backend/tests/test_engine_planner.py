"""Planning a week (docs/ENGINE.md, section 12)."""

import dataclasses
import time
from datetime import date, timedelta

from engine_support import COLORS, OCCASIONS, context, make, wardrobe
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from test_engine_generate import big_wardrobe

from app.engine.config import DEFAULT
from app.engine.planner import DaySpec, Locked, Worn, alternatives, plan_week, violations
from app.engine.types import EngineItem, Weather

MONDAY = date(2026, 10, 19)
COLLEGE = OCCASIONS["college"]
MILD = Weather(feels_like=27.0, rain_chance=10)


def week(
    count: int = 7, occasion: str | None = "college", locked: dict[int, Locked] | None = None
) -> list[DaySpec]:
    return [
        DaySpec(
            day=MONDAY + timedelta(days=n),
            occasion=OCCASIONS[occasion] if occasion else None,
            weather=MILD,
            season="mild",
            locked=(locked or {}).get(n),
        )
        for n in range(count)
    ]


def closet() -> list[EngineItem]:
    return [
        *(make("casual_shirt", c, fabric="cotton") for c in ("white", "navy", "olive", "grey")),
        *(make("tshirt", c, fabric="cotton") for c in ("black", "beige", "maroon")),
        *(make("chinos", c) for c in ("beige", "navy", "olive")),
        make("jeans", "denim_blue", fabric="denim"),
        *(make("sneakers", c) for c in ("white", "black")),
        make("loafers", "brown", fabric="leather"),
    ]


def worn_week(plan_days: list[DaySpec], plan: object) -> list[Worn | None]:
    found: list[Worn | None] = []
    for spec, day in zip(plan_days, plan.days, strict=True):  # type: ignore[attr-defined]
        if spec.locked is not None:
            found.append(Worn(spec.locked.item_ids, spec.locked.core_ids))
        elif day.outfit is not None:
            found.append(Worn(tuple(i.id for i in day.outfit.items), day.outfit.core_ids))
        else:
            found.append(None)
    return found


def test_a_week_keeps_every_rule() -> None:
    items = closet()
    days = week()

    plan = plan_week(wardrobe(*items), context(), days)

    assert all(day.outfit is not None for day in plan.days)
    by_id = {item.id: item for item in items}
    assert violations(worn_week(days, plan), [d.day for d in days], by_id) == []


def test_no_top_is_planned_twice_within_three_days() -> None:
    plan = plan_week(wardrobe(*closet()), context(), week())

    tops = [
        next(item.id for item in day.outfit.items if item.slot == "top")
        for day in plan.days
        if day.outfit
    ]
    for index, top in enumerate(tops):
        assert top not in tops[index + 1 : index + 3]


def test_nothing_is_planned_past_its_wash_limit() -> None:
    # One shirt that takes two wears, worn once already, and plenty of everything else.
    shirt = make("casual_shirt", "white", wears_before_wash=2, wears_since_wash=1)
    others = [item for item in closet() if item.slot != "top"]
    tees = [make("tshirt", c, wears_before_wash=1) for c in ("black", "beige", "maroon", "grey")]

    plan = plan_week(wardrobe(shirt, *others, *tees), context(), week())

    uses = sum(1 for day in plan.days if day.outfit and shirt in day.outfit.items)
    assert uses <= 1
    for tee in tees:
        assert sum(1 for day in plan.days if day.outfit and tee in day.outfit.items) <= 1


def test_locked_days_are_kept_and_counted() -> None:
    items = closet()
    first = plan_week(wardrobe(*items), context(), week())
    keep = {
        n: Locked(
            tuple(i.id for i in first.days[n].outfit.items),  # type: ignore[union-attr]
            first.days[n].outfit.core_ids,  # type: ignore[union-attr]
        )
        for n in (1, 4)
    }
    days = week(locked=keep)

    again = plan_week(wardrobe(*items), context(), days)

    assert [day.locked for day in again.days] == [False, True, False, False, True, False, False]
    assert again.days[1].outfit is None and again.days[4].outfit is None
    by_id = {item.id: item for item in items}
    assert violations(worn_week(days, again), [d.day for d in days], by_id) == []


def test_a_small_wardrobe_says_which_days_it_could_not_fill() -> None:
    items = [
        make("tshirt", "white", wears_before_wash=1),
        make("jeans", "navy"),
        make("sneakers", "white"),
    ]

    plan = plan_week(wardrobe(*items), context(), week(3))

    assert plan.days[0].outfit is not None
    assert [m.code for m in plan.days[1].missing] == ["plan.blocked"]
    assert plan.days[1].missing[0].text == (
        "Everything that fits this day is due a wash or worn too recently by then."
    )


def test_a_day_without_an_occasion_asks_for_one() -> None:
    plan = plan_week(wardrobe(*closet()), context(), week(2, occasion=None))

    assert [m.code for m in plan.days[0].missing] == ["plan.no_occasion"]


def test_laundry_day_makes_everything_clean_again() -> None:
    # Only one top, washed after each wear. Laundry on Thursday (day 3).
    tee = make("tshirt", "white", wears_before_wash=1)
    rest = [make("jeans", "navy"), make("sneakers", "white"), make("loafers", "brown")]

    without = plan_week(wardrobe(tee, *rest), context(), week(5))
    with_laundry = plan_week(wardrobe(tee, *rest), context(), week(5), laundry_weekday=3)

    assert [bool(day.outfit) for day in without.days] == [True, False, False, False, False]
    assert [bool(day.outfit) for day in with_laundry.days] == [True, False, False, True, False]


def test_swaps_keep_the_rest_of_the_week_within_the_rules() -> None:
    items = closet()
    first = plan_week(wardrobe(*items), context(), week())
    locked = {
        n: Locked(tuple(i.id for i in day.outfit.items), day.outfit.core_ids)
        for n, day in enumerate(first.days)
        if day.outfit is not None
    }
    days = week(locked=locked)
    target = days[2].day

    options = alternatives(wardrobe(*items), context(), days, target, 6)

    assert options
    by_id = {item.id: item for item in items}
    for option in options:
        trial = worn_week(days, first)
        trial[2] = Worn(tuple(i.id for i in option.items), option.core_ids)
        assert violations(trial, [d.day for d in days], by_id) == []


def test_a_150_item_week_plans_in_a_few_seconds() -> None:
    items = big_wardrobe()
    started = time.perf_counter()

    plan = plan_week(wardrobe(*items), context(), week())

    elapsed = time.perf_counter() - started
    assert all(day.outfit for day in plan.days)
    assert elapsed < 3.0, f"took {elapsed:.2f} s"


CATEGORIES = ["casual_shirt", "tshirt", "polo", "chinos", "jeans", "sneakers", "loafers", "belt"]


@st.composite
def closets(draw: st.DrawFn) -> list[EngineItem]:
    found = []
    for _ in range(draw(st.integers(3, 18))):
        found.append(
            make(
                draw(st.sampled_from(CATEGORIES)),
                draw(st.sampled_from(sorted(COLORS))),
                wears_before_wash=draw(st.sampled_from([None, 1, 2, 3])),
                wears_since_wash=draw(st.integers(0, 2)),
            )
        )
    return found


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(items=closets(), laundry=st.sampled_from([None, 0, 3, 6]), lock=st.booleans())
def test_plans_on_random_wardrobes_keep_every_rule_and_beat_greedy(
    items: list[EngineItem], laundry: int | None, lock: bool
) -> None:
    days = week(5)
    if lock:
        first = plan_week(wardrobe(*items), context(), days, laundry_weekday=laundry)
        if first.days[1].outfit is not None:
            outfit = first.days[1].outfit
            days[1] = dataclasses.replace(
                days[1], locked=Locked(tuple(i.id for i in outfit.items), outfit.core_ids)
            )

    plan = plan_week(wardrobe(*items), context(), days, laundry_weekday=laundry)
    greedy = plan_week(
        wardrobe(*items),
        context(),
        days,
        config=dataclasses.replace(DEFAULT, plan_beam_width=1, plan_per_day=1),
        laundry_weekday=laundry,
    )

    by_id = {item.id: item for item in items}
    assert violations(worn_week(days, plan), [d.day for d in days], by_id, DEFAULT, laundry) == []
    assert plan.objective >= greedy.objective - 1e-9
