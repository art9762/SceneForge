"""Durable execution with fake agents and temporary projects only."""
import asyncio
import json
import select
import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import pytest
from typer.testing import CliRunner

import api.main as api
import cli.main as cli
import core.pipeline as engine
from core.pipeline import Pipeline, load_project_state
from core.schemas.brief import Brief
from core.schemas.concept import Concepts
from core.schemas.production import EditNotes, ProductionNotes
from core.schemas.project import PipelineRun, ProjectState
from core.storage import ProjectBusyError, ProjectLock


@pytest.fixture
def fake_agents(monkeypatch, sample_brief, sample_concept, sample_structure, sample_draft, sample_critique):
    control = SimpleNamespace(calls=[], fail=None, pause=None, entered=asyncio.Event(), release=asyncio.Event())
    outputs = {
        'BriefAgent': sample_brief, 'ConceptAgent': Concepts(concepts=[sample_concept] * 3),
        'StoryArchitect': sample_structure, 'SceneWriter': sample_draft, 'CriticAgent': sample_critique,
        'RewriteAgent': sample_draft, 'ProducerAgent': ProductionNotes(), 'EditorAgent': EditNotes(),
    }
    for name, output in outputs.items():
        def make_executor(agent_name, result):
            async def execute(_self, *_args, **_kwargs):
                control.calls.append(agent_name)
                if control.pause == agent_name:
                    control.entered.set()
                    await control.release.wait()
                await asyncio.sleep(0)
                if control.fail == agent_name:
                    raise RuntimeError('private-provider-response-fixture')
                return result.model_copy(deep=True)
            return execute
        monkeypatch.setattr(getattr(engine, name), 'run', make_executor(name, output))
    monkeypatch.setattr(Pipeline, '_get_provider', lambda self: object())
    return control


@pytest.fixture
async def client(tmp_path, monkeypatch, fake_agents):
    monkeypatch.setattr(api, 'get_settings', lambda: SimpleNamespace(projects_dir=tmp_path))
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url='http://test') as http:
        yield http
    tasks = list(api._running.values())
    for task in tasks:
        task.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
    await asyncio.sleep(0)
    assert not api._running
    assert not api._handles
    assert not api._concept_queues


async def saved_when(path, predicate):
    async with asyncio.timeout(4):
        while True:
            if path.exists():
                state = ProjectState.load(path)
                if predicate(state):
                    return state
            await asyncio.sleep(0.005)


async def create_waiting(client, tmp_path, **options):
    result = await client.post('/api/projects', json={'raw_idea': 'Fixture idea', 'project_name': 'fixture', **options})
    assert result.status_code == 200, result.text
    path = tmp_path / 'fixture' / 'project.json'
    state = await saved_when(path, lambda state: state.run.status == 'waiting_input')
    return path, state


async def choose(client, state, index=0):
    return await client.post(f'/api/projects/{state.id}/select-concept', json={'concept_index': index, 'run_id': state.run.id})


async def test_failure_is_persisted_and_retry_skips_committed_steps(client, tmp_path, fake_agents):
    fake_agents.fail = 'SceneWriter'
    path, waiting = await create_waiting(client, tmp_path, provider='openai', model='fixture-model')
    assert (await choose(client, waiting)).status_code == 200
    failed = await saved_when(path, lambda state: state.run.status == 'failed')
    assert failed.current_step == 4
    assert failed.run.step_name == 'draft_v1'
    assert failed.run.error_type == 'RuntimeError'
    assert failed.run.finished_at is not None
    assert 'private-provider-response' not in path.read_text()
    response = await client.get('/api/projects/fixture/state')
    assert response.json()['state']['run']['status'] == 'failed'
    fake_agents.fail = None
    result = await client.post('/api/projects/fixture/resume', json={})
    assert result.status_code == 200
    complete = await saved_when(path, lambda state: state.run.status == 'completed')
    assert complete.current_step == 10
    assert complete.id == failed.id
    assert complete.run.id != failed.run.id
    assert (complete.run.provider, complete.run.model) == ('openai', 'fixture-model')
    assert fake_agents.calls.count('BriefAgent') == 1
    assert fake_agents.calls.count('ConceptAgent') == 1
    assert fake_agents.calls.count('StoryArchitect') == 1
    assert fake_agents.calls.count('SceneWriter') == 2
    assert (path.parent / 'final/script.md').read_text()
    assert (await client.post('/api/projects/fixture/resume', json={})).status_code == 409


async def test_concurrent_starts_and_cli_cannot_share_a_project(client, tmp_path, fake_agents):
    fake_agents.pause = 'BriefAgent'
    requests = [client.post('/api/projects', json={'raw_idea': str(i), 'project_name': 'same'}) for i in range(2)]
    results = await asyncio.gather(*requests)
    assert sorted(response.status_code for response in results) == [200, 409]
    await asyncio.wait_for(fake_agents.entered.wait(), 2)
    path = tmp_path / 'same' / 'project.json'
    current = ProjectState.load(path)
    results = await asyncio.gather(*(client.post('/api/projects/same/resume', json={}) for _ in range(2)))
    assert all(response.status_code == 409 for response in results)
    result = subprocess.run([sys.executable, '-m', 'cli.main', 'resume', str(path.parent)],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 1
    assert 'уже выполняется' in result.stdout
    assert 'Traceback' not in result.stderr
    assert ProjectState.load(path).id == current.id
    assert fake_agents.calls == ['BriefAgent']


async def test_concurrent_resume_has_one_winner_and_preserves_legacy_data(client, tmp_path, fake_agents):
    path = tmp_path / 'legacy' / 'project.json'
    old = ProjectState(raw_idea='Saved legacy idea')
    old.save(path)
    raw = json.loads(path.read_text())
    raw.pop('run')
    path.write_text(json.dumps(raw))
    fake_agents.pause = 'BriefAgent'
    results = await asyncio.gather(*(client.post('/api/projects/legacy/resume', json={}) for _ in range(2)))
    assert sorted(response.status_code for response in results) == [200, 409]
    await asyncio.wait_for(fake_agents.entered.wait(), 2)
    assert ProjectState.load(path).raw_idea == old.raw_idea
    assert ProjectState.load(path).id == old.id
    assert fake_agents.calls == ['BriefAgent']


async def test_restart_detection_uses_the_os_lock_not_in_memory_tracking(client, tmp_path):
    directory = tmp_path / 'killed'
    code = '''
import sys
from pathlib import Path
from core.pipeline import Pipeline
handle = Pipeline(Path(sys.argv[1]), provider_name='openai', model='fixture').prepare_run('saved idea')
print('ready', flush=True)
sys.stdin.readline()
'''
    process = subprocess.Popen([sys.executable, '-c', code, str(directory)], stdin=subprocess.PIPE,
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try:
        assert select.select([process.stdout], [], [], 5)[0]
        assert process.stdout.readline() == b'ready\n'
        response = await client.get('/api/projects/killed/state')
        assert response.json()['state']['run']['status'] == 'running'
        assert (await client.post('/api/projects/killed/resume', json={})).status_code == 409
        process.kill()
        process.communicate(timeout=5)
        response = await client.get('/api/projects/killed/state')
        state = response.json()['state']
        assert state['run']['status'] == 'interrupted'
        assert state['current_step'] == 0
        assert state['run']['provider'] == 'openai'
        assert ProjectState.load(directory / 'project.json').run.status == 'interrupted'
        assert (await client.post('/api/projects/killed/resume', json={})).status_code == 200
        resumed = await saved_when(directory / 'project.json', lambda value: value.run.status == 'waiting_input')
        assert resumed.id == state['id']
    finally:
        if process.poll() is None:
            process.kill()
        process.communicate(timeout=5)


async def test_selection_is_validated_and_durable_before_runner_advances(client, tmp_path, fake_agents):
    path, waiting = await create_waiting(client, tmp_path)
    waiting.concepts.concepts = waiting.concepts.concepts[:1]
    waiting.save(path)
    invalid = await client.post(f'/api/projects/{waiting.id}/select-concept', json={'concept_index': 1, 'run_id': waiting.run.id})
    assert invalid.status_code == 422
    stale = await client.post(f'/api/projects/{waiting.id}/select-concept', json={'concept_index': 0, 'run_id': 'old-run'})
    assert stale.status_code == 409
    # This handler has no suspension point: cancel before the waiting runner
    # can consume its queue, simulating death after the decision commit.
    await api.select_concept(waiting.id, api.SelectConceptRequest(concept_index=0, run_id=waiting.run.id))
    with pytest.raises(api.HTTPException) as duplicate:
        await api.select_concept(waiting.id, api.SelectConceptRequest(concept_index=0))
    assert duplicate.value.status_code == 409
    task = api._running[waiting.id]
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    await asyncio.sleep(0)
    interrupted = ProjectState.load(path)
    assert interrupted.current_step == 2
    assert interrupted.selected_concept_index == 0
    assert interrupted.run.status == 'interrupted'
    assert not api._concept_queues
    assert (await client.post('/api/projects/fixture/resume', json={})).status_code == 200
    completed = await saved_when(path, lambda state: state.run.status == 'completed')
    assert completed.selected_concept_index == 0
    assert fake_agents.calls.count('ConceptAgent') == 1
    assert (await choose(client, waiting)).status_code == 409


async def test_cancel_before_first_task_instruction_releases_reservation(client, tmp_path):
    result = await api.create_project(api.CreateProjectRequest(raw_idea='fixture', project_name='never-started'))
    task = api._running[result['project_id']]
    task.cancel()
    await asyncio.gather(task, return_exceptions=True)
    await asyncio.sleep(0)
    path = tmp_path / 'never-started' / 'project.json'
    assert ProjectState.load(path).run.status == 'interrupted'
    with ProjectLock(path.parent):
        pass
    assert not api._running


async def test_api_shutdown_marks_live_work_interrupted(client, tmp_path, fake_agents):
    fake_agents.pause = 'BriefAgent'
    async with api.lifespan(api.app):
        response = await client.post('/api/projects', json={'raw_idea': 'fixture', 'project_name': 'shutdown'})
        assert response.status_code == 200
        await asyncio.wait_for(fake_agents.entered.wait(), 2)
    assert ProjectState.load(tmp_path / 'shutdown/project.json').run.status == 'interrupted'
    assert not api._running


async def test_existing_project_and_finished_state_are_never_overwritten(client, tmp_path, sample_project):
    path = tmp_path / 'saved/project.json'
    sample_project.save(path)
    original = path.read_bytes()
    response = await client.post('/api/projects', json={'raw_idea': 'replace', 'project_name': 'saved'})
    assert response.status_code == 409
    assert (await client.post('/api/projects/saved/resume', json={})).status_code == 409
    assert path.read_bytes() == original
    assert (await client.post('/api/projects/missing/resume', json={})).status_code == 404
    assert (await client.post('/api/projects/../../outside/resume', json={})).status_code != 200


def test_atomic_state_write_failure_keeps_previous_checkpoint(tmp_path):
    path = tmp_path / 'project.json'
    state = ProjectState(raw_idea='committed')
    state.save(path)
    original = path.read_bytes()
    state.raw_idea = 'uncommitted'
    with patch('core.schemas.project.os.replace', side_effect=OSError('fixture disk failure')):
        with pytest.raises(OSError):
            state.save(path)
    assert path.read_bytes() == original
    assert sorted(file.name for file in tmp_path.iterdir()) == ['project.json']


async def test_failure_discards_partial_unsaved_agent_mutations(tmp_path):
    pipeline = Pipeline(tmp_path)
    async def fail(state, _provider):
        state.brief = Brief(title='not committed')
        raise RuntimeError('fixture')
    pipeline.steps[0].execute = fail
    pipeline.steps[0].uses_llm = False
    with pytest.raises(RuntimeError):
        await pipeline.run('fixture')
    stored = ProjectState.load(tmp_path / 'project.json')
    assert stored.current_step == 0 and stored.brief is None
    assert stored.run.status == 'failed'


async def test_explicit_single_step_is_paused_and_remains_resumable(tmp_path, fake_agents):
    pipeline = Pipeline(tmp_path)
    partial = await pipeline.run_step(0, ProjectState(raw_idea='fixture'))
    assert partial.current_step == 1
    assert partial.run.status == 'paused'
    assert partial.run.finished_at is not None
    assert load_project_state(tmp_path).run.status == 'paused'
    # Core's default choice callback selects index zero; no completed step is repeated.
    complete = await pipeline.run()
    assert complete.current_step == 10 and complete.run.status == 'completed'
    assert fake_agents.calls.count('BriefAgent') == 1


def test_cli_assembly_resume_preserves_saved_provider_without_constructing_llm(tmp_path, sample_project, monkeypatch):
    sample_project.current_step = 9
    sample_project.run = PipelineRun(status='failed', provider='openai', model='fixture-model')
    sample_project.save(tmp_path / 'project.json')
    monkeypatch.setattr(Pipeline, '_get_provider', lambda self: pytest.fail('Assembly must not construct an LLM'))
    result = CliRunner().invoke(cli.app, ['resume', str(tmp_path)])
    assert result.exit_code == 0, result.output
    stored = ProjectState.load(tmp_path / 'project.json')
    assert stored.current_step == 10
    assert stored.run.status == 'completed'
    assert (stored.run.provider, stored.run.model) == ('openai', 'fixture-model')
    assert (tmp_path / 'final/script.md').is_file()


def test_cli_run_refuses_name_collision_and_status_reads_legacy(tmp_path, monkeypatch):
    monkeypatch.setattr(cli, 'get_settings', lambda: SimpleNamespace(projects_dir=tmp_path))
    path = tmp_path / 'saved/project.json'
    ProjectState(raw_idea='old').save(path)
    original = path.read_bytes()
    result = CliRunner().invoke(cli.app, ['run', 'new', '--name', 'saved'])
    assert result.exit_code == 1 and 'уже существует' in result.output
    assert path.read_bytes() == original
    result = CliRunner().invoke(cli.app, ['status', str(path.parent)])
    assert result.exit_code == 0
    assert path.read_bytes() == original
