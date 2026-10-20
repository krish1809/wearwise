"""Finding real products for a gap (docs/SHOPPING.md, part 2).

Three sources, each honest about what it is:

- Shop search links: the gap or candidate as search words, linked to each shop's own search.
- A pasted link: the page read once a day at most (adapters/pages.py), its preview data
  shown for the person to confirm. Nothing is guessed: what the page doesn't say stays empty,
  and a page the site doesn't let us read just leaves the form for the person to fill in.
- The demo catalogue: products from an open dataset, loaded by a script, always marked as
  demo and never shown with a price.

Catalogue products are ranked by what they'd add to this wardrobe, with the same engine as
everything else.
"""

import re
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.adapters.pages import PageData, PageUnavailable, check_url
from app.adapters.products import PageBlocked, PageReader, SearchLink, search_links
from app.engine import shopping as engine
from app.engine.config import DEFAULT
from app.engine.insights import steady
from app.engine.types import EngineItem
from app.models import (
    Archetype,
    Candidate,
    CatalogProduct,
    Category,
    ColorFamily,
    LinkPreview,
    User,
    VocabularyTerm,
)
from app.services import categories, reference
from app.services.item_names import ItemNames
from app.services.shopping import Setting, candidate_item, staple_item

# A page read is kept this long; a failed read is retried after RETRY_AFTER.
FRESH_FOR = timedelta(days=1)
RETRY_AFTER = timedelta(minutes=30)
CATALOG = "catalog:"
# Catalogue products weighed for one gap or candidate, and shown.
WEIGHED = 30
SHOWN = 8


@dataclass(frozen=True)
class LinkRead:
    """What a pasted link gave, and suggestions for the form, all for the person to check."""

    # ok, blocked (robots.txt), unavailable, not_product, or not_a_web_link.
    outcome: str
    url: str
    fetched_at: datetime | None
    site: str | None = None
    title: str | None = None
    brand: str | None = None
    image_url: str | None = None
    # Minor units, only for a price in rupees.
    price: int | None = None
    # A price in another currency is reported, not converted.
    other_currency: str | None = None
    category_id: str | None = None
    color_primary: str | None = None
    fabric: str | None = None


def read_link(db: Session, user: User, url: str, reader: PageReader) -> LinkRead:
    """Read a pasted page, from the shared cache when it was read in the last day. Commits
    the session before going out, so no transaction stays open during the call."""
    try:
        parts = check_url(url)
    except PageUnavailable:
        return LinkRead("not_a_web_link", url.strip(), None)
    address = parts._replace(fragment="").geturl()
    now = datetime.now(UTC)
    cached = db.scalar(select(LinkPreview).where(LinkPreview.url == address))
    if cached is not None:
        age = now - cached.fetched_at
        if (cached.outcome in ("ok", "not_product") and age < FRESH_FOR) or age < RETRY_AFTER:
            return _suggest(db, user, address, cached.outcome, cached.fetched_at, cached.data)
    db.commit()
    data: dict[str, Any] = {}
    try:
        page = reader.read(address)
        outcome = "ok" if page.is_product else "not_product"
        data = _stored(page)
    except PageBlocked:
        outcome = "blocked"
    except PageUnavailable:
        outcome = "unavailable"
    db.execute(
        insert(LinkPreview)
        .values(url=address, fetched_at=now, outcome=outcome, data=data)
        .on_conflict_do_update(
            index_elements=["url"],
            set_={"fetched_at": now, "outcome": outcome, "data": data, "updated_at": now},
        )
    )
    db.flush()
    return _suggest(db, user, address, outcome, now, data)


def _stored(page: PageData) -> dict[str, Any]:
    return {
        "url": page.url,
        "site": page.site,
        "title": page.title,
        "brand": page.brand,
        "image_url": page.image_url,
        "price": str(page.price) if page.price is not None else None,
        "currency": page.currency,
        "colour": page.colour,
        "material": page.material,
    }


def _suggest(
    db: Session,
    user: User,
    url: str,
    outcome: str,
    fetched_at: datetime,
    data: dict[str, Any],
) -> LinkRead:
    if outcome not in ("ok", "not_product"):
        return LinkRead(outcome, url, fetched_at)
    title = data.get("title") or ""
    words = " ".join(filter(None, [data.get("colour"), data.get("material"), title]))
    price = None
    other = None
    if data.get("price"):
        currency = data.get("currency") or "INR"
        if currency == "INR":
            price = int((Decimal(data["price"]) * 100).to_integral_value())
        else:
            other = f"{currency} {data['price']}"
    return LinkRead(
        outcome=outcome,
        url=data.get("url") or url,
        fetched_at=fetched_at,
        site=data.get("site"),
        title=title or None,
        brand=data.get("brand"),
        image_url=data.get("image_url"),
        price=price,
        other_currency=other,
        category_id=_best(title, _category_names(db, user)),
        color_primary=_best(words, _colour_names(db)),
        fabric=_best(words, _fabric_names(db)),
    )


def _normal(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9]+", " ", text.lower()).split())


def _best(text: str, names: dict[str, str]) -> str | None:
    """The id whose name appears in the text as whole words, the longest name winning
    ("light blue" over "blue", "formal shirt" over "shirt")."""
    haystack = f" {_normal(text)} "
    found = [(len(name), name, id_) for name, id_ in names.items() if f" {name} " in haystack]
    return max(found)[2] if found else None


def _category_names(db: Session, user: User) -> dict[str, str]:
    names: dict[str, str] = {}
    for category in categories.list_categories(db, user):
        for name in (category.name, category.id.replace("_", " ")):
            normal = _normal(name)
            if normal and not normal.startswith("custom"):
                names.setdefault(normal, category.id)
                names.setdefault(normal + "s", category.id)
    return names


def _colour_names(db: Session) -> dict[str, str]:
    names: dict[str, str] = {}
    for family in reference.ordered(db, ColorFamily):
        for part in [*family.name.split(" / "), family.id.replace("_", " ")]:
            normal = _normal(part.split(" (")[0])
            if normal:
                names.setdefault(normal, family.id)
    return names


def _fabric_names(db: Session) -> dict[str, str]:
    return {
        _normal(term.name): term.id
        for term in reference.terms(db, "fabric")
        if term.id not in ("other", "blend")
    }


# Shop search links and catalogue products for a gap or a candidate.


@dataclass(frozen=True)
class Ranked:
    product: CatalogProduct
    coverage_gain: float
    new_outfits: int
    redundancy: float
    closest: str | None


@dataclass(frozen=True)
class ShopFor:
    query: str
    links: list[SearchLink]
    # The person's usual spend for its kind of clothing, shown beside the links.
    price_cap: int | None
    group_name: str
    # None when no demo catalogue is loaded.
    products: list[Ranked] | None


def shop_for_staple(db: Session, s: Setting, staple: Archetype) -> ShopFor:
    return _shop(db, s, staple_item(s, staple))


def shop_for_candidate(db: Session, s: Setting, candidate: Candidate) -> ShopFor:
    names = ItemNames(db, s.user)
    item = candidate_item(s, candidate, names.display_name(candidate))
    return _shop(db, s, item)


def _shop(db: Session, s: Setting, item: EngineItem) -> ShopFor:
    category = s.categories[item.category_id]
    colour = s.families[item.color_family].name.split(" / ")[0].split(" (")[0]
    words = [colour, category.name.lower()]
    sections = set(s.profile.sections)
    if sections == {"menswear"}:
        words.append("men")
    elif sections == {"womenswear"}:
        words.append("women")
    query, links = search_links(words)
    return ShopFor(
        query=query,
        links=links,
        price_cap=s.profile.category_budgets.get(category.group_id),
        group_name=s.groups.get(category.group_id, ""),
        products=_ranked(db, s, item) if has_catalogue(db) else None,
    )


def has_catalogue(db: Session) -> bool:
    return db.scalar(select(func.count()).select_from(CatalogProduct)) != 0


def _ranked(db: Session, s: Setting, target: EngineItem) -> list[Ranked]:
    """Catalogue products of the same category, the closest in colour first, weighed by
    what each would add: coverage gain where the person is short, less for each that's like
    something owned. Duplicates of what's owned are left out."""
    query = select(CatalogProduct).where(CatalogProduct.category_id == target.category_id)
    if s.profile.sections:
        query = query.where(CatalogProduct.sections.overlap(list(s.profile.sections)))
    rows = list(db.scalars(query.order_by(CatalogProduct.title).limit(500)))
    if not rows:
        return []
    items = {row.id: product_item(s, row) for row in rows}
    rows.sort(key=lambda row: -engine.colour_closeness(items[row.id], target))
    owned = [item for item in steady(s.wardrobe).items if item.owner_id == str(s.user.id)]
    names = {item.id: item.name for item in owned}
    before = s.before
    short = (
        [cell for cell, n in before.coverage.items() if n < DEFAULT.coverage_cap] if before else []
    )
    found: list[Ranked] = []
    pairs = s.pairs()
    for row in rows[:WEIGHED]:
        item = items[row.id]
        near, alike = engine.closest(item, owned)
        if alike >= DEFAULT.duplicate_at:
            continue
        gain, new = 0.0, 0
        if short and before is not None:
            outfits = engine.outfits_with(
                replace(s.wardrobe, items=(*s.wardrobe.items, item)),
                s.base,
                s.engine_occasions,
                s.seasons,
                [item],
                DEFAULT,
                pairs,
                cells=short,
            )
            added = {cell: len(cores) for cell, cores in outfits.cells.items() if cores}
            gain = engine.coverage_gain(before.coverage, added)
            new = len(outfits.distinct())
        found.append(
            Ranked(row, round(gain, 4), new, round(alike, 4), names.get(near.id) if near else None)
        )
    found.sort(key=lambda r: (-r.coverage_gain * (1 - r.redundancy), -r.new_outfits))
    return found[:SHOWN]


def product_item(s: Setting, row: CatalogProduct) -> EngineItem:
    category = s.categories[row.category_id]
    family = s.families[row.color_primary]
    return EngineItem(
        id=CATALOG + str(row.id),
        owner_id=str(s.user.id),
        name=row.title,
        slot=category.slot,
        category_id=row.category_id,
        group_id=category.group_id,
        color_family=row.color_primary,
        color_neutrality=family.neutrality,
        color_hex=family.hex,
        pattern=row.pattern,
        fabric=row.fabric,
        formality=row.formality,
        warmth=row.warmth,
        seasons=frozenset(row.seasons),
        wears_before_wash=category.wears_before_wash,
        traits=frozenset(category.traits),
    )


def find_product(db: Session, product_id: Any) -> CatalogProduct | None:
    return db.get(CatalogProduct, product_id)


def candidate_fields(row: CatalogProduct) -> dict[str, Any]:
    """A catalogue product as a candidate. Demo products have no price or link to copy."""
    return {
        "source": "catalog",
        "name": row.title[:100],
        "brand": row.brand,
        "url": row.url,
        "image_url": row.image_url,
        "price": row.price if not row.is_demo else None,
        "category_id": row.category_id,
        "color_primary": row.color_primary,
        "pattern": row.pattern,
        "fabric": row.fabric,
        "formality": row.formality,
        "warmth": row.warmth,
        "seasons": row.seasons,
    }


def known(db: Session) -> tuple[set[str], set[str], set[str], dict[str, Category]]:
    """For the catalogue loader: category ids, colour ids, fabric ids, and categories."""
    rows = {c.id: c for c in db.scalars(select(Category).where(Category.user_id.is_(None)))}
    colours = {family.id for family in reference.ordered(db, ColorFamily)}
    fabrics = {
        term.id
        for term in db.scalars(select(VocabularyTerm).where(VocabularyTerm.kind == "fabric"))
    }
    return set(rows), colours, fabrics, rows
