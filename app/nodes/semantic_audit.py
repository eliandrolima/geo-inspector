from __future__ import annotations

from pydantic import ValidationError

from app.config import Settings, get_settings
from app.exceptions import LLMConfigurationError, LLMProviderError, LLMSchemaError
from app.schemas.audit import SemanticAuditResult
from app.services.llm_factory import LLMProvider, get_llm_provider
from app.state import AuditState


async def run_semantic_audit_node(
    state: AuditState,
    *,
    settings: Settings | None = None,
    llm_provider: LLMProvider | None = None,
) -> AuditState:
    settings = settings or get_settings()
    provider = llm_provider
    text_limit = settings.semantic_text_limit
    extracted_text = state.get("extracted_text", "")[:text_limit]
    try:
        provider = provider or get_llm_provider(settings)
        raw_result = await provider.audit_semantics(
            page_type=state.get("page_type", "tipo não identificado"),
            audit_plan=state.get("audit_plan", []),
            metadata=state.get("metadata", {}),
            extracted_text=extracted_text,
            validation_errors=state.get("validation_errors", []),
        )
        result = SemanticAuditResult.model_validate(raw_result)
    except LLMConfigurationError as exc:
        message = str(exc)
        return {
            "status": "semantic_failed",
            "error_type": "llm_configuration",
            "error_message": message,
            "semantic_findings": [],
            "validation_errors": [*state.get("validation_errors", []), message],
        }
    except LLMProviderError as exc:
        message = str(exc)
        return {
            "status": "semantic_failed",
            "error_type": "llm_provider",
            "error_message": message,
            "semantic_findings": [],
            "validation_errors": [*state.get("validation_errors", []), message],
        }
    except (ValidationError, LLMSchemaError) as exc:
        message = "A resposta semântica não respeitou o schema exigido."
        return {
            "status": "semantic_failed",
            "error_type": "semantic_schema",
            "error_message": message,
            "semantic_findings": [],
            "validation_errors": [*state.get("validation_errors", []), f"{message} {exc}"],
        }
    return {
        "status": "semantic_audit_completed",
        "error_type": "",
        "error_message": "",
        "semantic_summary": result.summary,
        "semantic_findings": [finding.model_dump(mode="json") for finding in result.findings],
    }
