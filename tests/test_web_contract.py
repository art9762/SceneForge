"""Keep browser fixtures in sync with real, serialized API responses."""

import asyncio
import json
from pathlib import Path
from types import SimpleNamespace

import httpx
import pytest

import api.main as api
from core.pipeline import Pipeline
from core.schemas.project import ProjectState

SNAPSHOTS = json.loads(
    (Path(__file__).parents[1] / "web/tests/fixtures/project-states.json").read_text()
)


@pytest.mark.parametrize("name", SNAPSHOTS)
async def test_browser_fixture_matches_api(name, tmp_path, monkeypatch):
    snapshot = SNAPSHOTS[name]
    state = ProjectState.model_validate(snapshot["state"])
    state.save(tmp_path / name / "project.json")
    monkeypatch.setattr(api, "get_settings", lambda: SimpleNamespace(projects_dir=tmp_path))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url="http://test") as client:
        response = await client.get(f"/api/projects/{name}/state")
    assert response.status_code == 200
    assert response.json() == snapshot
    assert snapshot["steps"] == [step.name for step in Pipeline(tmp_path).steps]


async def test_concept_selection_uses_state_uuid_and_accepts_zero():
    project_id = SNAPSHOTS["waiting"]["state"]["id"]
    queue = asyncio.Queue()
    api._concept_queues[project_id] = queue
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url="http://test") as client:
            response = await client.post(f"/api/projects/{project_id}/select-concept", json={"concept_index": 0})
        assert response.status_code == 200
        assert queue.get_nowait() == 0
    finally:
        api._concept_queues.pop(project_id, None)
