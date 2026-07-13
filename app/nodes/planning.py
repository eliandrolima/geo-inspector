from __future__ import annotations

from app.state import AuditState

ALLOWED_ANALYSIS_MODULES = {
    "technical_access",
    "technical_structure",
    "semantic_clarity",
    "semantic_authority",
    "semantic_evidence",
    "reporting",
}


def plan_audit_node(state: AuditState) -> AuditState:
    metadata = state.get("metadata", {})
    schema_types = {str(item).lower() for item in metadata.get("schema_types", [])}
    word_count = int(metadata.get("word_count") or 0)
    source = str(metadata.get("content_source") or "")
    title = str(metadata.get("title") or "").lower()
    final_url = state.get("final_url", "").lower()

    if word_count < 120:
        page_type = "página com conteúdo insuficiente"
    elif "product" in schema_types:
        page_type = "página de produto"
    elif {"techarticle", "apireference", "softwareapplication"} & schema_types or "/docs" in final_url:
        page_type = "documentação técnica"
    elif "article" in schema_types or source == "article":
        page_type = "artigo"
    elif any(token in final_url or token in title for token in ("about", "sobre", "contato")):
        page_type = "página institucional"
    elif any(token in final_url or token in title for token in ("landing", "lp", "oferta")):
        page_type = "landing page"
    else:
        page_type = "tipo não identificado"

    audit_plan = [
        "technical_access",
        "technical_structure",
        "semantic_clarity",
        "semantic_authority",
        "semantic_evidence",
        "reporting",
    ]
    return {
        "status": "audit_planned",
        "page_type": page_type,
        "audit_plan": [module for module in audit_plan if module in ALLOWED_ANALYSIS_MODULES],
    }
