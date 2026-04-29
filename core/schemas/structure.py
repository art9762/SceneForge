from __future__ import annotations

from pydantic import BaseModel

from .brief import Brief
from .concept import Concept


class StructureSection(BaseModel):
    title: str = ""
    description: str = ""
    duration_hint: str = ""
    notes: str = ""


class StructureInput(BaseModel):
    brief: Brief
    concept: Concept


class StoryStructure(BaseModel):
    hook: StructureSection = StructureSection()
    setup: StructureSection = StructureSection()
    conflict: StructureSection = StructureSection()
    escalation: StructureSection = StructureSection()
    midpoint: StructureSection = StructureSection()
    climax: StructureSection = StructureSection()
    resolution: StructureSection = StructureSection()
    cta: StructureSection = StructureSection()
