"""Real products: pasted links, shop searches, and the demo catalogue."""

from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select, update
from sqlalchemy.orm import Session
from wardrobe_support import add_item

from app.adapters.pages import PageData, PageUnavailable
from app.adapters.products import FakePageReader, PageBlocked
from app.models import CatalogProduct, LinkPreview
from app.services import insights, shopping
from app.services.catalog import clear_catalog, load_catalog

PREVIEW = "/api/v1/links/preview"
SHOP = "/api/v1/shopping/shop"
LINK = "https://shop.example.com/p/123"


@pytest.fixture(autouse=True)
def fresh_caches() -> Iterator[None]:
    insights.without_cache()
    shopping.without_cache()
    yield
    insights.without_cache()
    shopping.without_cache()


def page(**fields: Any) -> PageData:
    values: dict[str, Any] = {
        "url": LINK,
        "site": "Example Shop",
        "title": "Men Navy Slim Fit Chinos",
        "brand": "Northline",
        "image_url": "https://cdn.example.com/navy.jpg",
        "price": Decimal("1799.00"),
        "currency": "INR",
        "colour": "Navy Blue",
        "material": "Cotton",
        "is_product": True,
    }
    values.update(fields)
    return PageData(**values)


def test_a_pasted_page_is_read_once_and_suggests_the_form(
    sam: TestClient, pages: FakePageReader
) -> None:
    pages.found[LINK] = page()

    first = sam.post(PREVIEW, json={"url": f"{LINK}#reviews"})
    second = sam.post(PREVIEW, json={"url": LINK})

    assert first.status_code == 200, first.text
    found = first.json()
    assert found["outcome"] == "ok"
    assert (found["title"], found["brand"], found["site"]) == (
        "Men Navy Slim Fit Chinos",
        "Northline",
        "Example Shop",
    )
    assert found["price"] == 179900 and found["other_currency"] is None
    assert (found["category_id"], found["color_primary"], found["fabric"]) == (
        "chinos",
        "navy",
        "cotton",
    )
    assert found["fetched_at"] is not None
    # Read once: the second paste (and the fragment-free address) came from the cache.
    assert pages.reads == [LINK]
    assert second.json()["title"] == found["title"]


def test_a_day_later_the_page_is_read_again(
    sam: TestClient, pages: FakePageReader, db: Session
) -> None:
    pages.found[LINK] = page()
    sam.post(PREVIEW, json={"url": LINK})
    db.execute(
        update(LinkPreview).values(fetched_at=datetime.now(UTC) - timedelta(days=1, minutes=1))
    )
    pages.found[LINK] = page(price=Decimal("1599"))

    again = sam.post(PREVIEW, json={"url": LINK}).json()

    assert len(pages.reads) == 2
    assert again["price"] == 159900


def test_a_blocked_or_unreachable_page_is_an_answer_not_an_error(
    sam: TestClient, pages: FakePageReader
) -> None:
    pages.found[LINK] = PageBlocked(LINK)
    pages.found["https://down.example.com/p"] = PageUnavailable("timeout")

    blocked = sam.post(PREVIEW, json={"url": LINK})
    down = sam.post(PREVIEW, json={"url": "https://down.example.com/p"})
    again = sam.post(PREVIEW, json={"url": "https://down.example.com/p"})
    odd = sam.post(PREVIEW, json={"url": "javascript:alert(1)"})

    assert (blocked.status_code, blocked.json()["outcome"]) == (200, "blocked")
    assert blocked.json()["title"] is None
    assert down.json()["outcome"] == "unavailable"
    # A failure is remembered for a while rather than retried at once.
    assert again.json()["outcome"] == "unavailable"
    assert pages.reads.count("https://down.example.com/p") == 1
    assert odd.json()["outcome"] == "not_a_web_link"


def test_a_page_without_a_product_and_a_foreign_price(
    sam: TestClient, pages: FakePageReader
) -> None:
    pages.found[LINK] = page(is_product=False, title="Sign in", price=None, colour=None)
    pages.found["https://us.example.com/p"] = page(price=Decimal("30"), currency="USD")

    login = sam.post(PREVIEW, json={"url": LINK}).json()
    foreign = sam.post(PREVIEW, json={"url": "https://us.example.com/p"}).json()

    assert login["outcome"] == "not_product" and login["category_id"] is None
    assert foreign["price"] is None and foreign["other_currency"] == "USD 30"


def test_a_candidate_from_a_link_keeps_its_source_and_picture(sam: TestClient) -> None:
    made = sam.post(
        "/api/v1/candidates",
        json={
            "source": "link",
            "category_id": "chinos",
            "color_primary": "navy",
            "url": LINK,
            "image_url": "https://cdn.example.com/navy.jpg",
            "price": 179900,
        },
    )
    bad = sam.post(
        "/api/v1/candidates",
        json={"category_id": "chinos", "color_primary": "navy", "image_url": "javascript:x"},
    )
    staple = sam.post(
        "/api/v1/candidates",
        json={"source": "archetype", "category_id": "chinos", "color_primary": "navy"},
    )

    assert made.status_code == 201, made.text
    assert (made.json()["source"], made.json()["image_url"]) == (
        "link",
        "https://cdn.example.com/navy.jpg",
    )
    assert made.json()["price_checked_at"] is not None
    assert bad.status_code == 422
    # Only "manual" and "link" can be sent; staples and catalogue products have their own routes.
    assert staple.status_code == 422


def test_shop_links_for_a_staple_with_the_usual_spend(sam: TestClient) -> None:
    sam.patch(
        "/api/v1/profile",
        json={"sections": ["menswear"], "category_budgets": {"bottoms": 200000}},
    )

    found = sam.get(SHOP, params={"archetype_id": "navy_chinos"}).json()

    assert found["query"] == "Navy chinos men"
    assert [link["shop"] for link in found["links"]] == ["Myntra", "AJIO", "Flipkart", "Amazon"]
    assert found["links"][0]["url"].startswith("https://www.myntra.com/navy-chinos-men?")
    assert found["price_cap"] == 200000 and found["group_name"] == "Bottoms"
    # No demo catalogue loaded: no products, rather than made-up ones.
    assert found["products"] is None


def styles_rows() -> list[dict[str, str]]:
    def row(id_: str, article: str, colour: str, name: str, **extra: str) -> dict[str, str]:
        return {
            "id": id_,
            "gender": extra.get("gender", "Men"),
            "articleType": article,
            "baseColour": colour,
            "usage": extra.get("usage", "Casual"),
            "productDisplayName": name,
        }

    return [
        row("1", "Trousers", "Navy Blue", "Peter England Men Navy Trousers"),
        row("2", "Trousers", "Black", "Arrow Men Black Formal Trousers", usage="Formal"),
        row("3", "Shirts", "White", "Van Heusen Men White Striped Formal Shirt", usage="Formal"),
        row("4", "Casual Shoes", "Brown", "Woodland Men Brown Leather Casual Shoes"),
        row("5", "Lipstick", "Red", "Lakme Red Lipstick", gender="Women"),
        row("6", "Shirts", "Fluorescent Green", "Some Green Shirt"),
        row("7", "Tshirts", "Blue", "Boys Blue T-shirt", gender="Boys"),
        row("8", "Jeans", "Blue", ""),
        row("9", "Jeans", "Blue", "Roadster Men Blue Denim Jeans"),
    ]


def test_the_catalogue_loader_maps_clear_labels_and_skips_the_rest(db: Session) -> None:
    loaded = load_catalog(db, styles_rows(), "test-catalog")
    again = load_catalog(db, styles_rows(), "test-catalog")

    rows = {
        row.external_id: row
        for row in db.scalars(select(CatalogProduct).where(CatalogProduct.source == "test-catalog"))
    }
    assert loaded.loaded == again.loaded == 5
    assert loaded.skipped == {"category": 1, "colour": 1, "section": 1, "incomplete": 1}
    assert set(rows) == {"1", "2", "3", "4", "9"}
    assert rows["2"].category_id == "formal_trousers"
    assert (rows["3"].category_id, rows["3"].pattern) == ("formal_shirt", "stripe")
    assert rows["3"].formality >= 4
    assert (rows["4"].category_id, rows["4"].fabric) == ("sneakers", "leather")
    assert rows["9"].fabric == "denim"
    assert all(row.is_demo and row.price is None and row.url is None for row in rows.values())
    assert all(row.seasons == [] for row in rows.values())
    assert clear_catalog(db, "test-catalog") == 5


def test_demo_products_are_ranked_by_what_they_add_and_marked_as_demo(
    sam: TestClient, db: Session
) -> None:
    sam.patch("/api/v1/profile", json={"occasion_ids": ["college"], "sections": ["menswear"]})
    add_item(sam, "casual_shirt", "white", fabric="cotton")
    add_item(sam, "loafers", "brown", fabric="leather")
    add_item(sam, "casual_trousers", "navy", fabric="cotton")
    load_catalog(db, styles_rows(), "test-catalog")

    found = sam.get(SHOP, params={"archetype_id": "beige_chinos"}).json()
    trousers = sam.get(SHOP, params={"archetype_id": "grey_formal_trousers"}).json()

    assert found["products"] == []
    products = trousers["products"]
    # Only products of the staple's own kind are weighed: the formal trousers, as demo.
    assert [p["title"] for p in products] == ["Arrow Men Black Formal Trousers"]
    shown = products[0]
    assert shown["is_demo"] and shown["price"] is None and shown["url"] is None
    assert shown["source"] == "test-catalog" and shown["fetched_at"]
    # Every product shown has a real link or is marked as demo.
    assert all(p["is_demo"] or p["url"] for p in products)


def test_a_catalogue_product_goes_on_the_list_without_a_price(sam: TestClient, db: Session) -> None:
    load_catalog(db, styles_rows(), "test-catalog")
    product = db.scalar(select(CatalogProduct).where(CatalogProduct.external_id == "9"))
    assert product is not None

    made = sam.post("/api/v1/candidates/from-catalog", json={"product_id": str(product.id)})

    assert made.status_code == 201, made.text
    assert (made.json()["source"], made.json()["category_id"]) == ("catalog", "jeans")
    assert made.json()["price"] is None and made.json()["name"] == "Roadster Men Blue Denim Jeans"


def test_shop_for_another_accounts_candidate_is_404(sam: TestClient, ana: TestClient) -> None:
    mine = sam.post("/api/v1/candidates", json={"category_id": "chinos", "color_primary": "navy"})

    theirs = ana.get(SHOP, params={"candidate_id": mine.json()["id"]})
    own = sam.get(SHOP, params={"candidate_id": mine.json()["id"]})

    assert theirs.status_code == 404
    assert own.status_code == 200 and own.json()["query"] == "Navy chinos"


def test_shop_needs_exactly_one_thing_to_shop_for(sam: TestClient) -> None:
    assert sam.get(SHOP).status_code == 422
    assert sam.get(SHOP, params={"archetype_id": "nope"}).status_code == 404


def test_reading_links_is_limited(
    sam: TestClient, pages: FakePageReader, monkeypatch: pytest.MonkeyPatch
) -> None:
    from app.api import shopping as routes
    from app.services import rate_limit

    monkeypatch.setattr(routes, "LINKS_PER_USER", rate_limit.Limit(2, timedelta(hours=1)))

    codes = [sam.post(PREVIEW, json={"url": f"{LINK}?n={n}"}).status_code for n in range(3)]

    assert codes == [200, 200, 429]


def test_products_need_a_login(client: TestClient) -> None:
    assert client.post(PREVIEW, json={"url": LINK}).status_code == 401
    assert client.get(SHOP, params={"archetype_id": "navy_chinos"}).status_code == 401
