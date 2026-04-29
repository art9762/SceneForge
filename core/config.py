"""SceneForge configuration — loads from .env and provides defaults."""

from __future__ import annotations

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    # Trinity proxy — Claude
    trinity_claude_api_key: str = ""
    trinity_claude_base_url: str = "https://gate.trinity.tg/aurora/v1"

    # Trinity proxy — OpenAI
    trinity_openai_api_key: str = ""
    trinity_openai_base_url: str = "https://gate.trinity.tg/orion/v1"

    # Default models
    default_claude_model: str = "claude-sonnet-4-6"
    default_openai_model: str = "gpt-5.4"

    # Project storage
    projects_dir: str = "projects"

    def validate_provider(self, provider: str) -> None:
        """Raise a clear error if the API key for the chosen provider is missing."""
        if provider == "claude" and not self.trinity_claude_api_key:
            raise ValueError(
                "TRINITY_CLAUDE_API_KEY не задан.\n"
                "Скопируйте .env.example в .env и заполните ключ:\n"
                "  cp .env.example .env"
            )
        if provider == "openai" and not self.trinity_openai_api_key:
            raise ValueError(
                "TRINITY_OPENAI_API_KEY не задан.\n"
                "Скопируйте .env.example в .env и заполните ключ:\n"
                "  cp .env.example .env"
            )


_settings: Settings | None = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
