"""Claude provider via Trinity proxy (anthropic SDK)."""

from __future__ import annotations

import anthropic

from ..config import get_settings
from .provider import LLMProvider


class ClaudeProvider(LLMProvider):
    def __init__(self) -> None:
        s = get_settings()
        self._client = anthropic.AsyncAnthropic(
            api_key=s.trinity_claude_api_key,
            base_url=s.trinity_claude_base_url,
        )

    async def generate(
        self,
        system: str,
        messages: list[dict[str, str]],
        model: str,
        response_schema=None,
        temperature: float = 0.7,
    ) -> str:
        s = get_settings()
        resp = await self._client.messages.create(
            model=model or s.default_claude_model,
            max_tokens=8192,
            system=system,
            messages=messages,
            temperature=temperature,
        )
        return resp.content[0].text
