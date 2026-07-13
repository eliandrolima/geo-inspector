from __future__ import annotations

import httpx

from app.config import Settings, get_settings
from app.exceptions import FetchError, URLValidationError
from app.state import AuditState
from app.tools.page_extractor import extract_page_data
from app.tools.safe_http import Resolver, fetch_webpage
from app.tools.site_files import inspect_site_files


async def fetch_page_node(
    state: AuditState,
    *,
    settings: Settings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    resolver: Resolver | None = None,
) -> AuditState:
    settings = settings or get_settings()
    try:
        result = await fetch_webpage(
            state["normalized_url"],
            settings=settings,
            transport=transport,
            resolver=resolver,
        )
    except URLValidationError as exc:
        return {
            "status": "invalid_url",
            "error_type": "invalid_url",
            "error_message": str(exc),
            "validation_errors": [*state.get("validation_errors", []), str(exc)],
        }
    except FetchError as exc:
        return {
            "status": "fetch_failed",
            "error_type": "fetch_failed",
            "error_message": str(exc),
            "validation_errors": [*state.get("validation_errors", []), str(exc)],
        }

    return {
        "status": "fetched",
        "status_code": result.status_code,
        "final_url": result.final_url,
        "content_type": result.content_type,
        "redirects": result.redirects,
        "raw_html": result.text,
    }


async def inspect_site_files_node(
    state: AuditState,
    *,
    settings: Settings | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    resolver: Resolver | None = None,
) -> AuditState:
    settings = settings or get_settings()
    robots_data, sitemap_data = await inspect_site_files(
        state["final_url"],
        settings=settings,
        transport=transport,
        resolver=resolver,
    )
    return {
        "status": "site_files_inspected",
        "robots_data": robots_data,
        "sitemap_data": sitemap_data,
    }


def extract_content_node(state: AuditState) -> AuditState:
    extraction = extract_page_data(state.get("raw_html", ""), state["final_url"])
    return {
        "status": "content_extracted",
        "extracted_text": extraction.extracted_text,
        "metadata": extraction.metadata,
        "structured_data": extraction.structured_data,
        "warnings": [*state.get("warnings", []), *extraction.warnings],
    }
