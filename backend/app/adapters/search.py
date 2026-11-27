"""Web search for the Trend Scout (docs/AGENTS.md, section 7; D58).

One interface, three settings: Tavily over HTTPS with Python's own HTTP client (no SDK), a fake
that serves recorded results, and none at all (SEARCH_PROVIDER=off). A timeout, and one retry
when the service is busy or erring; anything else is SearchUnavailable, and the run stops
cleanly.

Tavily's terms let it keep queries and train models on them, so a query must never carry
anything about a person: the Trend Scout builds its queries from the season, the sections,
style names, and the festive calendar.
"""

import json
import logging
import urllib.error
import urllib.request
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import date, datetime
from email.utils import parsedate_to_datetime
from functools import lru_cache
from typing import Any, Literal, Protocol

from app.core.config import get_settings

log = logging.getLogger(__name__)

API_URL = "https://api.tavily.com/search"
TIMEOUT_SECONDS = 30
ATTEMPTS = 2
RETRY_STATUSES = {429, 500, 502, 503, 504}
# What a basic search costs, when the answer doesn't say (checked October 2026).
BASIC_CREDITS = 1
USER_AGENT = "WearWise/1.0"


class SearchUnavailable(Exception):
    """The search service didn't answer, refused, or the plan's credits ran out."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class SearchQuery:
    text: str
    # Only pages from the last this many days.
    days: int = 30
    # The only sites searched, when given; and sites never searched.
    sites: tuple[str, ...] = ()
    blocked_sites: tuple[str, ...] = ()
    max_results: int = 5


@dataclass(frozen=True)
class SearchResult:
    url: str
    title: str
    # The page's text as the search returned it: up to three passages.
    content: str
    # The search's best estimate of when the page was published or updated; None when unknown.
    published_on: date | None
    score: float


@dataclass(frozen=True)
class SearchResponse:
    results: tuple[SearchResult, ...]
    # Credits the search used, as the service reported them.
    credits: int


class WebSearch(Protocol):
    def search(self, query: SearchQuery) -> SearchResponse: ...


class TavilySearch:
    def __init__(self, key: str) -> None:
        self._key = key

    def search(self, query: SearchQuery) -> SearchResponse:
        body: dict[str, Any] = {
            "query": query.text,
            "topic": "general",
            "search_depth": "basic",
            "chunks_per_source": 3,
            "max_results": query.max_results,
            "time_range": _time_range(query.days),
            # Pages without a date, or outside the window, are left out by the service.
            "include_published_date": True,
            "filter_by_published_date": True,
            "country": "india",
            "include_usage": True,
        }
        if query.sites:
            body["include_domains"] = list(query.sites)
        if query.blocked_sites:
            body["exclude_domains"] = list(query.blocked_sites)
        data = self._post(body)
        results = tuple(
            SearchResult(
                url=str(found.get("url") or ""),
                title=str(found.get("title") or "").strip(),
                content=str(found.get("content") or "").strip(),
                published_on=parse_date(found.get("published_date")),
                score=float(found.get("score") or 0),
            )
            for found in data.get("results") or []
            if found.get("url")
        )
        usage = data.get("usage") or {}
        return SearchResponse(results, int(usage.get("credits", BASIC_CREDITS)))

    def _post(self, body: dict[str, Any]) -> dict[str, Any]:
        payload = json.dumps(body).encode()
        for attempt in range(ATTEMPTS):
            request = urllib.request.Request(
                API_URL,
                data=payload,
                method="POST",
                headers={
                    "authorization": f"Bearer {self._key}",
                    "content-type": "application/json",
                    "user-agent": USER_AGENT,
                },
            )
            try:
                with urllib.request.urlopen(request, timeout=TIMEOUT_SECONDS) as response:
                    data: dict[str, Any] = json.loads(response.read())
                    return data
            except urllib.error.HTTPError as error:
                log.warning("Search service answered %s", error.code)
                if error.code in (432, 433):
                    raise SearchUnavailable("out_of_credits") from error
                if error.code not in RETRY_STATUSES or attempt == ATTEMPTS - 1:
                    raise SearchUnavailable("refused" if error.code < 500 else "down") from error
            except (urllib.error.URLError, TimeoutError, ValueError) as error:
                log.warning("Search service unreachable: %s", error)
                if attempt == ATTEMPTS - 1:
                    raise SearchUnavailable("down") from error
        raise SearchUnavailable("down")  # pragma: no cover


def _time_range(days: int) -> Literal["day", "week", "month", "year"]:
    if days <= 1:
        return "day"
    if days <= 7:
        return "week"
    if days <= 31:
        return "month"
    return "year"


def parse_date(value: Any) -> date | None:
    """A published date as the service gives it ("Tue, 11 Mar 2025 17:00:00 GMT"), or as an
    ISO date; None when there isn't one, or it can't be read."""
    if not isinstance(value, str) or not value.strip():
        return None
    text = value.strip()
    try:
        return datetime.fromisoformat(text.replace("Z", "+00:00")).date()
    except ValueError:
        pass
    try:
        return parsedate_to_datetime(text).date()
    except TypeError, ValueError, IndexError:
        return None


@dataclass
class FakeSearch:
    """Recorded results, for tests and working offline: every query gets the same pages unless
    `by_query` names its own. Remembers the queries; `down` makes every search fail."""

    pages: Sequence[SearchResult] = ()
    by_query: dict[str, Sequence[SearchResult]] = field(default_factory=dict)
    credits: int = BASIC_CREDITS
    down: bool = False
    asked: list[SearchQuery] = field(default_factory=list)

    def search(self, query: SearchQuery) -> SearchResponse:
        self.asked.append(query)
        if self.down:
            raise SearchUnavailable("down")
        found = self.by_query.get(query.text, self.pages)
        return SearchResponse(tuple(found)[: query.max_results], self.credits)


@lru_cache
def get_web_search() -> WebSearch | None:
    settings = get_settings()
    if settings.search_provider == "tavily":
        return TavilySearch(settings.search_api_key or "")
    if settings.search_provider == "fake":
        return FakeSearch()
    return None
