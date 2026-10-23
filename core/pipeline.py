"""Pipeline engine — orchestrates agents through the script development process."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Awaitable

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
from .schemas.project import PipelineRun, ProjectState
from .storage import ProjectBusyError, ProjectLock
from .llm.provider import LLMProvider, get_provider

console = Console()


class ProjectCompleteError(ValueError):
    pass


@dataclass
class PipelineStep:
    name: str
    description: str
    execute: Callable[[ProjectState, LLMProvider | None], Awaitable[ProjectState]]
    interactive: bool = False
    optional: bool = False
    uses_llm: bool = True


@dataclass
class PreparedRun:
    state: ProjectState
    lock: ProjectLock
    closed: bool = False
    started: bool = False

    def finish(self, status: str, error: str | None = None, error_type: str | None = None) -> None:
        # Read the last committed boundary, discarding partial in-memory outputs.
        state = ProjectState.load(self.lock.project_dir / 'project.json')
        if state.run is not None and state.run.id == self.state.run.id:
            state.run.status = status
            state.run.error, state.run.error_type = error, error_type
            state.run.finished_at = datetime.now(timezone.utc)
            state.updated_at = datetime.now(timezone.utc)
            state.save(self.lock.project_dir / 'project.json')

    def close(self) -> None:
        if not self.closed:
            self.closed = True
            self.lock.close()

    def interrupt(self) -> None:
        if not self.closed:
            try:
                self.finish('interrupted', 'Выполнение прервано. Можно продолжить с сохранённого шага.')
            finally:
                self.close()


def load_project_state(project_dir: Path) -> ProjectState:
    """Recover an orphaned active receipt only while holding its execution lock."""
    try:
        lock = ProjectLock(project_dir).acquire()
    except ProjectBusyError:
        return ProjectState.load(project_dir / 'project.json')
    try:
        state = ProjectState.load(project_dir / 'project.json')
        if state.run is not None and state.run.status in ('running', 'waiting_input'):
            state.run.status = 'interrupted'
            state.run.error = 'Процесс остановился до завершения. Можно продолжить с сохранённого шага.'
            state.run.finished_at = datetime.now(timezone.utc)
            state.updated_at = datetime.now(timezone.utc)
            state.save(project_dir / 'project.json')
        return state
    finally:
        lock.close()


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
            PipelineStep("select_concept", "Выбор концепции", self._step_select_concept, interactive=True, uses_llm=False),
            PipelineStep("structure", "Построение структуры", self._step_structure),
            PipelineStep("draft_v1", "Написание первого черновика", self._step_draft_v1),
            PipelineStep("critique", "Критика сценария", self._step_critique),
            PipelineStep("draft_v2", "Переписывание сценария", self._step_rewrite),
            PipelineStep("production", "Продюсерские заметки", self._step_production),
            PipelineStep("edit_notes", "Монтажные заметки", self._step_edit_notes),
            PipelineStep("assemble", "Сборка финального пакета", self._step_assemble, uses_llm=False),
        ]

    def _save(self, state: ProjectState) -> None:
        state.updated_at = datetime.now(timezone.utc)
        state.save(self.state_path)

    def prepare_run(self, raw_idea: str | None = None, *, create_only: bool = False, resume_only: bool = False,
                    initial_state: ProjectState | None = None) -> PreparedRun:
        """Reserve before scheduling a task, so concurrent starts cannot race."""
        lock = ProjectLock(self.project_dir).acquire()
        try:
            if create_only and self.state_path.exists():
                raise FileExistsError('Проект уже существует. Откройте его и продолжите сохранённый запуск.')
            if initial_state is not None:
                state = initial_state
            elif self.state_path.exists():
                state = ProjectState.load(self.state_path)
            elif raw_idea:
                state = ProjectState(raw_idea=raw_idea)
            else:
                raise ValueError('raw_idea is required for new projects')
            if not 0 <= state.current_step <= len(self._steps):
                raise ValueError('Invalid saved pipeline step')
            if resume_only and state.current_step == len(self._steps):
                raise ProjectCompleteError('Проект уже завершён.')
            state.run = PipelineRun(provider=self.provider_name, model=self.model)
            self._save(state)
            return PreparedRun(state, lock)
        except BaseException:
            lock.close()
            raise

    async def run(self, raw_idea: str | None = None, *, prepared: PreparedRun | None = None,
                  stop_after: int | None = None) -> ProjectState:
        """Continue from the first uncommitted step; never replay completed steps."""
        handle = prepared or self.prepare_run(raw_idea)
        if handle.closed or handle.started or handle.lock.project_dir != self.project_dir.resolve():
            raise ValueError('Invalid prepared pipeline run')
        handle.started = True
        state = handle.state
        try:
            while state.current_step < (len(self._steps) if stop_after is None else stop_after):
                step = self._steps[state.current_step]
                state.run.step_name = step.name
                state.run.status = 'waiting_input' if step.interactive and state.selected_concept_index is None else 'running'
                self._save(state)
                provider = self._get_provider() if step.uses_llm else None
                t0 = time.monotonic()
                state = await step.execute(state, provider)
                state.current_step += 1
                state.run.status = 'completed' if state.current_step == len(self._steps) else 'running'
                if state.run.status == 'completed':
                    state.run.finished_at = datetime.now(timezone.utc)
                self._save(state)
                logger.info("Step {}/{} '{}' completed in {:.1f}s", state.current_step, len(self._steps), step.name, time.monotonic() - t0)
            state.run.status = 'completed' if state.current_step == len(self._steps) else 'paused'
            state.run.finished_at = datetime.now(timezone.utc)
            self._save(state)
            return state
        except asyncio.CancelledError:
            handle.finish('interrupted', 'Выполнение прервано. Можно продолжить с сохранённого шага.')
            raise
        except Exception as error:
            handle.finish('failed', 'Шаг завершился ошибкой. Проверьте настройки и доступность провайдера, затем повторите.',
                          type(error).__name__)
            raise
        finally:
            handle.close()

    async def run_step(self, step_index: int, state: ProjectState) -> ProjectState:
        """Run a single step."""
        if not 0 <= step_index < len(self._steps):
            raise ValueError('Invalid step index')
        state = state.model_copy(deep=True)
        state.current_step = step_index
        handle = self.prepare_run(initial_state=state)
        return await self.run(prepared=handle, stop_after=step_index + 1)

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
        if state.selected_concept_index is not None:
            if state.concepts is None or not 0 <= state.selected_concept_index < len(state.concepts.concepts):
                raise ValueError('Invalid saved concept selection')
            return state
        if self.on_select_concept:
            state.selected_concept_index = await self.on_select_concept(state)
        else:
            state.selected_concept_index = 0
        return state

    async def _step_structure(self, state: ProjectState, provider: LLMProvider | None) -> ProjectState:
        idx = state.selected_concept_index
        n = len(state.concepts.concepts)
        if not (0 <= idx < n):
            raise ValueError(f"selected_concept_index {idx} out of range [0, {n})")
        concept = state.concepts.concepts[idx]
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
