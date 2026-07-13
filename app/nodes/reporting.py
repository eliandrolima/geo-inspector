from __future__ import annotations

from datetime import UTC, datetime

from pydantic import ValidationError

from app.config import Settings, get_settings
from app.exceptions import ReportStorageError
from app.schemas.findings import Finding, FindingPriority, FindingStatus
from app.schemas.reports import AuditReport, ReportStatus
from app.state import AuditState
from app.tools.report_writer import save_report

DISCLAIMER = (
    "A pontuação é heurística e não garante citação, indexação, recomendação "
    "ou posicionamento por mecanismos generativos ou mecanismos de busca."
)

LIMITATIONS = [
    "GEO é uma área em evolução.",
    "Não existe garantia de citação por sistemas generativos.",
    "A pontuação é heurística e criada para este projeto acadêmico.",
    "A análise de uma página não representa todo o domínio.",
    "Mecanismos generativos utilizam critérios próprios.",
    "Páginas dependentes de JavaScript podem ser analisadas parcialmente.",
    "Os resultados semânticos podem variar conforme o modelo configurado.",
    "Ausência detectada não comprova inexistência absoluta.",
    "Originalidade não pode ser comprovada sem comparação externa.",
]


def generate_report_node(state: AuditState) -> AuditState:
    findings = [Finding.model_validate(item) for item in state.get("reviewed_findings", [])]
    report = AuditReport(
        execution_id=state["execution_id"],
        url=state.get("final_url") or state.get("normalized_url") or state.get("url", ""),
        analyzed_at=datetime.now(UTC),
        status=ReportStatus.COMPLETED,
        geo_score=state.get("geo_score", 0.0),
        classification=state.get("classification", "Não avaliado"),
        summary=_summary(state),
        strengths=_strengths(findings),
        critical_findings=_critical_findings(findings),
        quick_wins=_quick_wins(findings),
        findings=findings,
        score_breakdown=state.get("score_breakdown", {}),
        limitations=LIMITATIONS,
        disclaimer=DISCLAIMER,
    )
    return {"status": "report_generated", "report": report.model_dump(mode="json")}


def generate_error_report_node(state: AuditState) -> AuditState:
    raw_findings = [
        *state.get("technical_findings", []),
        *state.get("semantic_findings", []),
    ]
    findings: list[Finding] = []
    for raw in raw_findings:
        try:
            findings.append(Finding.model_validate(raw))
        except ValidationError:
            continue
    errors = state.get("validation_errors", [])
    message = state.get("error_message") or "A auditoria não pôde ser concluída."
    if errors:
        message = f"{message} Detalhes: {'; '.join(errors[:3])}."
    report = AuditReport(
        execution_id=state["execution_id"],
        url=state.get("normalized_url") or state.get("url", ""),
        analyzed_at=datetime.now(UTC),
        status=ReportStatus.ERROR,
        geo_score=0,
        classification="Não avaliado",
        summary=message,
        strengths=[],
        critical_findings=_critical_findings(findings),
        quick_wins=[],
        findings=findings,
        score_breakdown=state.get("score_breakdown", {}),
        limitations=LIMITATIONS,
        disclaimer=DISCLAIMER,
    )
    return {"status": "error_report_generated", "report": report.model_dump(mode="json")}


def save_report_node(
    state: AuditState,
    *,
    settings: Settings | None = None,
) -> AuditState:
    settings = settings or get_settings()
    try:
        report = AuditReport.model_validate(state["report"])
        json_path, markdown_path = save_report(report, settings=settings)
    except ReportStorageError as exc:
        return {
            "status": "report_save_failed",
            "error_type": "report_storage",
            "error_message": str(exc),
            "validation_errors": [*state.get("validation_errors", []), str(exc)],
        }
    return {
        "status": "report_saved",
        "report_json_path": str(json_path),
        "report_markdown_path": str(markdown_path),
    }


def _summary(state: AuditState) -> str:
    semantic = state.get("semantic_summary")
    score = state.get("geo_score", 0)
    classification = state.get("classification", "Não avaliado")
    if semantic:
        return (
            f"A página recebeu {score:.1f}/100 ({classification}). "
            f"Resumo semântico: {semantic}"
        )
    return f"A página recebeu {score:.1f}/100 ({classification}) na auditoria GEO heurística."


def _strengths(findings: list[Finding]) -> list[str]:
    return [
        f"{finding.criterion}: {finding.evidence.observed}"
        for finding in findings
        if str(finding.status) == FindingStatus.PASSED.value
    ][:6]


def _critical_findings(findings: list[Finding]) -> list[Finding]:
    return [
        finding
        for finding in findings
        if str(finding.status) == FindingStatus.FAILED.value
        and str(finding.priority)
        in {FindingPriority.CRITICAL.value, FindingPriority.HIGH.value}
    ][:8]


def _quick_wins(findings: list[Finding]) -> list[str]:
    return [
        finding.recommendation
        for finding in findings
        if str(finding.status) in {FindingStatus.WARNING.value, FindingStatus.FAILED.value}
        and str(finding.priority) in {FindingPriority.LOW.value, FindingPriority.MEDIUM.value}
    ][:6]
