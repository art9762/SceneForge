"""OpenAI/ChatGPT provider via Trinity proxy (openai SDK)."""

from __future__ import annotations

from openai import AsyncOpenAI

from ..config import get_settings
from .provider import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self) -> None:
        s = get_settings()
        self._client = AsyncOpenAI(
            api_key=s.trinity_openai_api_key,
            base_url=s.trinity_openai_base_url,
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
        full_messages = [{"role": "system", "content": system}] + messages
        resp = await self._client.chat.completions.create(
            model=model or s.default_openai_model,
            messages=full_messages,
            temperature=temperature,
            max_tokens=8192,
        )
        return resp.choices[0].message.content
