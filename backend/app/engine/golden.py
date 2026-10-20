"""The golden set: pairs from a real wardrobe labelled good, fine, or bad by its owner, and
outfits they love (docs/ENGINE.md, section 9). It checks the engine against human taste.

Files, in backend/tests/golden/:
  items.json    the wardrobe as the engine sees it, items keyed i01, i02, ... (no photos)
  pairs.csv     a, b, a_name, b_name, label   (label: good, fine, or bad)
  outfits.json  [{"occasion": "college", "items": ["i01", "i04", "i09"], "name": "..."}]
"""

import csv
import io
from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, fields
from itertools import combinations
from typing import Any, Literal

from app.engine.config import DEFAULT, EngineConfig
from app.engine.pairs import pair_score, with_preference
from app.engine.types import EngineItem

LABELS = ("good", "fine", "bad")
OWNER = "golden"
# Pairs worth labelling: the ones that shape an outfit most (weight 0.8 or more).
LABEL_WEIGHT = 0.8

LabelName = Literal["good", "fine", "bad"]


@dataclass(frozen=True)
class Label:
    a: str
    b: str
    label: LabelName


@dataclass(frozen=True)
class Agreement:
    # Good-versus-bad comparisons the engine ordered as the owner did (a tie counts half).
    share: float
    comparisons: int
    labelled: int


def item_to_dict(item: EngineItem, key: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    for field in fields(EngineItem):
        value = getattr(item, field.name)
        if isinstance(value, frozenset):
            value = sorted(value)
        elif field.name == "last_worn_on":
            # Rotation is fixed at "not worn lately", so the set doesn't change with time.
            value = None
        data[field.name] = value
    data.update(id=key, owner_id=OWNER)
    return data


def item_from_dict(data: Mapping[str, Any]) -> EngineItem:
    values = dict(data)
    for name in ("seasons", "style_tags", "occasion_ids"):
        values[name] = frozenset(values.get(name, []))
    return EngineItem(**values)


def read_labels(text: str) -> list[Label]:
    """Labelled rows of pairs.csv; rows still blank are skipped."""
    found = []
    for row in csv.DictReader(io.StringIO(text)):
        label = (row.get("label") or "").strip().lower()
        if label in LABELS:
            found.append(Label(row["a"].strip(), row["b"].strip(), label))  # type: ignore[arg-type]
    return found


def write_pairs(pairs: Iterable[tuple[EngineItem, EngineItem]]) -> str:
    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["a", "b", "a_name", "b_name", "label"])
    for a, b in pairs:
        writer.writerow([a.id, b.id, a.name, b.name, ""])
    return out.getvalue()


def candidate_pairs(
    items: Sequence[EngineItem], count: int, config: EngineConfig = DEFAULT
) -> list[tuple[EngineItem, EngineItem]]:
    """Pairs for the owner to label, spread across the engine's scores so the set holds good
    and bad pairs alike, not just the obvious ones."""
    weights = {
        slots: weight for slots, weight in config.pair_weights.items() if weight >= LABEL_WEIGHT
    }
    pairs = [
        (a, b)
        for a, b in combinations(sorted(items, key=lambda item: item.id), 2)
        if frozenset({a.slot, b.slot}) in weights and a.slot != b.slot
    ]
    pairs.sort(key=lambda pair: (pair_score(pair[0], pair[1], config).base, pair[0].id, pair[1].id))
    if len(pairs) <= count:
        return pairs
    step = (len(pairs) - 1) / (count - 1)
    return [pairs[round(index * step)] for index in range(count)]


def agreement(
    items: Mapping[str, EngineItem], labels: Sequence[Label], config: EngineConfig = DEFAULT
) -> Agreement:
    """How often the engine scores a pair labelled good above one labelled bad."""

    def score(label: Label) -> float:
        return with_preference(pair_score(items[label.a], items[label.b], config), 0.0, config)

    good = [score(label) for label in labels if label.label == "good"]
    bad = [score(label) for label in labels if label.label == "bad"]
    comparisons = len(good) * len(bad)
    if not comparisons:
        return Agreement(share=0.0, comparisons=0, labelled=len(labels))
    agreed = sum(1.0 if g > b else 0.5 if g == b else 0.0 for g in good for b in bad)
    return Agreement(share=agreed / comparisons, comparisons=comparisons, labelled=len(labels))
