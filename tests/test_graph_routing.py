from __future__ import annotations

from uuid import uuid4

import httpx
import pytest

from app.api.routes import _http_status_from_state
from app.config import Settings
from app.graph import build_audit_graph
from app.services.llm_factory import FakeLLMProvider


pytestmark = pytest.mark.asyncio


def semantic_response() -> dict:
    specs = [
        ("clarity_answerability", "Assunto principal claro"),
        ("clarity_answerability", "Respostas diretas"),
        ("clarity_answerability", "Definições e organização"),
        ("clarity_answerability", "Utilidade do conteúdo"),
        ("clarity_answerability", "Especificidade"),
        ("authority_trust", "Autoridade percebida"),
        ("authority_trust", "Transparência editorial"),
        ("evidence_citability", "Evidências e fontes"),
        ("evidence_citability", "Citabilidade dos parágrafos"),
        ("evidence_citability", "Links e referências"),
        ("evidence_citability", "Dados estruturados citáveis"),
    ]
    return {
        "summary": "Conteúdo claro, com autoria e evidências suficientes para o MVP.",
        "findings": [
            {
                "category": category,
                "criterion": criterion,
                "status": "passed",
                "evidence": {
                    "source": "Conteúdo extraído",
                    "observed": f"Evidência observável para {criterion}.",
                },
                "impact": "Contribui para compreensão da página.",
                "recommendation": "Manter a estrutura e revisar periodicamente.",
                "priority": "low",
                "confidence": 0.8,
            }
            for category, criterion in specs
        ],
    }


def graph_transport(html: str, *, page_status: int = 200) -> httpx.MockTransport:
    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/robots.txt":
            return httpx.Response(
                200,
                headers={"content-type": "text/plain"},
                text="User-agent: *\nAllow: /\nSitemap: https://example.com/sitemap.xml\n",
            )
        if request.url.path == "/sitemap.xml":
            return httpx.Response(
                200,
                headers={"content-type": "application/xml"},
                text="<urlset></urlset>",
            )
        return httpx.Response(
            page_status,
            headers={"content-type": "text/html"},
            text=html,
        )

    return httpx.MockTransport(handler)


async def run_graph(url: str, graph):
    execution_id = str(uuid4())
    return await graph.ainvoke(
        {"url": url, "execution_id": execution_id},
        config={"configurable": {"thread_id": execution_id}},
    )


async def test_invalid_url_routes_to_error_report(tmp_path, resolver):
    graph = build_audit_graph(
        settings=Settings(output_directory=tmp_path),
        llm_provider=FakeLLMProvider([semantic_response()]),
        resolver=resolver,
    )
    state = await run_graph("file:///etc/passwd", graph)
    assert state["error_type"] == "invalid_url"
    assert state["report"]["status"] == "error"
    assert state["report_json_path"].endswith(".json")


async def test_fetch_failure_routes_to_error_report(tmp_path, resolver, fixture_html):
    graph = build_audit_graph(
        settings=Settings(output_directory=tmp_path),
        llm_provider=FakeLLMProvider([semantic_response()]),
        transport=graph_transport(fixture_html("article_complete.html"), page_status=500),
        resolver=resolver,
    )
    state = await run_graph("https://example.com/article", graph)
    assert state["error_type"] == "fetch_failed"
    assert state["report"]["status"] == "error"


async def test_success_flow_saves_report(tmp_path, resolver, fixture_html):
    graph = build_audit_graph(
        settings=Settings(output_directory=tmp_path),
        llm_provider=FakeLLMProvider([semantic_response()]),
        transport=graph_transport(fixture_html("article_complete.html")),
        resolver=resolver,
    )
    state = await run_graph("https://example.com/article", graph)
    assert state["report"]["status"] == "completed"
    assert state["geo_score"] > 70
    assert state["retry_count"] == 0


async def test_reviewer_retries_once_then_succeeds(tmp_path, resolver, fixture_html):
    fake = FakeLLMProvider([
        {"summary": "inválido", "findings": []},
        semantic_response(),
    ])
    graph = build_audit_graph(
        settings=Settings(output_directory=tmp_path),
        llm_provider=fake,
        transport=graph_transport(fixture_html("article_complete.html")),
        resolver=resolver,
    )
    state = await run_graph("https://example.com/article", graph)
    assert fake.calls == 2
    assert state["retry_count"] == 1
    assert state["report"]["status"] == "completed"


async def test_reviewer_retry_limit_generates_error(tmp_path, resolver, fixture_html):
    fake = FakeLLMProvider([
        {"summary": "inválido", "findings": []},
        {"summary": "inválido", "findings": []},
    ])
    graph = build_audit_graph(
        settings=Settings(output_directory=tmp_path),
        llm_provider=fake,
        transport=graph_transport(fixture_html("article_complete.html")),
        resolver=resolver,
    )
    state = await run_graph("https://example.com/article", graph)
    assert fake.calls == 2
    assert state["retry_count"] == 1
    assert state["report"]["status"] == "error"
    assert state["error_type"] == "review_failed"
    assert _http_status_from_state(state) == 200
    assert (
        state["validation_errors"].count(
            "Quantidade mínima de achados semânticos aplicáveis não atingida."
        )
        == 1
    )
