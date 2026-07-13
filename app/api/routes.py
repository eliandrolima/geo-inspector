from __future__ import annotations

import logging
from typing import Literal
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import FileResponse, JSONResponse

from app.schemas.audit import AuditRequest
from app.schemas.reports import AuditReport
from app.tools.report_writer import load_report, report_paths

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/api/v1/audits", response_model=AuditReport)
async def create_audit(payload: AuditRequest, request: Request):
    execution_id = str(uuid4())
    graph = request.app.state.audit_graph
    try:
        state = await graph.ainvoke(
            {"url": payload.url, "execution_id": execution_id},
            config={"configurable": {"thread_id": execution_id}},
        )
        report = AuditReport.model_validate(state["report"])
    except Exception as exc:
        logger.error("audit_failed execution_id=%s error=%s", execution_id, exc.__class__.__name__)
        raise HTTPException(status_code=500, detail="Falha interna ao executar auditoria.") from exc

    status_code = _http_status_from_state(state)
    if status_code != 200:
        return JSONResponse(
            status_code=status_code,
            content={
                "error": report.summary,
                "report": report.model_dump(mode="json"),
            },
        )
    return report


@router.get("/api/v1/reports/{execution_id}", response_model=AuditReport)
async def get_report(execution_id: str, request: Request) -> AuditReport:
    try:
        return load_report(execution_id, settings=request.app.state.settings)
    except Exception as exc:
        logger.warning("report_load_failed execution_id=%s error=%s", execution_id, exc.__class__.__name__)
        raise HTTPException(status_code=404, detail="Relatório não encontrado.") from exc


@router.get("/api/v1/reports/{execution_id}/download")
async def download_report(
    execution_id: str,
    request: Request,
    format: Literal["json", "markdown"] = Query(default="json"),
):
    try:
        json_path, markdown_path = report_paths(execution_id, settings=request.app.state.settings)
    except Exception as exc:
        raise HTTPException(status_code=400, detail="Identificador inválido.") from exc

    if format == "json":
        if not json_path.exists():
            raise HTTPException(status_code=404, detail="Relatório não encontrado.")
        return FileResponse(
            json_path,
            media_type="application/json",
            filename=f"{execution_id}.json",
        )

    if not markdown_path.exists():
        raise HTTPException(status_code=404, detail="Relatório não encontrado.")
    return FileResponse(
        markdown_path,
        media_type="text/markdown; charset=utf-8",
        filename=f"{execution_id}.md",
    )


def _http_status_from_state(state: dict) -> int:
    report = state.get("report", {})
    if report.get("status") == "completed":
        return 200
    error_type = state.get("error_type")
    if error_type == "invalid_url":
        return 400
    if error_type == "fetch_failed":
        return 502
    return 500
