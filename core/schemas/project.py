from __future__ import annotations

import os
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4
from typing import Literal

from pydantic import BaseModel, Field

from .brief import Brief
from .concept import Concepts
from .critique import Critique
from .production import EditNotes, ProductionNotes
from .scene import ScriptDraft
from .structure import StoryStructure


class PipelineRun(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    status: Literal['running', 'waiting_input', 'failed', 'interrupted', 'paused', 'completed'] = 'running'
    provider: str = 'claude'
    model: str | None = None
    step_name: str | None = None
    error: str | None = None
    error_type: str | None = None
    started_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    finished_at: datetime | None = None


class ProjectState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    raw_idea: str = ""
    current_step: int = 0
    run: PipelineRun | None = None
    brief: Brief | None = None
    concepts: Concepts | None = None
    selected_concept_index: int | None = None
    structure: StoryStructure | None = None
    draft_v1: ScriptDraft | None = None
    critique: Critique | None = None
    draft_v2: ScriptDraft | None = None
    production_notes: ProductionNotes | None = None
    edit_notes: EditNotes | None = None
    final_script: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def save(self, path: str | Path) -> None:
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=path.parent,
                                             delete=False) as handle:
                temporary = Path(handle.name)
                handle.write(self.model_dump_json(indent=2))
                handle.flush()
                os.fsync(handle.fileno())
            os.replace(temporary, path)
            directory = os.open(path.parent, os.O_RDONLY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)

    @classmethod
    def load(cls, path: str | Path) -> ProjectState:
        path = Path(path)
        return cls.model_validate_json(path.read_text())
