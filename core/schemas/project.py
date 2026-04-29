from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from pydantic import BaseModel, Field

from .brief import Brief
from .concept import Concepts
from .critique import Critique
from .production import EditNotes, ProductionNotes
from .scene import ScriptDraft
from .structure import StoryStructure


class ProjectState(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid4()))
    raw_idea: str = ""
    current_step: int = 0
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
        path.write_text(self.model_dump_json(indent=2))

    @classmethod
    def load(cls, path: str | Path) -> ProjectState:
        path = Path(path)
        return cls.model_validate_json(path.read_text())
