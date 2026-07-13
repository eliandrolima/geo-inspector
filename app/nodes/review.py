from __future__ import annotations

from pydantic import ValidationError

from app.schemas.findings import Finding, FindingCategory, FindingStatus
from app.state import AuditState

SEMANTIC_CATEGORIES = {
    FindingCategory.CLARITY.value,
    FindingCategory.AUTHORITY.value,
    FindingCategory.EVIDENCE.value,
}
MIN_APPLICABLE_SEMANTIC_FINDINGS = 5


def review_findings_node(state: AuditState) -> AuditState:
    if state.get("error_type") == "llm_configuration":
        return {
            "review_status": "fatal",
            "status": "review_failed",
            "validation_errors": state.get("validation_errors", []),
        }

    errors: list[str] = []
    technical = _validate_findings(state.get("technical_findings", []), errors, "técnico")
    semantic = _validate_findings(state.get("semantic_findings", []), errors, "semântico")

    for finding in semantic:
        if str(finding.category) not in SEMANTIC_CATEGORIES:
            errors.append(
                f"Achado semântico em categoria não permitida: {finding.category}."
            )

    applicable_semantic = [
        finding
        for finding in semantic
        if str(finding.status) != FindingStatus.NOT_APPLICABLE.value
    ]
    if len(applicable_semantic) < MIN_APPLICABLE_SEMANTIC_FINDINGS:
        errors.append("Quantidade mínima de achados semânticos aplicáveis não atingida.")

    _check_duplicates([*technical, *semantic], errors)

    if errors:
        retry_count = int(state.get("retry_count") or 0)
        merged_errors = [*state.get("validation_errors", []), *errors]
        if retry_count < 1:
            return {
                "status": "review_retry_requested",
                "review_status": "retry",
                "retry_count": retry_count + 1,
                "validation_errors": merged_errors,
            }
        return {
            "status": "review_failed",
            "review_status": "fatal",
            "validation_errors": merged_errors,
            "error_type": "review_failed",
            "error_message": "Os achados semânticos não puderam ser validados após nova tentativa.",
        }

    return {
        "status": "findings_reviewed",
        "review_status": "valid",
        "reviewed_findings": [
            finding.model_dump(mode="json") for finding in [*technical, *semantic]
        ],
    }


def _validate_findings(raw: list[dict], errors: list[str], label: str) -> list[Finding]:
    findings: list[Finding] = []
    for index, item in enumerate(raw):
        try:
            finding = Finding.model_validate(item)
        except ValidationError as exc:
            errors.append(f"Achado {label} #{index + 1} inválido: {exc}.")
            continue
        if not finding.evidence.observed.strip():
            errors.append(f"Achado {label} #{index + 1} não possui evidência observável.")
        if not finding.recommendation.strip():
            errors.append(f"Achado {label} #{index + 1} não possui recomendação.")
        findings.append(finding)
    return findings


def _check_duplicates(findings: list[Finding], errors: list[str]) -> None:
    seen: set[tuple[str, str]] = set()
    for finding in findings:
        key = (str(finding.category), finding.criterion.lower().strip())
        if key in seen:
            errors.append(f"Achado duplicado detectado: {finding.criterion}.")
        seen.add(key)
