"""Tests for agents and pipeline with mocked LLM provider."""

from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest

from core.llm.provider import LLMProvider
from core.agents.brief import BriefAgent
from core.agents.concept import ConceptAgent
from core.agents.assembler import FinalAssembler, AssemblerInput, AssemblerOutput
from core.schemas.brief import Brief, BriefInput
from core.schemas.concept import Concepts, ConceptInput
from core.schemas.project import ProjectState
from core.config import Settings


class MockProvider(LLMProvider):
    """Mock LLM provider that returns predefined JSON responses."""

    def __init__(self, response_json: str):
        self._response = response_json

    async def generate(self, system, messages, model, response_schema=None, temperature=0.7):
        return self._response


class TestBriefAgent:
    @pytest.mark.asyncio
    async def test_brief_agent_parses_response(self):
        brief_json = json.dumps({
            "title": "Тест",
            "format": "обзор",
            "duration_minutes": 10.0,
            "target_audience": "все",
            "tone": "серьёзный",
            "style": "документальный",
            "platform": "YouTube",
            "goal": "просветить",
            "constraints": [],
            "keywords": ["тест"],
        })

        agent = BriefAgent()
        provider = MockProvider(brief_json)
        result = await agent.run(BriefInput(raw_idea="тест"), provider=provider, model="test-model")

        assert isinstance(result, Brief)
        assert result.title == "Тест"
        assert result.duration_minutes == 10.0

    @pytest.mark.asyncio
    async def test_brief_agent_handles_markdown_fences(self):
        brief_json = "```json\n" + json.dumps({
            "title": "Fenced",
            "format": "обзор",
            "duration_minutes": 5.0,
            "target_audience": "все",
            "tone": "лёгкий",
            "style": "влог",
            "platform": "YouTube",
            "goal": "развлечь",
            "constraints": [],
            "keywords": [],
        }) + "\n```"

        agent = BriefAgent()
        provider = MockProvider(brief_json)
        result = await agent.run(BriefInput(raw_idea="тест"), provider=provider, model="test-model")
        assert result.title == "Fenced"


class TestConceptAgent:
    @pytest.mark.asyncio
    async def test_concept_agent(self, sample_brief):
        concepts_json = json.dumps({
            "concepts": [
                {
                    "name": f"Концепт {i}",
                    "direction": ["безопасный", "смелый", "экспериментальный"][i],
                    "logline": f"Логлайн {i}",
                    "synopsis": f"Синопсис {i}",
                    "tone_description": f"Тон {i}",
                    "why_it_works": f"Потому что {i}",
                }
                for i in range(3)
            ]
        })

        agent = ConceptAgent()
        provider = MockProvider(concepts_json)
        result = await agent.run(ConceptInput(brief=sample_brief), provider=provider, model="m")

        assert isinstance(result, Concepts)
        assert len(result.concepts) == 3
        assert result.concepts[0].name == "Концепт 0"


class TestFinalAssembler:
    @pytest.mark.asyncio
    async def test_assembler_produces_markdown(self, sample_project):
        assembler = FinalAssembler()
        result = await assembler.run(AssemblerInput(project=sample_project))

        assert isinstance(result, AssemblerOutput)
        assert "# Заброшенная советская обсерватория" in result.script_markdown
        assert "## Бриф" in result.script_markdown
        assert "## Сценарий" in result.script_markdown
        assert result.teleprompter_text  # non-empty

    @pytest.mark.asyncio
    async def test_assembler_teleprompter_has_voiceover(self, sample_project):
        assembler = FinalAssembler()
        result = await assembler.run(AssemblerInput(project=sample_project))

        assert "Здесь когда-то слушали космос." in result.teleprompter_text
        assert "[VIDEO]" not in result.teleprompter_text


class TestRetryLogic:
    @pytest.mark.asyncio
    async def test_generate_structured_retries_on_bad_json(self):
        """Test that generate_structured retries when LLM returns invalid JSON."""
        provider = MockProvider("")  # will override generate

        call_count = 0
        valid_json = json.dumps({"title": "OK", "format": "", "duration_minutes": 0,
                                  "target_audience": "", "tone": "", "style": "",
                                  "platform": "", "goal": "", "constraints": [], "keywords": []})

        async def fake_generate(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                return "NOT VALID JSON!!!"
            return valid_json

        provider.generate = fake_generate
        result = await provider.generate_structured(
            system="test",
            messages=[{"role": "user", "content": "test"}],
            model="m",
            schema=Brief,
        )
        assert result.title == "OK"
        assert call_count == 3  # 2 failures + 1 success


class TestConfig:
    def test_validate_provider_claude_missing(self):
        s = Settings(trinity_claude_api_key="", trinity_openai_api_key="key")
        with pytest.raises(ValueError, match="TRINITY_CLAUDE_API_KEY"):
            s.validate_provider("claude")

    def test_validate_provider_openai_missing(self):
        s = Settings(trinity_claude_api_key="key", trinity_openai_api_key="")
        with pytest.raises(ValueError, match="TRINITY_OPENAI_API_KEY"):
            s.validate_provider("openai")

    def test_validate_provider_ok(self):
        s = Settings(trinity_claude_api_key="key")
        s.validate_provider("claude")  # should not raise
