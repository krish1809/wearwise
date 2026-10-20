"""Reading one product page a person pasted: its public preview data, nothing else.

This isn't a crawler. It fetches the one page a person asked about, and the site's
robots.txt, and reads the preview data shops publish for link previews: Open Graph tags and
schema.org Product data (docs/SHOPPING.md, 2.2). It:

- obeys robots.txt for its user agent, and treats a robots.txt it can't read as a no;
- sends no cookies and logs in nowhere; a login page, a CAPTCHA, or a bot check is simply a
  page without product data, and the person fills in the details instead;
- talks only to public addresses: each host is resolved and every address checked, and the
  connection is made to a checked address, so a link can't point the server at its own
  network;
- follows at most three redirects, checking each, reads at most 2 MB, and gives up after
  five seconds, with one retry for a server error or a timeout.

Callers cache what it returns (one read per page per day) and fetch outside any database
transaction. Text from pages is untrusted: it's trimmed, length-limited, and only ever shown
or stored as plain text.
"""

import http.client
import ipaddress
import json
import logging
import re
import socket
import ssl
import time
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from html.parser import HTMLParser
from threading import Lock
from typing import Any
from urllib.parse import SplitResult, urljoin, urlsplit
from urllib.robotparser import RobotFileParser

log = logging.getLogger(__name__)

USER_AGENT = "WearWise/1.0 (reads a page a person saved to their shopping list)"
# The name robots.txt rules are matched against.
ROBOTS_AGENT = "WearWise"
TIMEOUT_SECONDS = 5
ATTEMPTS = 2
MAX_REDIRECTS = 3
MAX_PAGE_BYTES = 2_000_000
MAX_ROBOTS_BYTES = 500_000
ROBOTS_CACHE_SECONDS = 24 * 3600
REDIRECTS = {301, 302, 303, 307, 308}
# The standard ports only (None: the scheme's own).
PORTS: tuple[int | None, ...] = (None, 80, 443)


class PageBlocked(Exception):
    """The site's robots.txt doesn't allow reading this page."""


class PageUnavailable(Exception):
    """The page couldn't be read: unreachable, an error status, not a web page, too large,
    or at an address that isn't public."""

    def __init__(self, reason: str, status: int | None = None) -> None:
        super().__init__(reason)
        self.reason = reason
        self.status = status


@dataclass(frozen=True)
class PageData:
    """What a product page says about itself. Every field may be missing."""

    url: str
    site: str | None
    title: str | None
    brand: str | None
    image_url: str | None
    # As written on the page, in major units (rupees), and its currency code.
    price: Decimal | None
    currency: str | None
    colour: str | None
    material: str | None
    # True when the page describes a product (schema.org Product, og:type product, or a
    # price), rather than a home page or a login screen.
    is_product: bool


# Fetching.


def check_url(url: str) -> SplitResult:
    """A web address the reader may fetch: http or https, a host name, no password, and the
    standard port."""
    parts = urlsplit(url.strip())
    if parts.scheme not in ("http", "https") or not parts.hostname:
        raise PageUnavailable("not_a_web_link")
    if parts.username or parts.password:
        raise PageUnavailable("not_a_web_link")
    try:
        port = parts.port
    except ValueError as error:
        raise PageUnavailable("not_a_web_link") from error
    if port not in PORTS:
        raise PageUnavailable("not_a_web_link")
    return parts


def public_address(host: str, port: int) -> str:
    """The first address of a host, if every address it has is a public one."""
    try:
        found = socket.getaddrinfo(host, port, type=socket.SOCK_STREAM)
    except (OSError, UnicodeError) as error:
        raise PageUnavailable("unreachable") from error
    addresses = [str(info[4][0]) for info in found]
    if not addresses:
        raise PageUnavailable("unreachable")
    for address in addresses:
        ip = ipaddress.ip_address(address.split("%")[0])
        if not ip.is_global or ip.is_multicast:
            raise PageUnavailable("not_public")
    return addresses[0]


class _PinnedHTTP(http.client.HTTPConnection):
    """Connects to an address already checked, whatever the host name resolves to now."""

    def __init__(self, host: str, address: str, port: int, timeout: float) -> None:
        super().__init__(host, port, timeout=timeout)
        self._address = address

    def connect(self) -> None:
        self.sock = socket.create_connection((self._address, self.port), self.timeout)


class _PinnedHTTPS(http.client.HTTPSConnection):
    def __init__(self, host: str, address: str, port: int, timeout: float) -> None:
        self._tls = ssl.create_default_context()
        super().__init__(host, port, timeout=timeout, context=self._tls)
        self._address = address

    def connect(self) -> None:
        raw = socket.create_connection((self._address, self.port), self.timeout)
        self.sock = self._tls.wrap_socket(raw, server_hostname=self.host)


@dataclass(frozen=True)
class Fetched:
    url: str
    content_type: str
    text: str


def fetch(url: str, accept: str, limit: int = MAX_PAGE_BYTES) -> Fetched:
    """GET a page, following up to three redirects, retrying once on a server error or a
    timeout. Raises PageUnavailable."""
    for attempt in range(ATTEMPTS):
        try:
            return _fetch_once(url, accept, limit)
        except PageUnavailable as error:
            retry = error.reason in ("timeout", "server_error")
            if not retry or attempt == ATTEMPTS - 1:
                raise
    raise PageUnavailable("unreachable")  # pragma: no cover


def _fetch_once(url: str, accept: str, limit: int) -> Fetched:
    for _ in range(MAX_REDIRECTS + 1):
        parts = check_url(url)
        host = parts.hostname or ""
        port = parts.port or (443 if parts.scheme == "https" else 80)
        address = public_address(host, port)
        connection: http.client.HTTPConnection = (
            _PinnedHTTPS(host, address, port, TIMEOUT_SECONDS)
            if parts.scheme == "https"
            else _PinnedHTTP(host, address, port, TIMEOUT_SECONDS)
        )
        path = parts.path or "/"
        if parts.query:
            path += f"?{parts.query}"
        try:
            connection.request(
                "GET",
                path,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": accept,
                    "Accept-Language": "en-IN,en;q=0.8",
                },
            )
            response = connection.getresponse()
            if response.status in REDIRECTS:
                location = response.getheader("Location")
                if not location:
                    raise PageUnavailable("bad_redirect", response.status)
                url = urljoin(url, location)
                continue
            if response.status >= 500:
                raise PageUnavailable("server_error", response.status)
            if response.status >= 400:
                raise PageUnavailable("refused", response.status)
            declared = response.getheader("Content-Length")
            if declared and declared.isdigit() and int(declared) > limit:
                raise PageUnavailable("too_large", response.status)
            body = response.read(limit + 1)
            if len(body) > limit:
                raise PageUnavailable("too_large", response.status)
            content_type = response.getheader("Content-Type") or ""
            return Fetched(url, content_type, _decode(body, content_type))
        except TimeoutError as error:
            raise PageUnavailable("timeout") from error
        except (OSError, http.client.HTTPException) as error:
            raise PageUnavailable("unreachable") from error
        finally:
            connection.close()
    raise PageUnavailable("too_many_redirects")


def _decode(body: bytes, content_type: str) -> str:
    match = re.search(r"charset=([\w-]+)", content_type, re.IGNORECASE)
    try:
        return body.decode(match.group(1) if match else "utf-8", errors="replace")
    except LookupError:
        return body.decode("utf-8", errors="replace")


# robots.txt.

_robots: dict[str, tuple[float, RobotFileParser | None, bool]] = {}
_robots_lock = Lock()


def allowed(url: str) -> bool:
    """Whether the site's robots.txt lets WearWise read this page. A missing robots.txt
    (404 or 410) allows everything; one that can't be read (refused, an error, a timeout)
    allows nothing."""
    parts = check_url(url)
    origin = f"{parts.scheme}://{parts.netloc}"
    now = time.monotonic()
    with _robots_lock:
        cached = _robots.get(origin)
    if cached is None or cached[0] < now:
        parser: RobotFileParser | None = None
        everything = False
        try:
            found = fetch(f"{origin}/robots.txt", "text/plain", MAX_ROBOTS_BYTES)
            parser = RobotFileParser()
            parser.parse(found.text.splitlines())
        except PageUnavailable as error:
            everything = error.status in (404, 410)
        cached = (now + ROBOTS_CACHE_SECONDS, parser, everything)
        with _robots_lock:
            _robots[origin] = cached
    _, parser, everything = cached
    if parser is None:
        return everything
    return parser.can_fetch(ROBOTS_AGENT, url)


def forget_robots() -> None:
    """For tests."""
    with _robots_lock:
        _robots.clear()


# Reading the preview data.


class _Head(HTMLParser):
    """Collects meta tags, the title, the canonical link, and JSON-LD scripts."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.meta: dict[str, str] = {}
        self.title = ""
        self.canonical: str | None = None
        self.scripts: list[str] = []
        self._in_title = False
        self._in_script = False
        self._script: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag == "meta":
            key = (values.get("property") or values.get("name") or "").lower()
            if key and "content" in values and key not in self.meta:
                self.meta[key] = values["content"]
        elif tag == "title":
            self._in_title = True
        elif tag == "link" and "canonical" in values.get("rel", "").lower().split():
            self.canonical = values.get("href") or None
        elif tag == "script" and values.get("type", "").lower() == "application/ld+json":
            self._in_script = True
            self._script = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "script" and self._in_script:
            self._in_script = False
            self.scripts.append("".join(self._script))

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title += data
        elif self._in_script:
            self._script.append(data)


def parse(url: str, html: str) -> PageData:
    """The preview data in a page: schema.org Product first, then Open Graph, then the
    title."""
    head = _Head()
    try:
        head.feed(html)
        head.close()
    except Exception:  # A broken page still gives what was read before the break.
        log.info("Couldn't finish parsing %s", url)
    meta = head.meta
    product = _product(head.scripts)
    offer = _offer(product.get("offers")) if product else {}
    price = _price(
        offer.get("price")
        or offer.get("lowPrice")
        or meta.get("product:price:amount")
        or meta.get("og:price:amount")
    )
    currency = _text(
        offer.get("priceCurrency")
        or meta.get("product:price:currency")
        or meta.get("og:price:currency"),
        3,
    )
    image = _image(product.get("image")) if product else None
    image = image or meta.get("og:image") or meta.get("twitter:image")
    canonical = head.canonical or meta.get("og:url")
    page_url = url
    if canonical:
        joined = urljoin(url, canonical)
        if urlsplit(joined).scheme in ("http", "https"):
            page_url = joined
    return PageData(
        url=page_url,
        site=_text(meta.get("og:site_name"), 100) or urlsplit(url).hostname,
        title=_text(
            (product.get("name") if product else None)
            or meta.get("og:title")
            or meta.get("twitter:title")
            or head.title,
            200,
        ),
        brand=_text(_name(product.get("brand")) if product else None, 100)
        or _text(meta.get("product:brand") or meta.get("og:brand"), 100),
        image_url=_absolute(url, image),
        price=price,
        currency=currency.upper() if currency else None,
        colour=_text(product.get("color") if product else None, 60),
        material=_text(product.get("material") if product else None, 60),
        is_product=bool(product)
        or meta.get("og:type", "").lower().startswith("product")
        or price is not None,
    )


def _product(scripts: list[str]) -> dict[str, Any]:
    for script in scripts:
        try:
            data = json.loads(script)
        except ValueError:
            continue
        found = _find_product(data)
        if found:
            return found
    return {}


def _find_product(data: Any, depth: int = 0) -> dict[str, Any] | None:
    if depth > 4:
        return None
    if isinstance(data, list):
        for entry in data:
            found = _find_product(entry, depth + 1)
            if found:
                return found
        return None
    if not isinstance(data, dict):
        return None
    kind = data.get("@type")
    kinds = kind if isinstance(kind, list) else [kind]
    if "Product" in kinds or "ProductGroup" in kinds:
        return data
    if "@graph" in data:
        return _find_product(data["@graph"], depth + 1)
    return None


def _offer(offers: Any) -> dict[str, Any]:
    if isinstance(offers, list):
        offers = offers[0] if offers else {}
    if isinstance(offers, dict):
        if offers.get("@type") == "AggregateOffer" and "offers" in offers:
            inner = _offer(offers["offers"])
            return inner or offers
        return offers
    return {}


def _price(value: Any) -> Decimal | None:
    if value is None:
        return None
    cleaned = re.sub(r"[^\d.]", "", str(value).replace(",", ""))
    if not cleaned or cleaned.count(".") > 1:
        return None
    try:
        price = Decimal(cleaned)
    except InvalidOperation:
        return None
    return price if price > 0 else None


def _image(value: Any) -> str | None:
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, dict):
        value = value.get("url") or value.get("contentUrl")
    return value if isinstance(value, str) else None


def _name(value: Any) -> str | None:
    if isinstance(value, list):
        value = value[0] if value else None
    if isinstance(value, dict):
        value = value.get("name")
    return value if isinstance(value, str) else None


def _absolute(base: str, value: str | None) -> str | None:
    if not value:
        return None
    joined = urljoin(base, value.strip())
    if urlsplit(joined).scheme not in ("http", "https") or len(joined) > 1000:
        return None
    return joined


def _text(value: Any, limit: int) -> str | None:
    """Untrusted text from a page: plain, one line, and no longer than `limit`."""
    if not isinstance(value, str):
        return None
    cleaned = "".join(ch for ch in " ".join(value.split()) if ch.isprintable())
    return cleaned[:limit].strip() or None
