"""Unit tests for Pydantic schemas."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest
from pydantic import ValidationError

from core.schemas.brief import Brief, BriefInput
from core.schemas.concept import Concept, Concepts, ConceptInput
from core.schemas.structure import StoryStructure, StructureSection
from core.schemas.scene import Scene, ScriptDraft
from core.schemas.critique import Critique, CritiqueItem
from core.schemas.production import ProductionNotes, Shot, EditNotes, PacingNote, BRollItem
from core.schemas.project import ProjectState


class TestBrief:
    def test_defaults(self):
        b = Brief()
        assert b.title == ""
        assert b.constraints == []
        assert b.keywords == []

    def test_full(self, sample_brief):
        assert sample_brief.title == "Заброшенная советская обсерватория"
        assert sample_brief.duration_minutes == 8.0
        assert len(sample_brief.keywords) == 4

    def test_json_roundtrip(self, sample_brief):
        data = sample_brief.model_dump_json()
        restored = Brief.model_validate_json(data)
        assert restored == sample_brief


class TestConcept:
    def test_concepts_list(self, sample_concept):
        cs = Concepts(concepts=[sample_concept, sample_concept])
        assert len(cs.concepts) == 2

    def test_empty_concepts(self):
        cs = Concepts()
        assert cs.concepts == []


class TestStructure:
    def test_defaults(self):
        s = StoryStructure()
        assert s.hook.title == ""
        assert s.cta.description == ""

    def test_all_sections(self, sample_structure):
        sections = ["hook", "setup", "conflict", "escalation", "midpoint", "climax", "resolution", "cta"]
        for name in sections:
            section = getattr(sample_structure, name)
            assert section.title != ""


class TestScene:
    def test_scene_fields(self):
        s = Scene(scene_number=1, title="Test", video="v", voiceover="vo")
        assert s.scene_number == 1
        assert s.sound == ""

    def test_script_draft(self, sample_draft):
        assert len(sample_draft.scenes) == 2
        assert sample_draft.scenes[0].scene_number == 1


class TestCritique:
    def test_score_bounds(self):
        c = Critique(overall_score=10)
        assert c.overall_score == 10

    def test_score_too_high(self):
        with pytest.raises(ValidationError):
            Critique(overall_score=11)

    def test_score_too_low(self):
        with pytest.raises(ValidationError):
            Critique(overall_score=0)


class TestProduction:
    def test_shot(self):
        s = Shot(scene_number=1, shot_type="крупный", description="лицо героя")
        assert s.shot_type == "крупный"

    def test_production_notes_empty(self):
        pn = ProductionNotes()
        assert pn.shot_list == []
        assert pn.locations == []

    def test_edit_notes(self):
        en = EditNotes(
            pacing_notes=[PacingNote(scene=1, note="ускорить")],
            music_notes="ambient",
        )
        assert len(en.pacing_notes) == 1


class TestProjectState:
    def test_save_load_roundtrip(self, sample_project):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "project.json"
            sample_project.save(path)

            loaded = ProjectState.load(path)
            assert loaded.raw_idea == sample_project.raw_idea
            assert loaded.brief.title == sample_project.brief.title
            assert loaded.current_step == 10
            assert loaded.critique.overall_score == 7
            assert len(loaded.draft_v1.scenes) == 2

    def test_defaults(self):
        ps = ProjectState()
        assert ps.raw_idea == ""
        assert ps.current_step == 0
        assert ps.brief is None
        assert ps.id  # UUID should be auto-generated

    def test_id_unique(self):
        a = ProjectState()
        b = ProjectState()
        assert a.id != b.id
