from __future__ import annotations

from urllib.parse import urlsplit, urlunsplit
from urllib.robotparser import RobotFileParser

import httpx

from app.config import Settings, get_settings
from app.tools.safe_http import Resolver, fetch_text_resource

SITE_FILE_TYPES = (
    "text/plain",
    "text/html",
    "application/xml",
    "text/xml",
    "application/xhtml+xml",
)


async def inspect_site_files(
    normalized_url: str,
    *,
    settings: Settings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    resolver: Resolver | None = None,
    sitemap_limit: int = 5,
) -> tuple[dict, dict]:
    settings = settings or get_settings()
    base_url = _origin(normalized_url)
    robots_url = f"{base_url}/robots.txt"
    fallback_sitemap_url = f"{base_url}/sitemap.xml"

    robots_data = {
        "url": robots_url,
        "found": False,
        "allowed": None,
        "sitemaps": [],
        "error": None,
    }
    sitemap_data = {
        "checked": [],
        "found": False,
        "urls": [],
        "error": None,
    }

    try:
        robots_response = await fetch_text_resource(
            robots_url,
            allowed_content_types=SITE_FILE_TYPES,
            settings=settings,
            transport=transport,
            resolver=resolver,
        )
        robots_text = robots_response.text
        parser = RobotFileParser()
        parser.set_url(robots_url)
        parser.parse(robots_text.splitlines())
        robots_data.update(
            {
                "found": True,
                "status_code": robots_response.status_code,
                "allowed": parser.can_fetch(settings.user_agent, normalized_url),
                "sitemaps": _extract_sitemap_lines(robots_text, sitemap_limit),
            }
        )
    except Exception as exc:  # expected site-file failure must not stop the audit
        robots_data["error"] = _public_error(exc)

    candidate_sitemaps = list(robots_data["sitemaps"][:sitemap_limit])
    if fallback_sitemap_url not in candidate_sitemaps:
        candidate_sitemaps.append(fallback_sitemap_url)

    for sitemap_url in candidate_sitemaps[:sitemap_limit]:
        sitemap_data["checked"].append(sitemap_url)
        try:
            response = await fetch_text_resource(
                sitemap_url,
                allowed_content_types=SITE_FILE_TYPES,
                settings=settings,
                transport=transport,
                resolver=resolver,
            )
            sitemap_data["found"] = True
            sitemap_data["urls"].append(
                {
                    "url": sitemap_url,
                    "status_code": response.status_code,
                    "content_type": response.content_type,
                }
            )
        except Exception as exc:  # sitemap is optional for this MVP
            sitemap_data["error"] = _public_error(exc)

    return robots_data, sitemap_data


def _origin(url: str) -> str:
    parsed = urlsplit(url)
    return urlunsplit((parsed.scheme, parsed.netloc, "", "", ""))


def _extract_sitemap_lines(robots_text: str, limit: int) -> list[str]:
    sitemaps: list[str] = []
    for line in robots_text.splitlines():
        if line.lower().startswith("sitemap:"):
            sitemap_url = line.split(":", 1)[1].strip()
            if sitemap_url and sitemap_url not in sitemaps:
                sitemaps.append(sitemap_url)
        if len(sitemaps) >= limit:
            break
    return sitemaps


def _public_error(exc: Exception) -> str:
    return str(exc) or exc.__class__.__name__
