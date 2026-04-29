"""LLM Provider abstraction layer."""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from typing import Any

from loguru import logger
from pydantic import BaseModel, ValidationError

from .retry import retry_async

# Maximum retries for JSON parse failures in generate_structured
_JSON_PARSE_RETRIES = 2


class LLMProvider(ABC):
    """Abstract base for LLM providers."""

    @abstractmethod
    async def generate(
        self,
        system: str,
        messages: list[dict[str, str]],
        model: str,
        response_schema: type[BaseModel] | None = None,
        temperature: float = 0.7,
    ) -> str:
        """Send messages to the LLM and return the text response."""
        ...

    async def generate_structured(
        self,
        system: str,
        messages: list[dict[str, str]],
        model: str,
        schema: type[BaseModel],
        temperature: float = 0.7,
    ) -> BaseModel:
        """Generate and parse a structured response.

        Appends JSON schema instructions to the system prompt and
        parses the LLM output into the given Pydantic model.
        Retries on JSON parse / validation errors up to _JSON_PARSE_RETRIES times.
        Network errors are retried by retry_async inside generate().
        """
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False, indent=2)
        augmented_system = (
            f"{system}\n\n"
            f"IMPORTANT: Respond ONLY with valid JSON matching this schema:\n"
            f"```json\n{schema_json}\n```\n"
            f"No commentary, no markdown fences — raw JSON only."
        )

        last_exc: Exception | None = None
        for attempt in range(_JSON_PARSE_RETRIES + 1):
            raw = await self.generate(augmented_system, messages, model, temperature=temperature)

            # Strip markdown fences if the model wraps them anyway
            cleaned = raw.strip()
            if cleaned.startswith("```"):
                cleaned = cleaned.split("\n", 1)[1] if "\n" in cleaned else cleaned[3:]
            if cleaned.endswith("```"):
                cleaned = cleaned[:-3]
            cleaned = cleaned.strip()

            try:
                return schema.model_validate_json(cleaned)
            except (json.JSONDecodeError, ValidationError) as exc:
                last_exc = exc
                if attempt < _JSON_PARSE_RETRIES:
                    logger.warning(
                        "JSON parse failed (attempt {}/{}): {} — retrying LLM call",
                        attempt + 1,
                        _JSON_PARSE_RETRIES + 1,
                        exc,
                    )
                else:
                    logger.error(
                        "JSON parse failed after {} attempts. Raw response: {}",
                        _JSON_PARSE_RETRIES + 1,
                        raw[:500],
                    )

        raise last_exc  # type: ignore[misc]


def get_provider(name: str) -> LLMProvider:
    """Factory: 'claude' or 'openai'. Validates API key is set."""
    from ..config import get_settings
    get_settings().validate_provider(name)

    if name == "claude":
        from .claude import ClaudeProvider
        return ClaudeProvider()
    elif name == "openai":
        from .openai_provider import OpenAIProvider
        return OpenAIProvider()
    else:
        raise ValueError(f"Unknown provider: {name}")
