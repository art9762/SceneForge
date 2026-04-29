from __future__ import annotations

from pydantic import BaseModel, Field

from .brief import Brief
from .scene import ScriptDraft


class CritiqueItem(BaseModel):
    area: str = ""
    issue: str = ""
    suggestion: str = ""


class CritiqueInput(BaseModel):
    brief: Brief
    draft: ScriptDraft


class Critique(BaseModel):
    overall_score: int = Field(default=5, ge=1, le=10)
    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[CritiqueItem] = Field(default_factory=list)
    suggestions: list[str] = Field(default_factory=list)
