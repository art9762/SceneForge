"""Pipeline engine — orchestrates agents through the script development process."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Awaitable

from loguru import logger
from rich.console import Console

from .agents import (
    BriefAgent, ConceptAgent, StoryArchitect, SceneWriter,
    CriticAgent, RewriteAgent, ProducerAgent, EditorAgent, FinalAssembler,
)
from .agents.assembler import AssemblerInput, AssemblerOutput
from .agents.rewriter import RewriteInput
from .schemas import (
    BriefInput, ConceptInput, StructureInput, SceneInput,
    CritiqueInput, ProductionInput, EditInput,
)
from .schemas.project import ProjectState
from .llm.provider import LLMProvider, get_provider

console = Console()


@dataclass
class PipelineStep:
    name: str
    description: str
    execute: Callable[[ProjectState, LLMProvider | None], Awaitable[ProjectState]]
    interactive: bool = False
    optional: bool = False


class Pipeline:
    """Runs the SceneForge pipeline step by step, saving state after each."""

    def __init__(
        self,
        project_dir: str | Path,
        provider_name: str = "claude",
        model: str | None = None,
        on_select_concept: Callable[[ProjectState], Awaitable[int]] | None = None,
    ):
        self.project_dir = Path(project_dir)
        self.project_dir.mkdir(parents=True, exist_ok=True)
        self.state_path = self.project_dir / "project.json"
        self.provider_name = provider_name
        self.model = model
        self.on_select_concept = on_select_concept
        self._steps = self._build_steps()

    @property
    def steps(self) -> list[PipelineStep]:
        return self._steps

    def _get_provider(self) -> LLMProvider:
        return get_provider(self.provider_name)

    def _build_steps(self) -> list[PipelineStep]:
        return [
            PipelineStep("brief", "Генерация брифа", self._step_brief),
            PipelineStep("concepts", "Генерация концепций", self._step_concepts),
            PipelineStep("select_concept", "Выбор концепции", self._step_select_concept, interactive=True),
            PipelineStep("structure", "Построение структуры", self._step_structure),
            PipelineStep("draft_v1", "Написание первого черновика", self._step_draft_v1),
            PipelineStep("critique", "Критика сценария", self._step_critique),
            PipelineStep("draft_v2", "Переписывание сценария", self._step_rewrite),
            PipelineStep("production", "Продюсерские заметки", self._step_production),
            PipelineStep("edit_notes", "Монтажные заметки", self._step_edit_notes),
            PipelineStep("assemble", "Сборка финального пакета", self._step_assemble),
        ]

    def _save(self, state: ProjectState) -> None:
        state.updated_at = datetime.now(timezone.utc)
        state.save(self.state_path)

    async def run(self, raw_idea: str | None = None) -> ProjectState:
        """Run the full pipeline from scratch or resume."""
        if self.state_path.exists():
            state = ProjectState.load(self.state_path)
            console.print(f"[yellow]Resuming project from step {state.current_step}[/yellow]")
        else:
            if not raw_idea:
                raise ValueError("raw_idea is required for new projects")
            state = ProjectState(raw_idea=raw_idea)
            self._save(state)

        while state.current_step < len(self._steps):
            step = self._steps[state.current_step]
            console.print(f"\n[bold cyan]━━━ Шаг {state.current_step + 1}/{len(self._steps)}: {step.description} ━━━[/bold cyan]")

            provider = self._get_provider()
            t0 = time.monotonic()
            state = await step.execute(state, provider)
            elapsed = time.monotonic() - t0
            state.current_step += 1
            self._save(state)

            logger.info("Step {}/{} '{}' completed in {:.1f}s", state.current_step, len(self._steps), step.name, elapsed)
            console.print(f"[green]✓ {step.description} — готово ({elapsed:.1f}s)[/green]")

        console.print("\n[bold green]🎬 Пайплайн завершён![/bold green]")
        return state

    async def run_step(self, step_index: int, state: ProjectState) -> ProjectState:
        """Run a single step."""
        step = self._steps[step_index]
        provider = self._get_provider()
        state = await step.execute(state, provider)
        state.current_step = step_index + 1
        self._save(state)
        return state

    # ── Individual steps ──────────────────────────────────────────

    async def _step_brief(self, state: ProjectState, provider: LLMProvider | None) -> ProjectState:
        agent = BriefAgent()
        state.brief = await agent.run(BriefInput(raw_idea=state.raw_idea), provider, self.model)
        return state

    async def _step_concepts(self, state: ProjectState, provider: LLMProvider | None) -> ProjectState:
        agent = ConceptAgent()
        state.concepts = await agent.run(ConceptInput(brief=state.brief), provider, self.model)
        return state

    async def _step_select_concept(self, state: ProjectState, provider: LLMProvider | None) -> ProjectState:
        if self.on_select_concept:
            state.selected_concept_index = await self.on_select_concept(state)
        else:
            state.selected_concept_index = 0
        return state

    async def _step_structure(self, state: ProjectState, provider: LLMProvider | None) -> ProjectState:
        concept = state.concepts.concepts[state.selected_concept_index]
        agent = StoryArchitect()
        state.structure = await agent.run(
            StructureInput(brief=state.brief, concept=concept), provider, self.model
        )
        return state

    async def _step_draft_v1(self, state: ProjectState, provider: LLMProvider | None) -> ProjectState:
        concept = state.concepts.concepts[state.selected_concept_index]
        agent = SceneWriter()
        state.draft_v1 = await agent.run(
            SceneInput(brief=state.brief, concept=concept, structure=state.structure),
            provider, self.model,
        )
        return state

    async def _step_critique(self, state: ProjectState, provider: LLMProvider | None) -> ProjectState:
        agent = CriticAgent()
        state.critique = await agent.run(
            CritiqueInput(brief=state.brief, draft=state.draft_v1), provider, self.model
        )
        return state

    async def _step_rewrite(self, state: ProjectState, provider: LLMProvider | None) -> ProjectState:
        agent = RewriteAgent()
        state.draft_v2 = await agent.run(
            RewriteInput(brief=state.brief, draft=state.draft_v1, critique=state.critique),
            provider, self.model,
        )
        return state

    async def _step_production(self, state: ProjectState, provider: LLMProvider | None) -> ProjectState:
        draft = state.draft_v2 or state.draft_v1
        agent = ProducerAgent()
        state.production_notes = await agent.run(
            ProductionInput(brief=state.brief, draft=draft), provider, self.model
        )
        return state

    async def _step_edit_notes(self, state: ProjectState, provider: LLMProvider | None) -> ProjectState:
        draft = state.draft_v2 or state.draft_v1
        agent = EditorAgent()
        state.edit_notes = await agent.run(
            EditInput(brief=state.brief, draft=draft), provider, self.model
        )
        return state

    async def _step_assemble(self, state: ProjectState, provider: LLMProvider | None) -> ProjectState:
        assembler = FinalAssembler()
        result: AssemblerOutput = await assembler.run(AssemblerInput(project=state))

        # Save final outputs
        final_dir = self.project_dir / "final"
        final_dir.mkdir(exist_ok=True)
        (final_dir / "script.md").write_text(result.script_markdown, encoding="utf-8")
        (final_dir / "teleprompter.md").write_text(result.teleprompter_text, encoding="utf-8")

        state.final_script = result.script_markdown
        return state
