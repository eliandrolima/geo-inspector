from pydantic import BaseModel, Field

from app.schemas.findings import Finding
from app.schemas.reports import AuditReport


class AuditRequest(BaseModel):
    url: str = Field(min_length=1, max_length=2_048)


class ErrorResponse(BaseModel):
    error: str
    report: AuditReport | None = None


class SemanticAuditResult(BaseModel):
    summary: str = Field(min_length=1, max_length=1_500)
    findings: list[Finding] = Field(min_length=1)
