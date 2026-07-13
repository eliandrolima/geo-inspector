from __future__ import annotations

from app.schemas.findings import Finding
from app.services.scoring import calculate_geo_score
from app.state import AuditState


def calculate_score_node(state: AuditState) -> AuditState:
    findings = [Finding.model_validate(item) for item in state.get("reviewed_findings", [])]
    breakdown, total, classification = calculate_geo_score(findings)
    return {
        "status": "score_calculated",
        "score_breakdown": breakdown,
        "geo_score": total,
        "classification": classification,
    }
