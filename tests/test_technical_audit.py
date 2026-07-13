from __future__ import annotations

from app.nodes.technical_audit import run_technical_audit_node
from app.tools.page_extractor import extract_page_data


def test_technical_audit_generates_evidence_based_findings(fixture_html):
    extraction = extract_page_data(
        fixture_html("article_complete.html"), "https://example.com/article"
    )
    state = {
        "status_code": 200,
        "content_type": "text/html",
        "redirects": [],
        "metadata": extraction.metadata,
        "robots_data": {"found": True, "allowed": True},
        "sitemap_data": {"found": True},
    }
    result = run_technical_audit_node(state)
    findings = {item["criterion"]: item for item in result["technical_findings"]}
    assert findings["Status HTTP acessível"]["status"] == "passed"
    assert findings["H1 único"]["status"] == "passed"
    assert findings["Imagens com texto alternativo"]["status"] == "warning"
    assert findings["Autoria detectável"]["evidence"]["observed"].startswith("Autor detectado")
