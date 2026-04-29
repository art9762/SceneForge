from __future__ import annotations

from pydantic import BaseModel, Field

from .brief import Brief
from .scene import ScriptDraft


class Shot(BaseModel):
    scene_number: int = 0
    shot_type: str = ""
    description: str = ""
    notes: str = ""


class ProductionInput(BaseModel):
    brief: Brief
    draft: ScriptDraft


class ProductionNotes(BaseModel):
    shot_list: list[Shot] = Field(default_factory=list)
    locations: list[str] = Field(default_factory=list)
    props: list[str] = Field(default_factory=list)
    archive_footage: list[str] = Field(default_factory=list)
    graphics: list[str] = Field(default_factory=list)
    challenges: list[str] = Field(default_factory=list)


class PacingNote(BaseModel):
    scene: int = 0
    note: str = ""


class BRollItem(BaseModel):
    timestamp_hint: str = ""
    description: str = ""
    source_suggestion: str = ""


class EditInput(BaseModel):
    brief: Brief
    draft: ScriptDraft


class EditNotes(BaseModel):
    pacing_notes: list[PacingNote] = Field(default_factory=list)
    broll_suggestions: list[BRollItem] = Field(default_factory=list)
    music_notes: str = ""
    sound_design: list[str] = Field(default_factory=list)
    transitions: list[str] = Field(default_factory=list)
