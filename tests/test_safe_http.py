from __future__ import annotations

import httpx
import pytest

from app.config import Settings
from app.exceptions import (
    FetchError,
    FetchTimeoutError,
    ResponseTooLargeError,
    UnsupportedContentTypeError,
    URLValidationError,
)
from app.tools.safe_http import fetch_webpage


pytestmark = pytest.mark.asyncio


async def test_fetch_valid_html(resolver):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(
            200, headers={"content-type": "text/html"}, text="<html>ok</html>"
        )
    )
    result = await fetch_webpage("https://example.com", transport=transport, resolver=resolver)
    assert result.status_code == 200
    assert result.text == "<html>ok</html>"


async def test_public_redirect_is_followed(resolver):
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/redirect":
            return httpx.Response(302, headers={"location": "https://example.com/final"})
        return httpx.Response(200, headers={"content-type": "text/html"}, text="<html>final</html>")

    result = await fetch_webpage(
        "https://example.com/redirect",
        transport=httpx.MockTransport(handler),
        resolver=resolver,
    )
    assert result.final_url == "https://example.com/final"
    assert result.redirects == ["https://example.com/final"]


async def test_redirect_to_private_ip_is_blocked(resolver):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(302, headers={"location": "http://127.0.0.1/"})
    )
    with pytest.raises(URLValidationError):
        await fetch_webpage("https://example.com", transport=transport, resolver=resolver)


async def test_too_many_redirects(resolver):
    settings = Settings(max_redirects=1)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(302, headers={"location": "https://example.com/again"})
    )
    with pytest.raises(FetchError):
        await fetch_webpage(
            "https://example.com",
            settings=settings,
            transport=transport,
            resolver=resolver,
        )


async def test_timeout_is_reported(resolver):
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    with pytest.raises(FetchTimeoutError):
        await fetch_webpage(
            "https://example.com",
            transport=httpx.MockTransport(handler),
            resolver=resolver,
        )


async def test_response_too_large(resolver):
    settings = Settings(max_response_bytes=5)
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, headers={"content-type": "text/html"}, text="too large")
    )
    with pytest.raises(ResponseTooLargeError):
        await fetch_webpage(
            "https://example.com",
            settings=settings,
            transport=transport,
            resolver=resolver,
        )


async def test_invalid_content_type(resolver):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(200, headers={"content-type": "application/json"}, json={})
    )
    with pytest.raises(UnsupportedContentTypeError):
        await fetch_webpage("https://example.com", transport=transport, resolver=resolver)


async def test_inaccessible_page(resolver):
    transport = httpx.MockTransport(
        lambda request: httpx.Response(500, headers={"content-type": "text/html"}, text="error")
    )
    with pytest.raises(FetchError):
        await fetch_webpage("https://example.com", transport=transport, resolver=resolver)
