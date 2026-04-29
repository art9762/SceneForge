from __future__ import annotations

from pydantic import BaseModel, Field

from .brief import Brief
from .concept import Concept
from .structure import StoryStructure


class Scene(BaseModel):
    scene_number: int = 0
    title: str = ""
    video: str = ""
    voiceover: str = ""
    sound: str = ""
    edit_notes: str = ""
    duration_hint: str = ""
    notes: str = ""


class SceneInput(BaseModel):
    brief: Brief
    concept: Concept
    structure: StoryStructure


class ScriptDraft(BaseModel):
    scenes: list[Scene] = Field(default_factory=list)
