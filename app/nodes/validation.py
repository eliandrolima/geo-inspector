from __future__ import annotations

from uuid import uuid4

from app.exceptions import URLValidationError
from app.state import AuditState
from app.tools.safe_http import Resolver, validate_public_url


def validate_url_node(
    state: AuditState,
    *,
    resolver: Resolver | None = None,
) -> AuditState:
    execution_id = state.get("execution_id") or str(uuid4())
    base: AuditState = {
        "execution_id": execution_id,
        "retry_count": state.get("retry_count", 0),
        "warnings": state.get("warnings", []),
        "validation_errors": state.get("validation_errors", []),
    }
    try:
        validated = validate_public_url(state.get("url", ""), resolver=resolver)
    except URLValidationError as exc:
        errors = [*base["validation_errors"], str(exc)]
        return {
            **base,
            "status": "invalid_url",
            "error_type": "invalid_url",
            "error_message": str(exc),
            "validation_errors": errors,
        }
    return {
        **base,
        "status": "validated",
        "normalized_url": validated.normalized_url,
    }
