"""Base agent class — all pipeline agents inherit from this."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import ClassVar

from pydantic import BaseModel

from ..llm.provider import LLMProvider, get_provider
from ..config import get_settings


class BaseAgent(ABC):
    """A single pipeline stage that takes structured input and returns structured output."""

    name: ClassVar[str]
    description: ClassVar[str]
    system_prompt: ClassVar[str]
    input_schema: ClassVar[type[BaseModel]]
    output_schema: ClassVar[type[BaseModel]]
    default_provider: ClassVar[str] = "claude"  # "claude" | "openai"
    default_model: ClassVar[str] = ""  # empty = use provider default

    async def run(
        self,
        input_data: BaseModel,
        provider: LLMProvider | None = None,
        model: str | None = None,
    ) -> BaseModel:
        """Execute this agent: send input to LLM, get structured output."""
        if provider is None:
            provider = get_provider(self.default_provider)

        settings = get_settings()
        if model is None:
            model = self.default_model or (
                settings.default_claude_model
                if self.default_provider == "claude"
                else settings.default_openai_model
            )

        user_message = self.build_user_message(input_data)
        messages = [{"role": "user", "content": user_message}]

        result = await provider.generate_structured(
            system=self.system_prompt,
            messages=messages,
            model=model,
            schema=self.output_schema,
        )
        return result

    def build_user_message(self, input_data: BaseModel) -> str:
        """Convert input data to user message. Override for custom formatting."""
        return input_data.model_dump_json(indent=2)
