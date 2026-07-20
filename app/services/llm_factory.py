from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any, Protocol

import httpx

from app.config import Settings, get_settings
from app.exceptions import LLMConfigurationError, LLMProviderError, LLMSchemaError
from app.prompts.semantic_audit import SYSTEM_PROMPT, build_semantic_user_prompt


class LLMProvider(Protocol):
    async def audit_semantics(
        self,
        *,
        page_type: str,
        audit_plan: list[str],
        metadata: dict[str, Any],
        extracted_text: str,
        validation_errors: list[str],
    ) -> dict[str, Any]:
        ...


class OpenAILLMProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.openai_api_key:
            raise LLMConfigurationError("OPENAI_API_KEY não configurada.")
        if not settings.model_name:
            raise LLMConfigurationError("MODEL_NAME não configurado.")
        self.settings = settings

    async def audit_semantics(
        self,
        *,
        page_type: str,
        audit_plan: list[str],
        metadata: dict[str, Any],
        extracted_text: str,
        validation_errors: list[str],
    ) -> dict[str, Any]:
        user_prompt = build_semantic_user_prompt(
            page_type=page_type,
            audit_plan=audit_plan,
            metadata=metadata,
            extracted_text=extracted_text,
            validation_errors=validation_errors,
        )
        payload = {
            "model": self.settings.model_name,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "response_format": {"type": "json_object"},
        }
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.settings.openai_api_key}"},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise _provider_status_error("OpenAI", exc) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError("Falha ao comunicar com o provedor OpenAI.") from exc
        content = response.json()["choices"][0]["message"]["content"]
        return _parse_json_content(content)


class GoogleLLMProvider:
    def __init__(self, settings: Settings) -> None:
        if not settings.google_api_key:
            raise LLMConfigurationError("GOOGLE_API_KEY não configurada.")
        if not settings.model_name:
            raise LLMConfigurationError("MODEL_NAME não configurado.")
        self.settings = settings

    async def audit_semantics(
        self,
        *,
        page_type: str,
        audit_plan: list[str],
        metadata: dict[str, Any],
        extracted_text: str,
        validation_errors: list[str],
    ) -> dict[str, Any]:
        user_prompt = build_semantic_user_prompt(
            page_type=page_type,
            audit_plan=audit_plan,
            metadata=metadata,
            extracted_text=extracted_text,
            validation_errors=validation_errors,
        )
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.settings.model_name}:generateContent"
        )
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_PROMPT}]},
            "contents": [{"role": "user", "parts": [{"text": user_prompt}]}],
            "generationConfig": {
                "temperature": 0,
                "responseMimeType": "application/json",
            },
        }
        try:
            async with httpx.AsyncClient(timeout=self.settings.request_timeout_seconds) as client:
                response = await client.post(
                    endpoint,
                    params={"key": self.settings.google_api_key},
                    json=payload,
                )
                response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise _provider_status_error("Google Gemini", exc) from exc
        except httpx.HTTPError as exc:
            raise LLMProviderError("Falha ao comunicar com o provedor Google Gemini.") from exc
        content = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        return _parse_json_content(content)


class FakeLLMProvider:
    """Injectable test double; never selected by production configuration."""

    def __init__(self, responses: Sequence[dict[str, Any]]) -> None:
        self._responses = list(responses)
        self.calls = 0

    async def audit_semantics(
        self,
        *,
        page_type: str,
        audit_plan: list[str],
        metadata: dict[str, Any],
        extracted_text: str,
        validation_errors: list[str],
    ) -> dict[str, Any]:
        self.calls += 1
        index = min(self.calls - 1, len(self._responses) - 1)
        return self._responses[index]


def get_llm_provider(settings: Settings | None = None) -> LLMProvider:
    settings = settings or get_settings()
    provider = (settings.llm_provider or "").strip().lower()
    if provider == "openai":
        return OpenAILLMProvider(settings)
    if provider == "google":
        return GoogleLLMProvider(settings)
    raise LLMConfigurationError("LLM_PROVIDER deve ser 'openai' ou 'google'.")


def _parse_json_content(content: str) -> dict[str, Any]:
    raw = content.strip()
    if raw.startswith("```"):
        raw = raw.strip("`")
        raw = raw.removeprefix("json").strip()
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise LLMSchemaError("A resposta da LLM não é JSON válido.") from exc
    if not isinstance(parsed, dict):
        raise LLMSchemaError("A resposta da LLM deve ser um objeto JSON.")
    return parsed


def _provider_status_error(provider: str, exc: httpx.HTTPStatusError) -> Exception:
    status_code = exc.response.status_code
    if status_code in {401, 403}:
        return LLMConfigurationError(
            f"{provider} recusou a requisição. Verifique chave e permissões configuradas."
        )
    if status_code == 404:
        return LLMConfigurationError(
            f"{provider} não encontrou o modelo configurado ou ele não está disponível para a chave usada."
        )
    return LLMProviderError(
        f"{provider} retornou erro HTTP {status_code} durante a auditoria semântica."
    )
