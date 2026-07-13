from __future__ import annotations

from dataclasses import dataclass

from app.schemas.findings import Finding, FindingCategory, FindingStatus


@dataclass(frozen=True)
class ScoringCriterion:
    category: str
    criterion: str
    max_points: float


SCORING_CRITERIA: tuple[ScoringCriterion, ...] = (
    ScoringCriterion(FindingCategory.CRAWLABILITY.value, "Status HTTP acessível", 5),
    ScoringCriterion(FindingCategory.CRAWLABILITY.value, "Redirecionamentos controlados", 4),
    ScoringCriterion(FindingCategory.CRAWLABILITY.value, "Tipo de conteúdo HTML", 3),
    ScoringCriterion(FindingCategory.CRAWLABILITY.value, "Robots.txt permite acesso", 5),
    ScoringCriterion(FindingCategory.CRAWLABILITY.value, "Sitemap localizado", 3),
    ScoringCriterion(FindingCategory.TECHNICAL.value, "Title descritivo", 2),
    ScoringCriterion(FindingCategory.TECHNICAL.value, "Meta description", 2),
    ScoringCriterion(FindingCategory.TECHNICAL.value, "Canonical", 2),
    ScoringCriterion(FindingCategory.TECHNICAL.value, "Meta robots noindex", 2),
    ScoringCriterion(FindingCategory.TECHNICAL.value, "H1 único", 2),
    ScoringCriterion(FindingCategory.TECHNICAL.value, "Hierarquia de headings", 2),
    ScoringCriterion(FindingCategory.TECHNICAL.value, "Idioma declarado", 1),
    ScoringCriterion(FindingCategory.TECHNICAL.value, "Dados estruturados JSON-LD", 1),
    ScoringCriterion(FindingCategory.TECHNICAL.value, "Elementos semânticos", 1),
    ScoringCriterion(FindingCategory.CLARITY.value, "Assunto principal claro", 5),
    ScoringCriterion(FindingCategory.CLARITY.value, "Respostas diretas", 5),
    ScoringCriterion(FindingCategory.CLARITY.value, "Definições e organização", 5),
    ScoringCriterion(FindingCategory.CLARITY.value, "Utilidade do conteúdo", 5),
    ScoringCriterion(FindingCategory.CLARITY.value, "Especificidade", 5),
    ScoringCriterion(FindingCategory.AUTHORITY.value, "Autoria detectável", 4),
    ScoringCriterion(FindingCategory.AUTHORITY.value, "Datas editoriais", 4),
    ScoringCriterion(FindingCategory.AUTHORITY.value, "Autoridade percebida", 6),
    ScoringCriterion(FindingCategory.AUTHORITY.value, "Transparência editorial", 6),
    ScoringCriterion(FindingCategory.EVIDENCE.value, "Evidências e fontes", 8),
    ScoringCriterion(FindingCategory.EVIDENCE.value, "Citabilidade dos parágrafos", 6),
    ScoringCriterion(FindingCategory.EVIDENCE.value, "Links e referências", 3),
    ScoringCriterion(FindingCategory.EVIDENCE.value, "Dados estruturados citáveis", 3),
)

STATUS_MULTIPLIER = {
    FindingStatus.PASSED.value: 1.0,
    FindingStatus.WARNING.value: 0.5,
    FindingStatus.FAILED.value: 0.0,
    FindingStatus.NOT_VERIFIED.value: 0.0,
}
CATEGORY_MAX = {
    FindingCategory.CRAWLABILITY.value: 20.0,
    FindingCategory.TECHNICAL.value: 15.0,
    FindingCategory.CLARITY.value: 25.0,
    FindingCategory.AUTHORITY.value: 20.0,
    FindingCategory.EVIDENCE.value: 20.0,
}


def calculate_geo_score(findings: list[Finding]) -> tuple[dict[str, float], float, str]:
    indexed = {(str(item.category), item.criterion): item for item in findings}
    raw_by_category = {category: 0.0 for category in CATEGORY_MAX}
    possible_by_category = {category: 0.0 for category in CATEGORY_MAX}

    for criterion in SCORING_CRITERIA:
        finding = indexed.get((criterion.category, criterion.criterion))
        if finding and str(finding.status) == FindingStatus.NOT_APPLICABLE.value:
            continue
        possible_by_category[criterion.category] += criterion.max_points
        if not finding:
            continue
        raw_by_category[criterion.category] += (
            criterion.max_points * STATUS_MULTIPLIER.get(str(finding.status), 0.0)
        )

    breakdown: dict[str, float] = {}
    total = 0.0
    for category, max_points in CATEGORY_MAX.items():
        possible = possible_by_category[category]
        category_score = max_points * raw_by_category[category] / possible if possible else 0
        category_score = round(category_score, 1)
        breakdown[category] = category_score
        total += category_score

    total = round(max(0.0, min(100.0, total)), 1)
    return breakdown, total, classify_score(total)


def classify_score(score: float) -> str:
    if score < 40:
        return "Baixa prontidão"
    if score < 60:
        return "Prontidão limitada"
    if score < 80:
        return "Prontidão moderada"
    return "Boa prontidão"
