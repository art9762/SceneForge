"""SceneForge API — FastAPI backend for the web interface."""

from __future__ import annotations

import asyncio
import os
import re
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel, Field

from core.config import get_settings
from core.pipeline import Pipeline, PreparedRun, ProjectCompleteError, load_project_state
from core.schemas.project import ProjectState
from core.storage import ProjectBusyError


@asynccontextmanager
async def lifespan(_app):
    yield
    tasks = list(_running.values())
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)


app = FastAPI(title="SceneForge API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory tracking of running pipelines
_running: dict[str, asyncio.Task] = {}
_handles: dict[str, PreparedRun] = {}

ALLOWED_FINAL_FILES = {"script.md", "teleprompter.md"}


def _sanitize_name(raw: str) -> str:
    name = re.sub(r"[^a-zA-Z0-9_\-а-яА-ЯёЁ]", "-", raw)
    name = re.sub(r"-{2,}", "-", name)
    return name[:80].strip("-") or "project"


def _safe_project_path(project_dir: str) -> Path:
    base = Path(get_settings().projects_dir).resolve()
    candidate = (base / project_dir).resolve()
    if not str(candidate).startswith(str(base) + os.sep) and candidate != base:
        raise HTTPException(400, "Invalid project path")
    return candidate


class CreateProjectRequest(BaseModel):
    raw_idea: str = Field(..., min_length=1, max_length=4000)
    project_name: str | None = Field(None, max_length=80)
    provider: str = Field("claude", pattern=r"^(claude|openai)$")
    model: str | None = Field(None, max_length=100)


class SelectConceptRequest(BaseModel):
    concept_index: int = Field(..., ge=0, le=2)
    run_id: str | None = Field(None, max_length=100)


class ResumeProjectRequest(BaseModel):
    provider: str | None = Field(None, pattern=r"^(claude|openai)$")
    model: str | None = Field(None, max_length=100)


# ── Concept selection queue per project ──
_concept_queues: dict[str, asyncio.Queue] = {}


async def _web_select_concept(state: ProjectState) -> int:
    """Wait for concept selection from web UI."""
    q = _concept_queues.get(state.id)
    if q is None:
        raise ValueError('No concept selection channel for this run')
    return await q.get()


def _start_pipeline(pipeline: Pipeline, handle: PreparedRun) -> dict:
    state = handle.state
    _concept_queues[state.id] = asyncio.Queue(maxsize=1)
    _handles[state.id] = handle

    async def execute():
        try:
            await pipeline.run(prepared=handle)
        except Exception as error:
            logger.error('Pipeline {} failed: {}', state.id, error)

    def finished(task):
        # A task cancelled before its first instruction never enters run's
        # finally block. Release its reservation and record that interruption.
        try:
            handle.interrupt()
        finally:
            if _running.get(state.id) is task:
                _running.pop(state.id, None)
                _handles.pop(state.id, None)
                _concept_queues.pop(state.id, None)

    task = asyncio.create_task(execute())
    _running[state.id] = task
    task.add_done_callback(finished)
    return {'project_id': state.id, 'project_dir': str(pipeline.project_dir), 'run_id': state.run.id}


@app.post("/api/projects", response_model=dict)
async def create_project(req: CreateProjectRequest):
    name = _sanitize_name(req.project_name or req.raw_idea[:40])
    project_dir = _safe_project_path(name)

    pipeline = Pipeline(
        project_dir=project_dir,
        provider_name=req.provider,
        model=req.model,
        on_select_concept=_web_select_concept,
    )

    try:
        handle = pipeline.prepare_run(req.raw_idea, create_only=True)
    except (ProjectBusyError, FileExistsError) as error:
        raise HTTPException(409, str(error)) from None
    return _start_pipeline(pipeline, handle)


@app.get("/api/projects/{project_dir:path}/state")
async def get_project_state(project_dir: str):
    safe_dir = _safe_project_path(project_dir)
    state_file = safe_dir / "project.json"
    if not state_file.exists():
        raise HTTPException(404, "Project not found")
    state = load_project_state(safe_dir)
    steps = [
        "brief", "concepts", "select_concept", "structure",
        "draft_v1", "critique", "draft_v2", "production",
        "edit_notes", "assemble",
    ]
    return {
        "state": state.model_dump(mode="json"),
        "steps": steps,
        "total_steps": len(steps),
    }


@app.post('/api/projects/{project_dir:path}/resume')
async def resume_project(project_dir: str, req: ResumeProjectRequest):
    safe_dir = _safe_project_path(project_dir)
    if not (safe_dir / 'project.json').is_file():
        raise HTTPException(404, 'Project not found')
    state = ProjectState.load(safe_dir / 'project.json')
    pipeline = Pipeline(
        safe_dir, provider_name=req.provider or (state.run.provider if state.run else 'claude'),
        model=req.model if 'model' in req.model_fields_set else (state.run.model if state.run else None),
        on_select_concept=_web_select_concept,
    )
    if state.current_step >= len(pipeline.steps):
        raise HTTPException(409, 'Проект уже завершён.')
    try:
        handle = pipeline.prepare_run(resume_only=True)
    except (ProjectBusyError, ProjectCompleteError) as error:
        raise HTTPException(409, str(error)) from None
    except ValueError:
        raise HTTPException(409, 'Сохранённое состояние проекта некорректно. Проверьте project.json.') from None
    return _start_pipeline(pipeline, handle)


@app.post("/api/projects/{project_id}/select-concept")
async def select_concept(project_id: str, req: SelectConceptRequest):
    q = _concept_queues.get(project_id)
    handle = _handles.get(project_id)
    if q is None or handle is None or handle.closed:
        raise HTTPException(409, 'No active selection in this API process; resume the saved project first')
    path = handle.lock.project_dir / 'project.json'
    state = ProjectState.load(path)
    steps = Pipeline(handle.lock.project_dir).steps
    if req.run_id is not None and (state.run is None or req.run_id != state.run.id):
        raise HTTPException(409, 'Запуск уже изменился. Обновите состояние проекта и выберите концепцию снова.')
    if (state.run is None or state.run.id != handle.state.run.id or state.run.status != 'waiting_input'
            or not 0 <= state.current_step < len(steps)
            or steps[state.current_step].name != 'select_concept'
            or state.selected_concept_index is not None or state.concepts is None or q.full()):
        raise HTTPException(409, 'Project is not waiting for a concept selection')
    if req.concept_index >= len(state.concepts.concepts):
        raise HTTPException(422, 'Concept index is outside this project')
    # Commit the human decision before waking the runner. After a crash, resume
    # can advance this interactive step without asking or choosing again.
    state.selected_concept_index = req.concept_index
    state.run.status = 'running'
    state.updated_at = datetime.now(timezone.utc)
    state.save(path)
    q.put_nowait(req.concept_index)
    return {"status": "ok"}


@app.get("/api/projects/{project_dir:path}/final/{filename}")
async def get_final_file(project_dir: str, filename: str):
    if filename not in ALLOWED_FINAL_FILES:
        raise HTTPException(400, "Invalid filename")
    safe_dir = _safe_project_path(project_dir)
    file_path = safe_dir / "final" / filename
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    return {"content": file_path.read_text(encoding="utf-8")}


def start():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    start()
