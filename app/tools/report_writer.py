from __future__ import annotations

import json
from pathlib import Path
from uuid import UUID

from pydantic import ValidationError

from app.config import Settings, get_settings
from app.exceptions import ReportStorageError
from app.schemas.findings import CATEGORY_LABELS
from app.schemas.reports import AuditReport


def save_report(
    report: AuditReport,
    *,
    settings: Settings | None = None,
) -> tuple[Path, Path]:
    settings = settings or get_settings()
    output_dir = settings.output_directory
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path, markdown_path = report_paths(report.execution_id, settings=settings)
    try:
        json_path.write_text(
            report.model_dump_json(indent=2),
            encoding="utf-8",
        )
        markdown_path.write_text(report_to_markdown(report), encoding="utf-8")
    except OSError as exc:
        raise ReportStorageError("Não foi possível salvar o relatório.") from exc
    return json_path, markdown_path


def load_report(execution_id: str, *, settings: Settings | None = None) -> AuditReport:
    settings = settings or get_settings()
    json_path, _ = report_paths(execution_id, settings=settings)
    if not json_path.exists():
        raise ReportStorageError("Relatório não encontrado.")
    try:
        return AuditReport.model_validate_json(json_path.read_text(encoding="utf-8"))
    except (OSError, ValidationError, json.JSONDecodeError) as exc:
        raise ReportStorageError("Relatório inválido ou indisponível.") from exc


def report_paths(
    execution_id: str,
    *,
    settings: Settings | None = None,
) -> tuple[Path, Path]:
    settings = settings or get_settings()
    try:
        safe_id = str(UUID(execution_id))
    except ValueError as exc:
        raise ReportStorageError("Identificador de relatório inválido.") from exc
    output_dir = settings.output_directory
    return output_dir / f"{safe_id}.json", output_dir / f"{safe_id}.md"


def report_to_markdown(report: AuditReport) -> str:
    lines = [
        f"# GEO Inspector - Relatório {report.execution_id}",
        "",
        f"- URL analisada: {report.url}",
        f"- Data da análise: {report.analyzed_at.isoformat()}",
        f"- Status: {report.status}",
        f"- Pontuação GEO: {report.geo_score:.1f}/100",
        f"- Classificação: {report.classification}",
        "",
        "## Resumo executivo",
        "",
        report.summary,
        "",
        "## Pontos fortes",
        "",
    ]
    lines.extend(_bullets(report.strengths))
    lines.extend(["", "## Achados críticos", ""])
    if report.critical_findings:
        for finding in report.critical_findings:
            lines.extend(_finding_block(finding))
    else:
        lines.append("- Nenhum achado crítico registrado.")

    lines.extend(["", "## Ações rápidas", ""])
    lines.extend(_bullets(report.quick_wins))

    lines.extend(["", "## Pontuação por categoria", ""])
    for category, score in report.score_breakdown.items():
        label = CATEGORY_LABELS.get(category, category)
        lines.append(f"- {label}: {score:.1f}")

    lines.extend(["", "## Achados", ""])
    for finding in report.findings:
        lines.extend(_finding_block(finding))

    lines.extend(["", "## Limitações", ""])
    lines.extend(_bullets(report.limitations))
    lines.extend(["", "## Aviso", "", report.disclaimer, ""])
    return "\n".join(lines)


def _bullets(items: list[str]) -> list[str]:
    return [f"- {item}" for item in items] if items else ["- Nenhum item registrado."]


def _finding_block(finding) -> list[str]:
    label = CATEGORY_LABELS.get(str(finding.category), str(finding.category))
    return [
        f"### {finding.criterion}",
        "",
        f"- Categoria: {label}",
        f"- Status: {finding.status}",
        f"- Prioridade: {finding.priority}",
        f"- Evidência: {finding.evidence.observed}",
        f"- Impacto: {finding.impact}",
        f"- Recomendação: {finding.recommendation}",
        f"- Confiança: {finding.confidence:.2f}",
        "",
    ]
