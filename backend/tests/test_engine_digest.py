"""The weekly digest's picks (docs/AGENTS.md, section 5): what a trend is worth to one person,
judged against what they own."""

from dataclasses import replace
from typing import Any

from engine_support import OCCASIONS, USER, context, make, wardrobe
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from test_engine_properties import items as random_items
from test_engine_shopping import FAMILIES, MENSWEAR, SEASONS

from app.engine.config import DEFAULT
from app.engine.digest import Declined, Person, Pick, TrendOption, pick, season_fit, trend_fit
from app.engine.insights import measure
from app.engine.shopping import buy_line, closest, gaps
from app.engine.types import EngineItem

COLLEGE = [OCCASIONS["college"], OCCASIONS["casual_outing"]]
SUMMER = Person(
    styles=frozenset({"minimal"}),
    preferred_colors=frozenset({"olive"}),
    avoided_colors=frozenset({"orange"}),
    season_now="summer",
    season_ahead="summer",
)


def owned() -> list[EngineItem]:
    return [
        make("casual_shirt", "white", fabric="cotton"),
        make("casual_shirt", "navy", fabric="cotton"),
        make("tshirt", "black", fabric="cotton"),
        make("chinos", "beige", fabric="cotton"),
        make("jeans", "denim_blue", fabric="denim"),
        make("sneakers", "white"),
        make("loafers", "brown", fabric="leather"),
    ]


def option(
    trend: str, category: str, color: str, seasons: frozenset[str] = frozenset(), **fields: Any
) -> TrendOption:
    candidate = make(category, color, id=f"trend:{trend}:{category}", **fields)
    return TrendOption(
        trend_id=trend,
        candidate=candidate,
        styles=frozenset({"minimal"}),
        colors=frozenset({color}),
        seasons=seasons,
    )


def picks(
    options: list[TrendOption], person: Person = SUMMER, items: list[EngineItem] | None = None
) -> list[Pick]:
    w = wardrobe(*(items if items is not None else owned()))
    ctx = context("college", season=person.season_now)
    before = measure(w, ctx, COLLEGE, SEASONS, FAMILIES)
    line = buy_line(gaps(w, ctx, COLLEGE, SEASONS, before, MENSWEAR[:12]))
    names = {item.id: item.name for item in w.items}
    return pick(options, person, w, ctx, COLLEGE, SEASONS, before, line, names)


def test_a_trend_like_something_owned_becomes_already_in_your_wardrobe() -> None:
    items = owned()
    white_shirt = items[0]

    [found] = picks([option("white-shirts", "casual_shirt", "white", fabric="cotton")], items=items)

    assert (found.kind, found.item.id) == ("owned", white_shirt.id)
    # With an outfit it's already part of.
    assert white_shirt.id in found.outfit
    assert found.analysis is None


def test_a_new_piece_is_judged_like_a_purchase_and_scored_mostly_on_what_it_adds() -> None:
    [found] = picks([option("olive-chinos", "chinos", "olive", fabric="cotton")])

    assert found.kind == "buy"
    assert found.analysis is not None and found.analysis.new_outfits >= 2
    assert found.verdict is not None and found.verdict.code in ("buy", "consider")
    assert found.score == round(
        DEFAULT.pick_value * found.value
        + DEFAULT.pick_trend_fit * found.trend_fit
        + DEFAULT.pick_season_fit * found.season_fit,
        4,
    )
    # Its example outfit has the new piece in it.
    assert found.item.id in found.outfit


def test_avoided_colours_out_of_season_trends_and_declined_trends_are_never_picked() -> None:
    person = replace(SUMMER, declined=(Declined("rust-chinos", "chinos", "rust", days_ago=200),))
    found = picks(
        [
            option("orange-shirts", "casual_shirt", "orange"),
            option("wool-coats", "coat", "charcoal", seasons=frozenset({"winter"})),
            option("rust-chinos", "chinos", "rust"),
        ],
        person,
    )

    assert found == []


def test_the_same_category_and_colour_scores_half_for_eight_weeks_after_not_for_me() -> None:
    chinos = option("olive-chinos", "chinos", "olive", fabric="cotton")
    [before] = picks([chinos])
    recent = replace(SUMMER, declined=(Declined("other-trend", "chinos", "olive", days_ago=10),))
    later = replace(SUMMER, declined=(Declined("other-trend", "chinos", "olive", days_ago=60),))

    [halved] = picks([chinos], recent)
    [back] = picks([chinos], later)

    assert halved.score == round(before.score * DEFAULT.pick_declined_factor, 4)
    assert back.score == before.score


def test_at_most_three_each_from_a_different_category_and_trend() -> None:
    found = picks(
        [
            option("olive-chinos", "chinos", "olive", fabric="cotton"),
            option("rust-chinos", "chinos", "rust", fabric="cotton"),
            option("sage-shirts", "casual_shirt", "sage", fabric="linen"),
            option("sage-shirts", "polo", "sage"),
            option("tan-loafers", "loafers", "tan", fabric="suede"),
            option("grey-trousers", "casual_trousers", "grey"),
        ]
    )

    assert 1 <= len(found) <= DEFAULT.picks
    assert len({p.item.category_id for p in found}) == len(found)
    assert len({p.trend_id for p in found}) == len(found)
    assert [p.score for p in found] == sorted((p.score for p in found), reverse=True)


def test_only_the_most_promising_get_the_slow_analysis() -> None:
    w = wardrobe(*owned())
    ctx = context("college", season="summer")
    before = measure(w, ctx, COLLEGE, SEASONS, FAMILIES)
    one = replace(DEFAULT, pick_analysed=1)

    found = pick(
        [
            option("olive-chinos", "chinos", "olive", fabric="cotton"),
            option("grey-trousers", "casual_trousers", "grey"),
        ],
        SUMMER,
        w,
        ctx,
        COLLEGE,
        SEASONS,
        before,
        None,
        {},
        one,
    )

    assert len([p for p in found if p.analysis is not None]) <= 1


def test_trend_fit_and_season_fit() -> None:
    nobody = replace(SUMMER, styles=frozenset(), preferred_colors=frozenset())
    autumn = replace(SUMMER, season_now="mild", season_ahead="winter")

    assert trend_fit(frozenset({"minimal", "streetwear"}), frozenset({"olive"}), SUMMER) == 0.75
    assert trend_fit(frozenset({"minimal"}), frozenset({"olive"}), nobody) == 0.5
    assert season_fit(frozenset(), SUMMER) == 1.0
    assert season_fit(frozenset({"winter"}), autumn) == DEFAULT.pick_next_season
    assert season_fit(frozenset({"monsoon"}), autumn) == 0.0


@settings(
    max_examples=12,
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow, HealthCheck.data_too_large],
)
@given(
    # A wardrobe that makes outfits, plus random pieces (some of them someone else's).
    extra=st.lists(random_items(), max_size=8),
    chosen=st.lists(st.sampled_from(MENSWEAR), min_size=1, max_size=6, unique_by=lambda s: s.id),
    avoided=st.sets(st.sampled_from(["black", "white", "navy", "olive", "rust"]), max_size=2),
)
def test_picks_keep_every_rule_on_random_wardrobes(
    extra: list[EngineItem], chosen: list[EngineItem], avoided: set[str]
) -> None:
    items = owned() + extra
    person = replace(SUMMER, avoided_colors=frozenset(avoided))
    options = [
        TrendOption(
            trend_id=f"trend-{n}",
            candidate=replace(staple, id=f"trend:{n}", owner_id=USER),
            styles=frozenset(),
            colors=frozenset({staple.color_family}),
            seasons=frozenset(),
        )
        for n, staple in enumerate(chosen)
    ]

    found = picks(options, person, items)

    mine = [item for item in items if item.owner_id == USER]
    assert len(found) <= DEFAULT.picks
    assert len({p.item.category_id for p in found}) == len(found)
    for found_pick in found:
        assert found_pick.item.color_family not in avoided
        if found_pick.kind == "owned":
            # Only the person's own pieces are named, never someone else's in the wardrobe.
            assert found_pick.item in mine
        else:
            # Never a near-copy of something owned: that would have been "owned".
            _, likeness = closest(found_pick.item, mine)
            assert likeness < DEFAULT.duplicate_at
            assert found_pick.verdict is not None and found_pick.verdict.code != "skip"
