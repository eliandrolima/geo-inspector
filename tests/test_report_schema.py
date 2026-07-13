from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

from app.config import Settings
from app.schemas.findings import Finding, FindingCategory, FindingPriority, FindingStatus
from app.schemas.reports import AuditReport, ReportStatus
from app.tools.report_writer import load_report, report_paths, save_report


def test_report_schema_and_storage(tmp_path):
    execution_id = str(uuid4())
    finding = Finding(
        category=FindingCategory.AUTHORITY,
        criterion="Autoria detectável",
        status=FindingStatus.FAILED,
        evidence={"source": "HTML", "observed": "Nenhum autor identificado."},
        impact="Dificulta avaliação editorial.",
        recommendation="Adicionar autor responsável.",
        priority=FindingPriority.HIGH,
        confidence=0.9,
    )
    report = AuditReport(
        execution_id=execution_id,
        url="https://example.com",
        analyzed_at=datetime.now(UTC),
        status=ReportStatus.COMPLETED,
        geo_score=68,
        classification="Prontidão moderada",
        summary="Resumo executivo.",
        strengths=[],
        critical_findings=[finding],
        quick_wins=["Adicionar autor responsável."],
        findings=[finding],
        score_breakdown={"authority_trust": 10},
        limitations=["A pontuação é heurística."],
        disclaimer="A pontuação é heurística e não garante citação.",
    )
    settings = Settings(output_directory=tmp_path)
    json_path, markdown_path = save_report(report, settings=settings)
    assert json_path.exists()
    assert markdown_path.exists()
    loaded = load_report(execution_id, settings=settings)
    assert loaded.execution_id == execution_id
    assert "Adicionar autor" in markdown_path.read_text(encoding="utf-8")


def test_report_path_rejects_traversal(tmp_path):
    settings = Settings(output_directory=tmp_path)
    try:
        report_paths("../secret", settings=settings)
    except Exception as exc:
        assert "Identificador" in str(exc)
    else:
        raise AssertionError("path traversal deveria ser rejeitado")
