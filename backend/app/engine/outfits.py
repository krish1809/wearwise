"""Which outfit templates a set of pieces fills. Plain data in, plain data out.

A template lists the slots an outfit needs (a top, a bottom, footwear), any limits on which
categories fill them (a saree outfit needs a saree), and the slots it may add (a layer,
accessories, fragrance). An outfit is complete when one template has every required slot
filled, nothing else outside its optional slots, and no slot holds two items.
"""

from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Requirement:
    slot: str
    # If set, only these categories fill the slot.
    only: frozenset[str] | None = None
    # These categories never fill it.
    never: frozenset[str] = frozenset()

    def accepts(self, category_id: str) -> bool:
        if self.only is not None and category_id not in self.only:
            return False
        return category_id not in self.never


@dataclass(frozen=True)
class Template:
    id: str
    required: tuple[Requirement, ...]
    optional: frozenset[str]

    @classmethod
    def from_seed(cls, id: str, required: list[dict[str, Any]], optional: list[str]) -> Template:
        return cls(
            id=id,
            required=tuple(
                Requirement(
                    slot=r["slot"],
                    only=frozenset(r["categories"]) if "categories" in r else None,
                    never=frozenset(r.get("exclude_categories", [])),
                )
                for r in required
            ),
            optional=frozenset(optional),
        )


@dataclass(frozen=True)
class Piece:
    key: str
    slot: str
    category_id: str


@dataclass(frozen=True)
class Check:
    complete: bool
    # The template the pieces come closest to; None only when there are no templates.
    template_id: str | None
    # Required slots that are still empty, in the template's order.
    missing: tuple[str, ...] = ()
    # Pieces the template has no place for: a slot it doesn't use, or a category it refuses.
    misplaced: tuple[Piece, ...] = ()
    # Slots that hold more than one piece.
    crowded: tuple[str, ...] = ()


def check_outfit(pieces: Sequence[Piece], templates: Sequence[Template]) -> Check:
    """How well the pieces fill the best-fitting template.

    The best template is the one with the fewest pieces it has no place for, then the most
    required slots already filled, then the fewest still missing. Missing slots only count
    once a required slot is filled, so an empty outfit (or one with only accessories) points
    at the first template rather than whichever needs the fewest pieces.
    """
    counts = Counter(piece.slot for piece in pieces)
    crowded = tuple(sorted(slot for slot, count in counts.items() if count > 1))
    best: tuple[tuple[int, int, int, int], Check] | None = None
    for order, template in enumerate(templates):
        missing: list[str] = []
        misplaced: list[Piece] = []
        filled = 0
        required_slots = {r.slot for r in template.required}
        for requirement in template.required:
            here = [piece for piece in pieces if piece.slot == requirement.slot]
            misplaced += [piece for piece in here if not requirement.accepts(piece.category_id)]
            if any(requirement.accepts(piece.category_id) for piece in here):
                filled += 1
            else:
                missing.append(requirement.slot)
        misplaced += [
            piece
            for piece in pieces
            if piece.slot not in required_slots and piece.slot not in template.optional
        ]
        check = Check(
            complete=not missing and not misplaced and not crowded,
            template_id=template.id,
            missing=tuple(missing),
            misplaced=tuple(misplaced),
            crowded=crowded,
        )
        rank = (len(misplaced), -filled, len(missing) if filled else 0, order)
        if best is None or rank < best[0]:
            best = (rank, check)
    return best[1] if best else Check(complete=False, template_id=None, crowded=crowded)
