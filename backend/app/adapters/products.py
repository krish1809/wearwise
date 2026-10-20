"""Where products come from (docs/SHOPPING.md, part 2). Two kinds of source here:

- Shop search links: a gap or a candidate turned into search words, as links to each shop's
  own search. Nothing is fetched; the person browses there. Always works.
- A page reader for one link a person pastes (adapters/pages.py), with a fake for tests and
  offline work (PAGE_READER=fake).

The demo catalogue is rows in our own database (services/products.py), not an outside call.
"""

import re
from dataclasses import dataclass, field
from functools import lru_cache
from typing import Protocol
from urllib.parse import quote, quote_plus

from app.adapters import pages
from app.adapters.pages import PageBlocked, PageData, PageUnavailable
from app.core.config import get_settings

__all__ = ["PageBlocked", "PageData", "PageUnavailable"]


@dataclass(frozen=True)
class Shop:
    id: str
    name: str
    # {q}: the words, %-encoded; {plus}: with + for spaces; {slug}: hyphenated.
    search: str


# Each shop's public search page, as its own site builds the address (checked October 2026;
# if a shop changes its addresses, change the template here). No price filters: they aren't
# documented and change often, so the price cap is shown beside the links instead.
SHOPS = (
    Shop("myntra", "Myntra", "https://www.myntra.com/{slug}?rawQuery={q}"),
    Shop("ajio", "AJIO", "https://www.ajio.com/search/?text={q}"),
    Shop("flipkart", "Flipkart", "https://www.flipkart.com/search?q={plus}"),
    Shop("amazon", "Amazon", "https://www.amazon.in/s?k={plus}"),
)


@dataclass(frozen=True)
class SearchLink:
    shop_id: str
    shop: str
    url: str


def search_links(words: list[str]) -> tuple[str, list[SearchLink]]:
    """The search words joined, and a link to each shop's search for them."""
    query = " ".join(" ".join(word.split()) for word in words if word and word.strip())
    slug = "-".join(re.sub(r"[^a-z0-9]+", " ", query.lower()).split())
    return query, [
        SearchLink(
            shop.id,
            shop.name,
            shop.search.format(q=quote(query), plus=quote_plus(query), slug=quote(slug)),
        )
        for shop in SHOPS
    ]


class PageReader(Protocol):
    def read(self, url: str) -> PageData:
        """The preview data on the page. Raises PageBlocked when robots.txt says no and
        PageUnavailable when it can't be read."""
        ...


class WebPageReader:
    def read(self, url: str) -> PageData:
        if not pages.allowed(url):
            raise PageBlocked(url)
        found = pages.fetch(url, "text/html,application/xhtml+xml;q=0.9,*/*;q=0.1")
        if "html" not in found.content_type.lower():
            raise PageUnavailable("not_a_page")
        if not pages.allowed(found.url):
            raise PageBlocked(found.url)
        return pages.parse(found.url, found.text)


@dataclass
class FakePageReader:
    """Canned pages by address; anything else is unreachable."""

    found: dict[str, PageData | Exception] = field(default_factory=dict)
    reads: list[str] = field(default_factory=list)

    def read(self, url: str) -> PageData:
        self.reads.append(url)
        answer = self.found.get(url)
        if answer is None:
            raise PageUnavailable("unreachable")
        if isinstance(answer, Exception):
            raise answer
        return answer


@lru_cache
def get_page_reader() -> PageReader:
    if get_settings().page_reader == "fake":
        return FakePageReader()
    return WebPageReader()
