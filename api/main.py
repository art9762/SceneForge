"""SceneForge API — FastAPI backend for the web interface."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.config import get_settings
from core.pipeline import Pipeline
from core.schemas.project import ProjectState

app = FastAPI(title="SceneForge API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# In-memory tracking of running pipelines
_running: dict[str, asyncio.Task] = {}


class CreateProjectRequest(BaseModel):
    raw_idea: str
    project_name: str | None = None
    provider: str = "claude"
    model: str | None = None


class SelectConceptRequest(BaseModel):
    concept_index: int


class StepResponse(BaseModel):
    step: int
    total_steps: int
    step_name: str
    status: str  # "completed" | "waiting_input" | "running" | "error"


# ── Concept selection queue per project ──
_concept_queues: dict[str, asyncio.Queue] = {}


async def _web_select_concept(state: ProjectState) -> int:
    """Wait for concept selection from web UI."""
    q = _concept_queues.get(state.id)
    if q is None:
        return 0
    return await q.get()


@app.post("/api/projects", response_model=dict)
async def create_project(req: CreateProjectRequest):
    settings = get_settings()
    name = req.project_name or req.raw_idea[:40].replace(" ", "-").lower()
    project_dir = Path(settings.projects_dir) / name

    pipeline = Pipeline(
        project_dir=project_dir,
        provider_name=req.provider,
        model=req.model,
        on_select_concept=_web_select_concept,
    )

    # Create initial state
    state = ProjectState(raw_idea=req.raw_idea)
    state.save(project_dir / "project.json")

    _concept_queues[state.id] = asyncio.Queue()

    # Run pipeline in background
    async def _run():
        try:
            await pipeline.run(raw_idea=req.raw_idea)
        except Exception as e:
            print(f"Pipeline error: {e}")

    task = asyncio.create_task(_run())
    _running[state.id] = task

    return {"project_id": state.id, "project_dir": str(project_dir)}


@app.get("/api/projects/{project_dir:path}/state")
async def get_project_state(project_dir: str):
    state_file = Path(project_dir) / "project.json"
    if not state_file.exists():
        raise HTTPException(404, "Project not found")
    state = ProjectState.load(state_file)
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


@app.post("/api/projects/{project_id}/select-concept")
async def select_concept(project_id: str, req: SelectConceptRequest):
    q = _concept_queues.get(project_id)
    if q is None:
        raise HTTPException(404, "No pending concept selection for this project")
    await q.put(req.concept_index)
    return {"status": "ok"}


@app.get("/api/projects/{project_dir:path}/final/{filename}")
async def get_final_file(project_dir: str, filename: str):
    file_path = Path(project_dir) / "final" / filename
    if not file_path.exists():
        raise HTTPException(404, "File not found")
    return {"content": file_path.read_text(encoding="utf-8")}


def start():
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)


if __name__ == "__main__":
    start()
