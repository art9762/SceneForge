from __future__ import annotations

from pydantic import BaseModel, Field


class BriefInput(BaseModel):
    raw_idea: str


class Brief(BaseModel):
    title: str = ""
    format: str = ""
    duration_minutes: float = 0.0
    target_audience: str = ""
    tone: str = ""
    style: str = ""
    platform: str = ""
    goal: str = ""
    constraints: list[str] = Field(default_factory=list)
    keywords: list[str] = Field(default_factory=list)
