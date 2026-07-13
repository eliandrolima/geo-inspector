from __future__ import annotations

import httpx
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph

from app.config import Settings, get_settings
from app.nodes.extraction import (
    extract_content_node,
    fetch_page_node,
    inspect_site_files_node,
)
from app.nodes.planning import plan_audit_node
from app.nodes.reporting import (
    generate_error_report_node,
    generate_report_node,
    save_report_node,
)
from app.nodes.review import review_findings_node
from app.nodes.scoring import calculate_score_node
from app.nodes.semantic_audit import run_semantic_audit_node
from app.nodes.technical_audit import run_technical_audit_node
from app.nodes.validation import validate_url_node
from app.services.llm_factory import LLMProvider
from app.state import AuditState
from app.tools.safe_http import Resolver


def build_audit_graph(
    *,
    settings: Settings | None = None,
    llm_provider: LLMProvider | None = None,
    transport: httpx.AsyncBaseTransport | None = None,
    resolver: Resolver | None = None,
):
    settings = settings or get_settings()
    builder = StateGraph(AuditState)

    async def fetch_node(state: AuditState) -> AuditState:
        return await fetch_page_node(
            state, settings=settings, transport=transport, resolver=resolver
        )

    async def inspect_node(state: AuditState) -> AuditState:
        return await inspect_site_files_node(
            state, settings=settings, transport=transport, resolver=resolver
        )

    async def semantic_node(state: AuditState) -> AuditState:
        return await run_semantic_audit_node(
            state, settings=settings, llm_provider=llm_provider
        )

    builder.add_node(
        "validate_url",
        lambda state: validate_url_node(state, resolver=resolver),
    )
    builder.add_node("fetch_page", fetch_node)
    builder.add_node("inspect_site_files", inspect_node)
    builder.add_node("extract_content", extract_content_node)
    builder.add_node("plan_audit", plan_audit_node)
    builder.add_node("run_technical_audit", run_technical_audit_node)
    builder.add_node("run_semantic_audit", semantic_node)
    builder.add_node("review_findings", review_findings_node)
    builder.add_node("calculate_score", calculate_score_node)
    builder.add_node("generate_report", generate_report_node)
    builder.add_node("generate_error_report", generate_error_report_node)
    builder.add_node(
        "save_report",
        lambda state: save_report_node(state, settings=settings),
    )

    builder.add_edge(START, "validate_url")
    builder.add_conditional_edges(
        "validate_url",
        _route_after_validation,
        {"ok": "fetch_page", "error": "generate_error_report"},
    )
    builder.add_conditional_edges(
        "fetch_page",
        _route_after_fetch,
        {"ok": "inspect_site_files", "error": "generate_error_report"},
    )
    builder.add_edge("inspect_site_files", "extract_content")
    builder.add_edge("extract_content", "plan_audit")
    builder.add_edge("plan_audit", "run_technical_audit")
    builder.add_edge("run_technical_audit", "run_semantic_audit")
    builder.add_edge("run_semantic_audit", "review_findings")
    builder.add_conditional_edges(
        "review_findings",
        _route_after_review,
        {
            "retry": "run_semantic_audit",
            "valid": "calculate_score",
            "fatal": "generate_error_report",
        },
    )
    builder.add_edge("calculate_score", "generate_report")
    builder.add_edge("generate_report", "save_report")
    builder.add_edge("generate_error_report", "save_report")
    builder.add_edge("save_report", END)

    return builder.compile(checkpointer=MemorySaver())


def _route_after_validation(state: AuditState) -> str:
    return "error" if state.get("status") == "invalid_url" else "ok"


def _route_after_fetch(state: AuditState) -> str:
    return "error" if state.get("status") in {"invalid_url", "fetch_failed"} else "ok"


def _route_after_review(state: AuditState) -> str:
    return state.get("review_status", "fatal")
