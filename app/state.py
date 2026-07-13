from typing import Any, TypedDict


class AuditState(TypedDict, total=False):
    url: str
    normalized_url: str
    execution_id: str

    status: str
    error_type: str
    error_message: str
    status_code: int
    final_url: str
    content_type: str
    redirects: list[str]

    raw_html: str
    extracted_text: str
    metadata: dict[str, Any]
    robots_data: dict[str, Any]
    sitemap_data: dict[str, Any]
    structured_data: list[dict[str, Any]]

    page_type: str
    audit_plan: list[str]

    technical_findings: list[dict[str, Any]]
    semantic_findings: list[dict[str, Any]]
    reviewed_findings: list[dict[str, Any]]
    semantic_summary: str

    score_breakdown: dict[str, float]
    geo_score: float
    classification: str

    validation_errors: list[str]
    warnings: list[str]

    retry_count: int
    review_status: str
    report: dict[str, Any]
    report_json_path: str
    report_markdown_path: str
