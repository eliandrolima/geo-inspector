from __future__ import annotations

from app.tools.page_extractor import extract_page_data


def test_extract_complete_article(fixture_html):
    extraction = extract_page_data(
        fixture_html("article_complete.html"), "https://example.com/article"
    )
    metadata = extraction.metadata
    assert metadata["title"] == "Guia completo de GEO para conteúdo técnico"
    assert metadata["description"].startswith("Aprenda como estruturar")
    assert metadata["canonical"] == "https://example.com/article"
    assert metadata["h1_count"] == 1
    assert metadata["author"] == "Elian Lima"
    assert metadata["published_time"] == "2026-07-01"
    assert metadata["modified_time"] == "2026-07-10"
    assert metadata["images_without_alt"][0]["src"] == "https://example.com/img/table.png"
    assert metadata["links"]["internal_count"] == 2
    assert metadata["links"]["external_count"] == 1
    assert metadata["json_ld_count"] == 1
    assert "Article" in metadata["schema_types"]
    assert "GEO é uma prática" in extraction.extracted_text


def test_extract_incomplete_html_and_invalid_jsonld(fixture_html):
    extraction = extract_page_data(
        fixture_html("article_incomplete.html"), "https://example.com/incomplete"
    )
    assert extraction.metadata["title"] == "Curto"
    assert extraction.metadata["description"] is None
    assert extraction.metadata["h1_count"] == 0
    assert extraction.metadata["json_ld_count"] == 0
    assert extraction.warnings == ["JSON-LD inválido encontrado e ignorado."]
