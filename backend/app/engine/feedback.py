"""Learning from reactions to suggestions (docs/ENGINE.md, section 10).

Pair preferences and like-rates are worked out from the list of reactions, not adjusted in
place, so changing a like to a dislike, or undoing one, gives the same numbers as if the
first reaction had never happened.
"""

from collections import defaultdict
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from itertools import combinations

from app.engine.config import DEFAULT, EngineConfig
from app.engine.types import EngineItem

POSITIVE = frozenset({"like", "saved", "worn"})
# The reason a dislike gives when it's about one piece, not how the pieces go together.
ITEM_REASON = "item"


@dataclass(frozen=True)
class Reaction:
    """One reaction, oldest first when replayed."""

    core_ids: tuple[str, ...]
    verdict: str
    reason: str | None = None
    # The piece a dislike is about, when its reason is the item.
    item_id: str | None = None


def pair_target(reaction: Reaction, config: EngineConfig = DEFAULT) -> float | None:
    """Where a reaction pulls each of its pairs, or None if it says nothing about them."""
    if reaction.verdict in POSITIVE:
        return config.preference_limit
    if reaction.verdict == "dislike" and reaction.reason != ITEM_REASON:
        return -config.preference_limit
    return None


def pair_preferences(
    reactions: Iterable[Reaction], config: EngineConfig = DEFAULT
) -> dict[tuple[str, str], float]:
    """Each pair's preference after replaying the reactions in order: every reaction moves
    the pref a share of the way to its target, pref += rate * (target - pref)."""
    found: dict[tuple[str, str], float] = {}
    for reaction in reactions:
        target = pair_target(reaction, config)
        if target is None:
            continue
        for pair in combinations(sorted(reaction.core_ids), 2):
            current = found.get(pair, 0.0)
            found[pair] = current + config.learning_rate * (target - current)
    return found


def like_counts(
    reactions: Iterable[Reaction], items: Mapping[str, EngineItem]
) -> tuple[dict[tuple[str, str], tuple[int, int]], dict[str, tuple[int, int]]]:
    """(likes, dislikes) by colour family and category, and by single item.

    Likes, saves, and wears count for every core piece's family and category, and so does a
    dislike of the whole outfit. A dislike of one item counts against that item alone.
    Pieces that have since been deleted are skipped."""
    groups: dict[tuple[str, str], list[int]] = defaultdict(lambda: [0, 0])
    singles: dict[str, list[int]] = defaultdict(lambda: [0, 0])
    for reaction in reactions:
        if reaction.verdict == "dislike" and reaction.reason == ITEM_REASON:
            if reaction.item_id is not None and reaction.item_id in items:
                singles[reaction.item_id][1] += 1
            continue
        if reaction.verdict in POSITIVE:
            column = 0
        elif reaction.verdict == "dislike":
            column = 1
        else:
            continue
        for item_id in reaction.core_ids:
            item = items.get(item_id)
            if item is not None:
                groups[(item.color_family, item.category_id)][column] += 1
    return (
        {key: (likes, dislikes) for key, (likes, dislikes) in groups.items()},
        {key: (likes, dislikes) for key, (likes, dislikes) in singles.items()},
    )
