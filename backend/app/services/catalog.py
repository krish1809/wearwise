"""Loading a demo catalogue from an open dataset's product list (docs/SHOPPING.md, 2.2).

Written for the columns of the "Fashion Product Images" dataset's styles.csv (id, gender,
masterCategory, subCategory, articleType, baseColour, season, year, usage,
productDisplayName). Check the dataset's licence before loading it.

Every row is stored as demo data: no price (the dataset has none, and a demo price would be
made up), no link to buy, and a label wherever it's shown. Labels are mapped onto the seed's
categories and colours only where the match is clear; anything else is skipped and counted.
What the dataset doesn't say stays empty: no seasons, and a fabric or pattern only when the
product's name states one (a name that states no pattern is taken as solid).
"""

import re
from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import delete
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.models import CatalogProduct, Category
from app.services import products

# The dataset's article types, as seed category ids.
ARTICLE_TYPES: dict[str, str] = {
    "Tshirts": "tshirt",
    "Shirts": "casual_shirt",
    "Jeans": "jeans",
    "Trousers": "casual_trousers",
    "Track Pants": "track_pants",
    "Shorts": "shorts",
    "Leggings": "leggings",
    "Skirts": "skirt",
    "Palazzos": "palazzo",
    "Dresses": "dress",
    "Jumpsuit": "jumpsuit",
    "Camisoles": "camisole",
    "Tunics": "tunic",
    "Sweatshirts": "sweatshirt",
    "Sweaters": "sweater",
    "Jackets": "casual_jacket",
    "Blazers": "blazer",
    "Waistcoat": "waistcoat",
    "Shrug": "shrug",
    "Rain Jacket": "rain_jacket",
    "Nehru Jackets": "nehru_jacket",
    "Kurtas": "kurta",
    "Kurtis": "kurti",
    "Sarees": "saree",
    "Dupatta": "dupatta",
    "Casual Shoes": "sneakers",
    "Sports Shoes": "sports_shoes",
    "Formal Shoes": "formal_shoes",
    "Sandals": "sandals",
    "Sports Sandals": "sandals",
    "Flip Flops": "slides",
    "Heels": "heels",
    "Flats": "flats",
    "Belts": "belt",
    "Watches": "watch",
    "Sunglasses": "sunglasses",
    "Caps": "cap",
    "Ties": "tie",
    "Scarves": "scarf_stole",
    "Mufflers": "scarf_stole",
    "Backpacks": "backpack",
    "Handbags": "tote_handbag",
    "Clutches": "clutch",
    "Laptop Bag": "laptop_bag",
    "Wallets": "wallet",
    "Socks": "socks",
    "Earrings": "earrings",
    "Necklace and Chains": "necklace_chain",
    "Bracelet": "bracelet_bangle",
    "Bangle": "bracelet_bangle",
    "Ring": "ring",
    "Perfume and Body Mist": "perfume",
    "Deodorant": "deodorant",
}
# Shirts and trousers labelled for formal use.
FORMAL_ARTICLES = {"Shirts": "formal_shirt", "Trousers": "formal_trousers"}

# The dataset's base colours, as seed colour families.
COLOURS: dict[str, str] = {
    "Black": "black",
    "White": "white",
    "Off White": "cream",
    "Cream": "cream",
    "Grey": "grey",
    "Grey Melange": "grey",
    "Charcoal": "charcoal",
    "Navy Blue": "navy",
    "Beige": "beige",
    "Khaki": "beige",
    "Tan": "tan",
    "Brown": "brown",
    "Coffee Brown": "brown",
    "Mushroom Brown": "brown",
    "Olive": "olive",
    "Blue": "blue",
    "Teal": "teal",
    "Turquoise Blue": "teal",
    "Green": "green",
    "Sea Green": "green",
    "Yellow": "yellow",
    "Mustard": "mustard",
    "Orange": "orange",
    "Rust": "rust",
    "Red": "red",
    "Maroon": "maroon",
    "Burgundy": "maroon",
    "Pink": "pink",
    "Purple": "purple",
    "Lavender": "lavender",
    "Gold": "gold",
    "Silver": "silver",
    "Steel": "silver",
    "Multi": "multi",
}
GENDERS: dict[str, list[str]] = {
    "Men": ["menswear"],
    "Women": ["womenswear"],
    "Unisex": ["menswear", "womenswear"],
}
PATTERNS = [
    (r"\bstripe[sd]?\b", "stripe"),
    (r"\bcheck(ed|s)?\b|\bcheckered\b", "check"),
    (r"\bgraphic\b", "graphic"),
    (r"\bprint(ed|s)?\b", "print"),
    (r"\btextured\b|\bself[- ]design\b", "texture"),
]
FABRICS = [
    (r"\bdenim\b", "denim"),
    (r"\blinen\b", "linen"),
    (r"\bwool(len)?\b", "wool"),
    (r"\bsilk\b", "silk"),
    (r"\bsatin\b", "satin"),
    (r"\bsuede\b", "suede"),
    (r"\bleather\b", "leather"),
    (r"\bcanvas\b", "canvas"),
    (r"\bpolyester\b", "polyester"),
    (r"\b(viscose|rayon)\b", "viscose"),
    (r"\bcotton\b", "cotton"),
]


@dataclass(frozen=True)
class Loaded:
    loaded: int
    # Rows left out, by reason.
    skipped: Mapping[str, int]


def load_catalog(db: Session, rows: Iterable[Mapping[str, str]], source: str) -> Loaded:
    """Insert or update every row that maps clearly, as demo products. The caller commits."""
    category_ids, colour_ids, fabric_ids, categories = products.known(db)
    skipped: Counter[str] = Counter()
    values = []
    now = datetime.now(UTC)
    for row in rows:
        article = (row.get("articleType") or "").strip()
        usage = (row.get("usage") or "").strip()
        category_id = (FORMAL_ARTICLES if usage == "Formal" else {}).get(
            article, ARTICLE_TYPES.get(article, "")
        )
        colour = COLOURS.get((row.get("baseColour") or "").strip())
        sections = GENDERS.get((row.get("gender") or "").strip())
        title = " ".join((row.get("productDisplayName") or "").split())[:200]
        external_id = (row.get("id") or "").strip()
        if category_id not in category_ids:
            skipped["category"] += 1
            continue
        if colour not in colour_ids:
            skipped["colour"] += 1
            continue
        if sections is None:
            skipped["section"] += 1
            continue
        if not title or not external_id:
            skipped["incomplete"] += 1
            continue
        category = categories[category_id]
        name = title.lower()
        fabric = next((f for regex, f in FABRICS if re.search(regex, name)), None)
        pattern = next((p for regex, p in PATTERNS if re.search(regex, name)), "solid")
        values.append(
            {
                "source": source,
                "external_id": external_id,
                "title": title,
                "brand": None,
                "url": None,
                "image_url": None,
                "price": None,
                "category_id": category_id,
                "color_primary": colour,
                "pattern": pattern,
                "fabric": fabric if fabric in fabric_ids else None,
                "formality": _formality(usage, category),
                "warmth": category.warmth,
                "seasons": [],
                "sections": sections,
                "fetched_at": now,
                "is_demo": True,
            }
        )
    for start in range(0, len(values), 1000):
        chunk = values[start : start + 1000]
        statement = insert(CatalogProduct).values(chunk)
        db.execute(
            statement.on_conflict_do_update(
                index_elements=["source", "external_id"],
                set_={
                    name: statement.excluded[name]
                    for name in chunk[0]
                    if name not in ("source", "external_id")
                },
            )
        )
    db.flush()
    return Loaded(len(values), dict(skipped))


def _formality(usage: str, category: Category) -> int:
    """The category's usual level, moved by the dataset's usage label, within the
    category's range."""
    level = {"Formal": 4, "Party": 4, "Smart Casual": 3, "Sports": 1}.get(
        usage, category.formality_default
    )
    return max(category.formality_min, min(category.formality_max, level))


def clear_catalog(db: Session, source: str) -> int:
    """Remove a catalogue's products. Candidates made from them keep their own copy."""
    result = db.execute(delete(CatalogProduct).where(CatalogProduct.source == source))
    db.flush()
    return result.rowcount or 0  # type: ignore[attr-defined]
