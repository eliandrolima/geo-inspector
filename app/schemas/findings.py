from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field, field_validator


class FindingStatus(StrEnum):
    PASSED = "passed"
    WARNING = "warning"
    FAILED = "failed"
    NOT_APPLICABLE = "not_applicable"
    NOT_VERIFIED = "not_verified"


class FindingPriority(StrEnum):
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FindingCategory(StrEnum):
    CRAWLABILITY = "crawlability_access"
    TECHNICAL = "technical_structure"
    CLARITY = "clarity_answerability"
    AUTHORITY = "authority_trust"
    EVIDENCE = "evidence_citability"


CATEGORY_LABELS: dict[str, str] = {
    FindingCategory.CRAWLABILITY.value: "Rastreabilidade e acesso",
    FindingCategory.TECHNICAL.value: "Estrutura técnica e semântica",
    FindingCategory.CLARITY.value: "Clareza e capacidade de resposta",
    FindingCategory.AUTHORITY.value: "Autoridade e confiabilidade",
    FindingCategory.EVIDENCE.value: "Evidências, fontes e citabilidade",
}


class Evidence(BaseModel):
    source: str = Field(min_length=1, max_length=120)
    observed: str = Field(min_length=1, max_length=1_500)


class Finding(BaseModel):
    category: FindingCategory
    criterion: str = Field(min_length=1, max_length=160)
    status: FindingStatus
    evidence: Evidence
    impact: str = Field(min_length=1, max_length=1_000)
    recommendation: str = Field(min_length=1, max_length=1_000)
    priority: FindingPriority
    confidence: float = Field(ge=0, le=1)

    model_config = ConfigDict(use_enum_values=True)

    @field_validator("criterion", "impact", "recommendation")
    @classmethod
    def strip_text(cls, value: str) -> str:
        return value.strip()
