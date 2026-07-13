from datetime import datetime
from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.findings import Finding


class ReportStatus(StrEnum):
    COMPLETED = "completed"
    ERROR = "error"


class AuditReport(BaseModel):
    execution_id: str
    url: str
    analyzed_at: datetime
    status: ReportStatus
    geo_score: float = Field(ge=0, le=100)
    classification: str
    summary: str
    strengths: list[str] = Field(default_factory=list)
    critical_findings: list[Finding] = Field(default_factory=list)
    quick_wins: list[str] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    limitations: list[str] = Field(default_factory=list)
    disclaimer: str

    model_config = ConfigDict(use_enum_values=True)
