"""Exercise the web contract without provider credentials or LLM calls."""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

from api import main as api
from core.schemas.project import ProjectState


@pytest.mark.asyncio
async def test_created_project_path_round_trips_through_web_endpoints(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "get_settings", lambda: SimpleNamespace(projects_dir=tmp_path))

    async def fake_run(self, raw_idea=None):
        # Preserve the initial state written by create_project; no LLM provider.
        return ProjectState.load(self.state_path)

    monkeypatch.setattr(api.Pipeline, "run", fake_run)
    transport = httpx.ASGITransport(app=api.app)
    project_id = None
    try:
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            created = await client.post("/api/projects", json={
                "raw_idea": "A mock video", "project_name": "Новый проект",
            })
            assert created.status_code == 200
            body = created.json()
            project_id = body["project_id"]
            assert body["project_dir"] == "Новый-проект"
            assert not Path(body["project_dir"]).is_absolute()

            prefix = f"/api/projects/{body['project_dir']}"
            response = await client.get(f"{prefix}/state")
            assert response.status_code == 200
            data = response.json()
            assert data["state"]["id"] == project_id
            assert data["state"]["current_step"] == 0
            assert data["steps"][2] == "select_concept"
            assert data["total_steps"] == 10

            selected = await client.post(f"/api/projects/{project_id}/select-concept", json={
                "concept_index": 0,
            })
            assert selected.status_code == 200
            assert api._concept_queues[project_id].get_nowait() == 0

            final_dir = tmp_path / body["project_dir"] / "final"
            final_dir.mkdir()
            (final_dir / "script.md").write_text("# Сценарий", encoding="utf-8")
            final = await client.get(f"{prefix}/final/script.md")
            assert final.status_code == 200
            assert final.json() == {"content": "# Сценарий"}
    finally:
        if project_id:
            task = api._running.pop(project_id, None)
            if task:
                await asyncio.gather(task)
            api._concept_queues.pop(project_id, None)


def test_shared_web_fixture_matches_backend_schema(tmp_path):
    fixture = Path(__file__).parent / "fixtures" / "web-project-state.json"
    data = json.loads(fixture.read_text(encoding="utf-8"))
    state = ProjectState.model_validate(data["state"])
    pipeline = api.Pipeline(tmp_path)
    assert data["steps"] == [step.name for step in pipeline.steps]
    assert data["total_steps"] == len(pipeline.steps)
    assert state.current_step == 2
    assert state.selected_concept_index is None
    assert len(state.concepts.concepts) == 3
