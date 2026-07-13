from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import Any
from urllib.parse import urljoin, urlsplit

from bs4 import BeautifulSoup


@dataclass
class PageExtraction:
    extracted_text: str
    metadata: dict[str, Any]
    structured_data: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def extract_page_data(html: str, base_url: str) -> PageExtraction:
    soup = BeautifulSoup(html or "", "html.parser")
    warnings: list[str] = []

    for selector in ("script:not([type='application/ld+json'])", "style", "noscript"):
        for tag in soup.select(selector):
            tag.decompose()
    for tag in soup.select("[hidden], [aria-hidden='true']"):
        tag.decompose()
    for tag in soup.find_all(style=True):
        style = str(tag.get("style", "")).lower().replace(" ", "")
        if "display:none" in style or "visibility:hidden" in style:
            tag.decompose()

    structured_data = _extract_json_ld(soup, warnings)
    headings = [
        {"level": int(tag.name[1]), "text": _clean_text(tag.get_text(" ", strip=True))}
        for tag in soup.find_all(re.compile("^h[1-6]$"))
    ]
    links = _extract_links(soup, base_url)
    images = _extract_images(soup, base_url)
    open_graph = _extract_meta_prefix(soup, "og:")
    semantic_tags = {
        name: len(soup.find_all(name))
        for name in ("article", "main", "section", "aside", "header", "footer", "nav")
    }

    main_node = soup.find("article") or soup.find("main") or soup.body or soup
    extracted_text = _clean_multiline_text(main_node.get_text("\n", strip=True))
    words = re.findall(r"\b\w+\b", extracted_text, flags=re.UNICODE)

    metadata: dict[str, Any] = {
        "title": _title(soup),
        "description": _meta_content(soup, "description"),
        "canonical": _canonical(soup, base_url),
        "meta_robots": _meta_content(soup, "robots"),
        "language": _language(soup),
        "headings": headings,
        "h1_count": sum(1 for heading in headings if heading["level"] == 1),
        "author": _author(soup),
        "published_time": _first_present(
            _meta_property(soup, "article:published_time"),
            _meta_content(soup, "date"),
            _time_datetime(soup),
        ),
        "modified_time": _first_present(
            _meta_property(soup, "article:modified_time"),
            _meta_content(soup, "last-modified"),
        ),
        "links": links,
        "images": images,
        "images_without_alt": [image for image in images if not image["alt"]],
        "open_graph": open_graph,
        "json_ld_count": len(structured_data),
        "schema_types": sorted(_schema_types(structured_data)),
        "semantic_tags": semantic_tags,
        "content_length_chars": len(extracted_text),
        "word_count": len(words),
        "content_source": getattr(main_node, "name", "document"),
    }

    return PageExtraction(
        extracted_text=extracted_text,
        metadata=metadata,
        structured_data=structured_data,
        warnings=warnings,
    )


def _title(soup: BeautifulSoup) -> str | None:
    if soup.title and soup.title.string:
        return _clean_text(soup.title.string)
    return None


def _meta_content(soup: BeautifulSoup, name: str) -> str | None:
    tag = soup.find("meta", attrs={"name": re.compile(f"^{re.escape(name)}$", re.I)})
    return _clean_text(tag.get("content")) if tag and tag.get("content") else None


def _meta_property(soup: BeautifulSoup, property_name: str) -> str | None:
    tag = soup.find(
        "meta", attrs={"property": re.compile(f"^{re.escape(property_name)}$", re.I)}
    )
    return _clean_text(tag.get("content")) if tag and tag.get("content") else None


def _canonical(soup: BeautifulSoup, base_url: str) -> str | None:
    tag = soup.find("link", rel=lambda value: value and "canonical" in value)
    href = tag.get("href") if tag else None
    return urljoin(base_url, href) if href else None


def _language(soup: BeautifulSoup) -> str | None:
    html = soup.find("html")
    return _clean_text(html.get("lang")) if html and html.get("lang") else None


def _author(soup: BeautifulSoup) -> str | None:
    candidates = [
        _meta_content(soup, "author"),
        _meta_property(soup, "article:author"),
    ]
    byline = soup.find(class_=re.compile("author|byline", re.I))
    if byline:
        candidates.append(_clean_text(byline.get_text(" ", strip=True)))
    return _first_present(*candidates)


def _time_datetime(soup: BeautifulSoup) -> str | None:
    tag = soup.find("time", datetime=True)
    return _clean_text(tag.get("datetime")) if tag else None


def _extract_links(soup: BeautifulSoup, base_url: str) -> dict[str, Any]:
    base_host = urlsplit(base_url).hostname
    internal: list[str] = []
    external: list[str] = []
    for tag in soup.find_all("a", href=True):
        href = tag.get("href", "").strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute = urljoin(base_url, href)
        host = urlsplit(absolute).hostname
        if host == base_host:
            internal.append(absolute)
        else:
            external.append(absolute)
    return {
        "internal_count": len(set(internal)),
        "external_count": len(set(external)),
        "internal": sorted(set(internal))[:25],
        "external": sorted(set(external))[:25],
    }


def _extract_images(soup: BeautifulSoup, base_url: str) -> list[dict[str, str]]:
    images: list[dict[str, str]] = []
    for image in soup.find_all("img"):
        src = image.get("src", "")
        images.append(
            {
                "src": urljoin(base_url, src) if src else "",
                "alt": _clean_text(image.get("alt", "")),
            }
        )
    return images


def _extract_meta_prefix(soup: BeautifulSoup, prefix: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for tag in soup.find_all("meta", attrs={"property": True}):
        prop = str(tag.get("property", ""))
        if prop.startswith(prefix) and tag.get("content"):
            values[prop] = _clean_text(tag["content"])
    return values


def _extract_json_ld(soup: BeautifulSoup, warnings: list[str]) -> list[dict[str, Any]]:
    data: list[dict[str, Any]] = []
    for tag in soup.find_all("script", attrs={"type": re.compile("ld\\+json", re.I)}):
        raw = tag.string or tag.get_text("", strip=True)
        if not raw:
            continue
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            warnings.append("JSON-LD inválido encontrado e ignorado.")
            continue
        if isinstance(parsed, list):
            data.extend(item for item in parsed if isinstance(item, dict))
        elif isinstance(parsed, dict):
            data.append(parsed)
    return data


def _schema_types(data: list[dict[str, Any]]) -> set[str]:
    found: set[str] = set()

    def visit(value: Any) -> None:
        if isinstance(value, dict):
            schema_type = value.get("@type")
            if isinstance(schema_type, str):
                found.add(schema_type)
            elif isinstance(schema_type, list):
                found.update(str(item) for item in schema_type)
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for item in value:
                visit(item)

    visit(data)
    return found


def _first_present(*values: str | None) -> str | None:
    for value in values:
        if value:
            return value
    return None


def _clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def _clean_multiline_text(value: str) -> str:
    lines = [_clean_text(line) for line in value.splitlines()]
    return "\n".join(line for line in lines if line)
