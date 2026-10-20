"""Reading a pasted product page: what's read, and what's refused."""

import socket
import threading
from collections.abc import Iterator
from decimal import Decimal
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from app.adapters import pages
from app.adapters.pages import PageUnavailable, check_url, parse, public_address
from app.adapters.products import PageBlocked, WebPageReader, search_links

PRODUCT = """<!doctype html><html><head>
<title>Ignored when there's product data</title>
<meta property="og:site_name" content="Example Shop">
<meta property="og:image" content="/img/fallback.jpg">
<link rel="canonical" href="/p/navy-chinos">
<script type="application/ld+json">
{"@context": "https://schema.org", "@graph": [
  {"@type": "BreadcrumbList"},
  {"@type": "Product", "name": "Men Navy\\n  Slim Fit Chinos",
   "brand": {"@type": "Brand", "name": "Northline"},
   "image": ["https://cdn.example.com/navy.jpg"], "color": "Navy Blue",
   "material": "Cotton",
   "offers": {"@type": "Offer", "price": "1,799.00", "priceCurrency": "INR"}}
]}
</script></head><body>...</body></html>"""


def test_product_data_comes_from_schema_org_first() -> None:
    found = parse("https://shop.example.com/p/123?ref=x", PRODUCT)

    assert found.is_product
    assert found.title == "Men Navy Slim Fit Chinos"
    assert found.brand == "Northline"
    assert found.price == Decimal("1799.00") and found.currency == "INR"
    assert found.image_url == "https://cdn.example.com/navy.jpg"
    assert (found.colour, found.material) == ("Navy Blue", "Cotton")
    assert found.site == "Example Shop"
    assert found.url == "https://shop.example.com/p/navy-chinos"


def test_open_graph_stands_in_and_a_login_page_isnt_a_product() -> None:
    og = parse(
        "https://shop.example.com/x",
        '<meta property="og:title" content="White Sneakers">'
        '<meta property="og:type" content="product">'
        '<meta property="product:price:amount" content="₹2,499">'
        '<meta property="product:price:currency" content="inr">'
        '<meta property="og:image" content="javascript:alert(1)">',
    )
    login = parse("https://shop.example.com/login", "<title>Sign in</title><form></form>")

    assert og.is_product and og.title == "White Sneakers"
    assert (og.price, og.currency) == (Decimal("2499"), "INR")
    assert og.image_url is None
    assert not login.is_product and login.title == "Sign in"


def test_only_plain_web_links_on_standard_ports() -> None:
    for bad in (
        "ftp://shop.example.com/x",
        "https://user:secret@shop.example.com/x",
        "https://shop.example.com:8443/x",
        "javascript:alert(1)",
        "https:///nohost",
    ):
        with pytest.raises(PageUnavailable):
            check_url(bad)
    assert check_url("https://shop.example.com/p?id=1").hostname == "shop.example.com"


@pytest.mark.parametrize(
    "address", ["127.0.0.1", "10.0.0.5", "192.168.1.2", "169.254.169.254", "::1", "100.64.0.1"]
)
def test_private_addresses_are_refused(monkeypatch: pytest.MonkeyPatch, address: str) -> None:
    def resolve(host: str, port: int, **_: object) -> list[tuple[object, ...]]:
        return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (address, port))]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)

    with pytest.raises(PageUnavailable) as error:
        public_address("shop.example.com", 443)
    assert error.value.reason == "not_public"


def test_a_host_with_any_private_address_is_refused(monkeypatch: pytest.MonkeyPatch) -> None:
    def resolve(host: str, port: int, **_: object) -> list[tuple[object, ...]]:
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", port)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.1.2.3", port)),
        ]

    monkeypatch.setattr(socket, "getaddrinfo", resolve)

    with pytest.raises(PageUnavailable):
        public_address("shop.example.com", 443)


def test_search_links_take_the_words_to_each_shop() -> None:
    query, links = search_links(["Navy", "chinos", " men "])

    assert query == "Navy chinos men"
    by_shop = {link.shop_id: link.url for link in links}
    assert (
        by_shop["myntra"] == "https://www.myntra.com/navy-chinos-men?rawQuery=Navy%20chinos%20men"
    )
    assert by_shop["ajio"] == "https://www.ajio.com/search/?text=Navy%20chinos%20men"
    assert by_shop["flipkart"] == "https://www.flipkart.com/search?q=Navy+chinos+men"
    assert by_shop["amazon"] == "https://www.amazon.in/s?k=Navy+chinos+men"
    _, odd = search_links(["Black & white", "kurta/pyjama"])
    assert all("&white" not in link.url and " " not in link.url for link in odd)


# A local shop, reached as "shop.test" on a local port, to check fetching end to end.

ROUTES: dict[str, tuple[int, str, str, dict[str, str]]] = {}


class _Shop(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        status, content_type, body, headers = ROUTES.get(
            self.path, (404, "text/plain", "missing", {})
        )
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        for name, value in headers.items():
            self.send_header(name, value)
        data = body.encode()
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def log_message(self, *_: object) -> None:
        pass


@pytest.fixture
def shop(monkeypatch: pytest.MonkeyPatch) -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), _Shop)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    real = pages.public_address

    def resolve(host: str, port_: int) -> str:
        return "127.0.0.1" if host == "shop.test" else real(host, port_)

    monkeypatch.setattr(pages, "public_address", resolve)
    monkeypatch.setattr(pages, "PORTS", (None, 80, 443, port))
    monkeypatch.setattr(pages, "TIMEOUT_SECONDS", 2)
    pages.forget_robots()
    ROUTES.clear()
    yield f"http://shop.test:{port}"
    server.shutdown()
    pages.forget_robots()


def test_a_product_page_is_read(shop: str) -> None:
    ROUTES["/robots.txt"] = (200, "text/plain", "User-agent: *\nDisallow: /account", {})
    ROUTES["/p/1"] = (200, "text/html; charset=utf-8", PRODUCT, {})

    found = WebPageReader().read(f"{shop}/p/1")

    assert found.title == "Men Navy Slim Fit Chinos"
    assert found.url == f"{shop}/p/navy-chinos"


def test_robots_txt_is_obeyed(shop: str) -> None:
    ROUTES["/robots.txt"] = (200, "text/plain", "User-agent: *\nDisallow: /p/", {})
    ROUTES["/p/1"] = (200, "text/html", PRODUCT, {})

    with pytest.raises(PageBlocked):
        WebPageReader().read(f"{shop}/p/1")


def test_rules_for_wearwise_by_name_apply(shop: str) -> None:
    ROUTES["/robots.txt"] = (
        200,
        "text/plain",
        "User-agent: WearWise\nDisallow: /\n\nUser-agent: *\nAllow: /",
        {},
    )

    assert not pages.allowed(f"{shop}/p/1")


def test_no_robots_txt_allows_and_an_unreadable_one_refuses(shop: str) -> None:
    ROUTES["/p/1"] = (200, "text/html", PRODUCT, {})
    assert WebPageReader().read(f"{shop}/p/1").is_product

    pages.forget_robots()
    ROUTES["/robots.txt"] = (503, "text/plain", "down", {})
    with pytest.raises(PageBlocked):
        WebPageReader().read(f"{shop}/p/1")


def test_a_redirect_into_a_private_network_is_refused(shop: str) -> None:
    ROUTES["/p/1"] = (302, "text/html", "", {"Location": "http://169.254.169.254/latest/"})

    with pytest.raises(PageUnavailable) as error:
        pages.fetch(f"{shop}/p/1", "text/html")
    assert error.value.reason == "not_public"


def test_too_large_or_not_a_page_is_unavailable(shop: str) -> None:
    ROUTES["/big"] = (200, "text/html", "x" * (pages.MAX_PAGE_BYTES + 10), {})
    ROUTES["/photo"] = (200, "image/jpeg", "jpeg", {})

    with pytest.raises(PageUnavailable) as big:
        pages.fetch(f"{shop}/big", "text/html")
    with pytest.raises(PageUnavailable) as photo:
        WebPageReader().read(f"{shop}/photo")

    assert big.value.reason == "too_large"
    assert photo.value.reason == "not_a_page"


def test_a_refused_page_is_unavailable_without_a_retry(shop: str) -> None:
    ROUTES["/p/1"] = (403, "text/html", "Access denied", {})

    with pytest.raises(PageUnavailable) as error:
        pages.fetch(f"{shop}/p/1", "text/html")
    assert (error.value.reason, error.value.status) == ("refused", 403)
