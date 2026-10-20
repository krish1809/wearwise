"""What a purchase would add (docs/SHOPPING.md, part 1)."""

import json
import random
import time
from collections import Counter
from itertools import combinations
from typing import Any

import pytest
from engine_support import COLORS, OCCASIONS, USER, context, make, wardrobe
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from test_engine_generate import big_wardrobe
from test_engine_properties import items as random_items

from app.engine.config import DEFAULT
from app.engine.insights import Family, measure
from app.engine.shopping import (
    Cell,
    analyse,
    best_subset,
    budget_split,
    buy_line,
    capsule,
    closest,
    coverage_gain,
    gaps,
    greedy_subset,
    similarity,
    value,
    verdict,
)
from app.engine.types import EngineItem
from app.services.reference_seed import SEED_DIR

FAMILIES = [Family(c["id"], c["name"], c["hex"], c["neutrality"]) for c in COLORS.values()]
SEASONS = ["summer", "monsoon", "winter", "mild"]
COLLEGE_AND_INTERVIEW = [OCCASIONS["college"], OCCASIONS["interview"]]

_archetypes = json.loads((SEED_DIR / "archetypes.json").read_text())["archetypes"]


def staple(spec: dict[str, Any]) -> EngineItem:
    return make(
        spec["category"],
        spec["color"],
        id=f"archetype:{spec['id']}",
        name=spec["name"],
        pattern=spec["pattern"],
        fabric=spec.get("fabric"),
        formality=spec["formality"],
        warmth=spec["warmth"],
        seasons=frozenset(spec["seasons"]),
    )


MENSWEAR = [staple(spec) for spec in _archetypes if "menswear" in spec["sections"]]


def casual_wardrobe() -> list[EngineItem]:
    """Plenty for college; for an interview, only formal trousers, which nothing here
    dresses up to that level."""
    return [
        *(make("casual_shirt", c, fabric="cotton") for c in ("white", "navy", "light_blue")),
        make("casual_shirt", "grey", fabric="cotton"),
        *(make("chinos", c, fabric="cotton") for c in ("beige", "grey", "navy")),
        make("loafers", "brown", fabric="leather"),
        make("formal_trousers", "charcoal", formality=4),
    ]


def names(items: list[EngineItem]) -> dict[str, str]:
    return {item.id: item.name for item in items}


# Value and likeness.


def test_good_outfits_have_diminishing_value_and_a_cap() -> None:
    assert value(2) - value(0) > value(11) - value(9)
    assert value(15) == value(10)
    cell: Cell = ("college", "mild")
    assert coverage_gain({cell: 10}, {cell: 5}) == 0.0
    assert coverage_gain({cell: 0}, {cell: 2}) == pytest.approx(value(2))


def test_likeness_of_pieces_for_the_same_slot() -> None:
    navy = make("chinos", "navy", fabric="cotton")

    assert similarity(navy, make("chinos", "navy")) == pytest.approx(1.0)
    # Navy and black are close, so similar, but not "the same chinos".
    black = similarity(navy, make("chinos", "black"))
    assert DEFAULT.buy_similarity_below <= black < DEFAULT.duplicate_at
    # White and cream T-shirts are as good as the same.
    assert similarity(make("tshirt", "white"), make("tshirt", "cream")) >= DEFAULT.duplicate_at
    # A different kind of bottom in the same colour is never a duplicate.
    assert similarity(navy, make("jeans", "navy")) < DEFAULT.duplicate_at
    # Another pair of chinos in a clearly different colour can still be a Buy.
    assert similarity(navy, make("chinos", "maroon")) < DEFAULT.buy_similarity_below


# The analysis and the verdict.


def test_an_identical_candidate_is_skip_and_names_the_duplicate() -> None:
    items = casual_wardrobe()
    w = wardrobe(*items)
    ctx = context()
    before = measure(w, ctx, COLLEGE_AND_INTERVIEW, SEASONS, FAMILIES)
    candidate = make("chinos", "beige", fabric="cotton", id="candidate-1")

    analysis = analyse(w, ctx, COLLEGE_AND_INTERVIEW, SEASONS, before, candidate)
    found = verdict(
        analysis, candidate, names(items), COLLEGE_AND_INTERVIEW, before.coverage, 0.0, None, ""
    )

    assert analysis.closest_id == items[4].id
    assert analysis.redundancy == pytest.approx(1.0)
    assert found.code == "skip"
    assert found.reasons[0].text == "Very close to your beige / khaki chinos."


def test_opening_an_empty_occasion_beats_adding_to_a_full_one() -> None:
    items = casual_wardrobe()
    w = wardrobe(*items)
    ctx = context()
    before = measure(w, ctx, COLLEGE_AND_INTERVIEW, SEASONS, FAMILIES)
    assert all(before.coverage[("college", s)] >= DEFAULT.coverage_cap for s in SEASONS)
    assert all(before.coverage[("interview", s)] == 0 for s in SEASONS)
    line = buy_line(gaps(w, ctx, COLLEGE_AND_INTERVIEW, SEASONS, before, MENSWEAR))
    tee = make("tshirt", "olive", fabric="cotton", id="candidate-tee")
    shoes = make("formal_shoes", "black", fabric="leather", formality=5, id="candidate-shoes")

    more_of_the_same = analyse(w, ctx, COLLEGE_AND_INTERVIEW, SEASONS, before, tee)
    opens = analyse(w, ctx, COLLEGE_AND_INTERVIEW, SEASONS, before, shoes)

    assert more_of_the_same.new_outfits >= 2
    assert more_of_the_same.coverage_gain == 0.0
    assert opens.coverage_gain > more_of_the_same.coverage_gain
    assert all(opens.added[("interview", s)] > 0 for s in SEASONS)
    tee_verdict = verdict(
        more_of_the_same, tee, names(items), COLLEGE_AND_INTERVIEW, before.coverage, line, None, ""
    )
    shoes_verdict = verdict(
        opens, shoes, names(items), COLLEGE_AND_INTERVIEW, before.coverage, line, None, ""
    )
    assert tee_verdict.code == "consider"
    assert "You already have plenty" in " ".join(r.text for r in tee_verdict.reasons)
    assert shoes_verdict.code == "buy"
    assert shoes_verdict.reasons[0].text == (
        "It gives you a first good outfit for interview / presentation in every season."
    )


def test_a_candidate_rescues_the_orphan_it_dresses_up() -> None:
    items = casual_wardrobe()
    trousers = items[-1]
    w = wardrobe(*items)
    ctx = context()
    before = measure(w, ctx, COLLEGE_AND_INTERVIEW, SEASONS, FAMILIES)
    shoes = make("formal_shoes", "black", fabric="leather", formality=5, id="candidate-shoes")

    analysis = analyse(w, ctx, COLLEGE_AND_INTERVIEW, SEASONS, before, shoes)
    found = verdict(
        analysis, shoes, names(items), COLLEGE_AND_INTERVIEW, before.coverage, None, None, ""
    )

    assert trousers.id in before.orphans
    assert trousers.id in analysis.rescued
    assert "It gives your charcoal formal trousers more to go with." in [
        r.text for r in found.reasons
    ]


def test_over_budget_or_too_similar_is_never_buy() -> None:
    items = casual_wardrobe()
    w = wardrobe(*items)
    ctx = context()
    before = measure(w, ctx, COLLEGE_AND_INTERVIEW, SEASONS, FAMILIES)
    shoes = make("formal_shoes", "black", fabric="leather", formality=5, id="candidate-shoes")
    analysis = analyse(w, ctx, COLLEGE_AND_INTERVIEW, SEASONS, before, shoes)

    over = verdict(
        analysis, shoes, names(items), COLLEGE_AND_INTERVIEW, before.coverage, 0.0, False, "Shoes"
    )

    assert over.code == "consider"
    assert "It costs more than you usually spend on shoes." in [r.text for r in over.reasons]


def test_an_accessory_finishes_outfits_but_is_at_most_consider() -> None:
    items = casual_wardrobe()
    w = wardrobe(*items)
    ctx = context()
    before = measure(w, ctx, COLLEGE_AND_INTERVIEW, SEASONS, FAMILIES)
    belt = make("belt", "brown", fabric="leather", id="candidate-belt")

    analysis = analyse(w, ctx, COLLEGE_AND_INTERVIEW, SEASONS, before, belt)
    found = verdict(
        analysis, belt, names(items), COLLEGE_AND_INTERVIEW, before.coverage, 0.0, True, ""
    )

    assert analysis.kind == "accessory"
    assert analysis.new_outfits >= 2
    assert analysis.coverage_gain == 0.0
    assert all(belt.id in core for _, core in analysis.examples)
    assert found.code == "consider"
    assert found.reasons[0].code == "verdict.accessory" or any(
        r.code == "verdict.accessory" for r in found.reasons
    )


def test_matches_are_owned_pieces_in_other_slots() -> None:
    items = casual_wardrobe()
    w = wardrobe(*items)
    ctx = context()
    before = measure(w, ctx, [OCCASIONS["college"]], ["mild"], FAMILIES)
    shirt = make("casual_shirt", "white", fabric="linen", id="candidate-shirt")

    analysis = analyse(w, ctx, [OCCASIONS["college"]], ["mild"], before, shirt)

    slots = {item.id: item.slot for item in items}
    assert analysis.matches
    assert all(slots[item_id] != "top" for item_id, _ in analysis.matches)
    assert [score for _, score in analysis.matches] == sorted(
        (score for _, score in analysis.matches), reverse=True
    )


@settings(max_examples=60, deadline=None, suppress_health_check=[HealthCheck.too_slow])
@given(
    found=st.lists(random_items(), max_size=12),
    candidate=random_items(),
    occasion=st.sampled_from(sorted(OCCASIONS)),
    season=st.sampled_from(SEASONS),
)
def test_adding_a_candidate_never_lowers_coverage_and_matches_a_recount(
    found: list[EngineItem], candidate: EngineItem, occasion: str, season: str
) -> None:
    candidate = EngineItem(**{**candidate.__dict__, "owner_id": USER, "id": "candidate-x"})
    occasions = [OCCASIONS[occasion]]
    w = wardrobe(*found)
    ctx = context(occasion=None)
    before = measure(w, ctx, occasions, [season], FAMILIES)

    analysis = analyse(w, ctx, occasions, [season], before, candidate)
    after = measure(wardrobe(*found, candidate), ctx, occasions, [season], FAMILIES)

    for cell, count in before.coverage.items():
        assert after.coverage[cell] >= count
        if analysis.kind == "core":
            assert after.coverage[cell] == count + analysis.added.get(cell, 0)
    assert analysis.coverage_gain >= 0


# Gaps and the starter capsule.


def test_a_wardrobe_without_shoes_needs_shoes_first() -> None:
    items = [i for i in casual_wardrobe() if i.slot != "footwear"]
    w = wardrobe(*items)
    ctx = context()
    before = measure(w, ctx, [OCCASIONS["college"]], SEASONS, FAMILIES)

    found = gaps(w, ctx, [OCCASIONS["college"]], SEASONS, before, MENSWEAR)

    first = found[0]
    assert len(first.item_ids) == 1
    assert first.coverage_gain > 0
    assert {s.id: s.slot for s in MENSWEAR}[first.item_ids[0]] == "footwear"


def test_staples_you_already_own_are_not_gaps() -> None:
    white_tee = next(s for s in MENSWEAR if s.id == "archetype:white_tshirt")
    owned = make("tshirt", "white", pattern="solid", fabric="cotton", formality=2)
    w = wardrobe(owned, make("jeans", "denim_blue"), make("sneakers", "white"))
    ctx = context()
    before = measure(w, ctx, [OCCASIONS["college"]], SEASONS, FAMILIES)

    found = gaps(w, ctx, [OCCASIONS["college"]], SEASONS, before, MENSWEAR)

    assert closest(white_tee, [owned])[1] >= DEFAULT.duplicate_at
    assert all(white_tee.id not in gap.item_ids for gap in found)


def test_an_occasion_no_single_staple_opens_gets_a_whole_outfit() -> None:
    w = wardrobe(*casual_wardrobe()[:-1])
    ctx = context()
    before = measure(w, ctx, COLLEGE_AND_INTERVIEW, SEASONS, FAMILIES)

    found = gaps(w, ctx, COLLEGE_AND_INTERVIEW, SEASONS, before, MENSWEAR)

    together = [gap for gap in found if len(gap.item_ids) > 1]
    assert together
    assert together[0].reason.startswith("Together, your first good outfit for interview")
    assert all(cell[0] == "interview" for gap in together for cell in gap.added)


def test_a_capsule_from_nothing_starts_with_a_whole_outfit_within_budget() -> None:
    w = wardrobe()
    ctx = context()
    occasions = [OCCASIONS["college"]]
    before = measure(w, ctx, occasions, SEASONS, FAMILIES)
    spend = {"tops": 100000, "bottoms": 150000, "footwear": 250000, "layers": 200000}
    costs = {s.id: spend.get(s.group_id) for s in MENSWEAR}

    steps = capsule(w, ctx, occasions, SEASONS, before, MENSWEAR, costs, 1_200_000)

    slots = {s.id: s.slot for s in MENSWEAR}
    first = sorted(slots[i] for i in steps[0].item_ids)
    assert first in (["bottom", "footwear", "top"], ["footwear", "one_piece"])
    assert all(len(step.item_ids) == 1 for step in steps[1:])
    assert sum(step.cost or 0 for step in steps) <= 1_200_000
    assert all(step.coverage_gain > 0 for step in steps)
    assert len({i for step in steps for i in step.item_ids}) <= DEFAULT.capsule_limit


def test_a_capsule_without_a_budget_stops_at_the_limit_or_when_nothing_adds() -> None:
    w = wardrobe()
    ctx = context()
    occasions = [OCCASIONS["college"]]
    before = measure(w, ctx, occasions, ["mild"], FAMILIES)

    steps = capsule(w, ctx, occasions, ["mild"], before, MENSWEAR, {}, None)

    pieces = [i for step in steps for i in step.item_ids]
    assert 3 <= len(pieces) <= DEFAULT.capsule_limit
    assert len(pieces) == len(set(pieces))


# The budget split.


def test_a_shirt_and_trousers_bought_together_beat_either_alone() -> None:
    shoes = make("loafers", "brown", fabric="leather")
    w = wardrobe(shoes)
    ctx = context()
    occasions = [OCCASIONS["college"]]
    before = measure(w, ctx, occasions, ["mild"], FAMILIES)
    shirt = make("casual_shirt", "white", fabric="cotton", id="c-shirt")
    chinos = make("chinos", "navy", fabric="cotton", id="c-chinos")
    jacket = make("blazer", "navy", id="c-jacket")

    split = budget_split(
        w,
        ctx,
        occasions,
        ["mild"],
        before,
        [(shirt, 100000), (chinos, 150000), (jacket, 400000)],
        300000,
    )

    assert set(split.chosen) == {"c-shirt", "c-chinos"}
    assert split.spent == 250000
    assert split.exhaustive


def _brute_force(
    masks: dict[Cell, Counter[int]], before: dict[Cell, int], prices: list[int], budget: int
) -> float:
    best = 0.0
    for size in range(len(prices) + 1):
        for chosen in combinations(range(len(prices)), size):
            if sum(prices[i] for i in chosen) > budget:
                continue
            bits = sum(1 << i for i in chosen)
            made = {
                cell: sum(n for mask, n in counted.items() if mask & ~bits == 0)
                for cell, counted in masks.items()
            }
            best = max(best, coverage_gain(before, made))
    return best


@st.composite
def split_cases(
    draw: st.DrawFn,
) -> tuple[dict[Cell, Counter[int]], dict[Cell, int], list[int], int]:
    n = draw(st.integers(1, 7))
    cells = [("college", s) for s in SEASONS[: draw(st.integers(1, 4))]]
    masks = {
        cell: Counter(draw(st.lists(st.integers(1, (1 << n) - 1), max_size=12))) for cell in cells
    }
    before = {cell: draw(st.integers(0, 10)) for cell in cells}
    prices = draw(st.lists(st.integers(1, 50), min_size=n, max_size=n))
    budget = draw(st.integers(0, 150))
    return masks, before, prices, budget


@settings(max_examples=200, deadline=None)
@given(case=split_cases())
def test_the_budget_split_never_exceeds_the_budget_and_is_the_best_subset(
    case: tuple[dict[Cell, Counter[int]], dict[Cell, int], list[int], int],
) -> None:
    masks, before, prices, budget = case

    chosen, gain = best_subset(masks, before, prices, budget)

    assert sum(p for i, p in enumerate(prices) if chosen >> i & 1) <= budget
    assert gain == pytest.approx(_brute_force(masks, before, prices, budget))


def test_greedy_stays_within_budget_and_close_to_the_best() -> None:
    """Pieces make outfits together, so greedy has no guarantee. On 300 random cases of
    eight candidates it reached 98% of the best on average, the best itself in four cases
    out of five, and two thirds of it at worst (D44)."""
    rng = random.Random(7)
    ratios = []
    for _ in range(300):
        n = 8
        cells = [("college", s) for s in SEASONS]
        # Most new outfits need one of the candidates, some two, a few three.
        masks = {
            cell: Counter(
                sum(1 << i for i in rng.sample(range(n), rng.choice((1, 1, 1, 2, 2, 3))))
                for _ in range(rng.randrange(0, 15))
            )
            for cell in cells
        }
        before = {cell: rng.randrange(0, 11) for cell in cells}
        prices = [rng.randrange(1, 60) for _ in range(n)]
        budget = rng.randrange(20, 200)

        best_mask, best = best_subset(masks, before, prices, budget)
        greedy_mask, greedy = greedy_subset(masks, before, prices, budget)

        assert sum(p for i, p in enumerate(prices) if greedy_mask >> i & 1) <= budget
        assert greedy <= best + 1e-9
        ratios.append(greedy / best if best else 1.0)
    assert sum(ratios) / len(ratios) >= 0.95
    assert min(ratios) >= 0.6


# Speed: the analysis runs on a small server.


def test_a_150_item_wardrobe_is_analysed_and_its_gaps_found_quickly() -> None:
    w = wardrobe(*big_wardrobe())
    ctx = context()
    before = measure(w, ctx, COLLEGE_AND_INTERVIEW, SEASONS, FAMILIES)
    cache: dict[Any, Any] = {}

    started = time.perf_counter()
    analyse(w, ctx, COLLEGE_AND_INTERVIEW, SEASONS, before, make("chinos", "olive", id="c-x"))
    analysed = time.perf_counter() - started
    started = time.perf_counter()
    found = gaps(w, ctx, COLLEGE_AND_INTERVIEW, SEASONS, before, MENSWEAR, pair_cache=cache)
    gapped = time.perf_counter() - started

    assert analysed < 1.0, f"analysis took {analysed:.2f} s"
    assert gapped < 2.0, f"gaps took {gapped:.2f} s"
    assert found[0].coverage_gain > 0
