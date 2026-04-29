from __future__ import annotations

from pydantic import BaseModel, Field

from .brief import Brief


class Concept(BaseModel):
    name: str = ""
    direction: str = ""
    logline: str = ""
    synopsis: str = ""
    tone_description: str = ""
    why_it_works: str = ""


class ConceptInput(BaseModel):
    brief: Brief


class Concepts(BaseModel):
    concepts: list[Concept] = Field(default_factory=list)
