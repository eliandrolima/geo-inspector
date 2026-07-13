from __future__ import annotations

from app.schemas.findings import Finding, FindingPriority, FindingStatus
from app.services.scoring import SCORING_CRITERIA, calculate_geo_score, classify_score


def make_finding(category: str, criterion: str, status: str) -> Finding:
    return Finding(
        category=category,
        criterion=criterion,
        status=status,
        evidence={"source": "teste", "observed": "evidência observável"},
        impact="impacto",
        recommendation="recomendação ligada à evidência",
        priority=FindingPriority.LOW,
        confidence=0.9,
    )


def test_score_upper_bound():
    findings = [
        make_finding(item.category, item.criterion, FindingStatus.PASSED.value)
        for item in SCORING_CRITERIA
    ]
    breakdown, score, classification = calculate_geo_score(findings)
    assert sum(breakdown.values()) == 100
    assert score == 100
    assert classification == "Boa prontidão"


def test_score_lower_bound_for_failed_findings():
    findings = [
        make_finding(item.category, item.criterion, FindingStatus.FAILED.value)
        for item in SCORING_CRITERIA
    ]
    _, score, classification = calculate_geo_score(findings)
    assert score == 0
    assert classification == "Baixa prontidão"


def test_not_applicable_is_removed_from_category_denominator():
    findings = [
        make_finding(item.category, item.criterion, FindingStatus.PASSED.value)
        for item in SCORING_CRITERIA
    ]
    first = SCORING_CRITERIA[0]
    findings[0] = make_finding(
        first.category, first.criterion, FindingStatus.NOT_APPLICABLE.value
    )
    _, score, _ = calculate_geo_score(findings)
    assert score == 100


def test_classifications():
    assert classify_score(39.9) == "Baixa prontidão"
    assert classify_score(40) == "Prontidão limitada"
    assert classify_score(60) == "Prontidão moderada"
    assert classify_score(80) == "Boa prontidão"
