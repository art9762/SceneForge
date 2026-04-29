"""Shared fixtures for SceneForge tests."""

from __future__ import annotations

import pytest

from core.schemas.brief import Brief, BriefInput
from core.schemas.concept import Concept, Concepts, ConceptInput
from core.schemas.structure import StoryStructure, StructureSection, StructureInput
from core.schemas.scene import Scene, ScriptDraft, SceneInput
from core.schemas.critique import Critique, CritiqueItem, CritiqueInput
from core.schemas.production import (
    ProductionNotes, Shot, ProductionInput,
    EditNotes, PacingNote, BRollItem, EditInput,
)
from core.schemas.project import ProjectState


@pytest.fixture
def sample_brief() -> Brief:
    return Brief(
        title="Заброшенная советская обсерватория",
        format="документальный обзор",
        duration_minutes=8.0,
        target_audience="любители урбэкса 18-35 лет",
        tone="атмосферный, загадочный",
        style="визуальное эссе",
        platform="YouTube",
        goal="вызвать интерес к заброшенным местам",
        constraints=["без дрона — запрет на полёты"],
        keywords=["урбэкс", "заброшка", "обсерватория", "СССР"],
    )


@pytest.fixture
def sample_concept() -> Concept:
    return Concept(
        name="Глаз, который видел космос",
        direction="атмосферный",
        logline="Обсерватория, которая следила за звёздами — а теперь звёзды следят за ней.",
        synopsis="Камера проникает внутрь заброшенной обсерватории...",
        tone_description="тихий, медитативный с нарастающим напряжением",
        why_it_works="визуальный контраст руин и космических масштабов",
    )


@pytest.fixture
def sample_structure() -> StoryStructure:
    return StoryStructure(
        hook=StructureSection(title="Hook", description="Дрожащий луч фонарика в темноте", duration_hint="0:00-0:30"),
        setup=StructureSection(title="Setup", description="История обсерватории", duration_hint="0:30-1:30"),
        conflict=StructureSection(title="Conflict", description="Почему закрыли", duration_hint="1:30-3:00"),
        escalation=StructureSection(title="Escalation", description="Проникаем глубже", duration_hint="3:00-4:30"),
        midpoint=StructureSection(title="Midpoint", description="Находим телескоп", duration_hint="4:30-5:30"),
        climax=StructureSection(title="Climax", description="Телескоп ещё работает?", duration_hint="5:30-6:30"),
        resolution=StructureSection(title="Resolution", description="Тишина и звёзды", duration_hint="6:30-7:30"),
        cta=StructureSection(title="CTA", description="Подписка и следующий объект", duration_hint="7:30-8:00"),
    )


@pytest.fixture
def sample_draft() -> ScriptDraft:
    return ScriptDraft(scenes=[
        Scene(
            scene_number=1,
            title="Hook",
            video="Тёмный коридор, луч фонарика",
            voiceover="Здесь когда-то слушали космос.",
            sound="тишина, капли воды",
            edit_notes="быстрый монтаж, 3 кадра",
            duration_hint="30s",
        ),
        Scene(
            scene_number=2,
            title="История",
            video="Архивные фото обсерватории",
            voiceover="В 1967 году здесь установили крупнейший радиотелескоп.",
            sound="винтажная музыка",
            edit_notes="плавные переходы",
            duration_hint="60s",
        ),
    ])


@pytest.fixture
def sample_critique() -> Critique:
    return Critique(
        overall_score=7,
        strengths=["Сильный хук", "Атмосферные описания"],
        weaknesses=[
            CritiqueItem(area="пейсинг", issue="вторая сцена затянута", suggestion="сократить до 45 секунд"),
        ],
        suggestions=["Добавить больше звуковых деталей"],
    )


@pytest.fixture
def sample_project(sample_brief, sample_concept, sample_structure, sample_draft, sample_critique) -> ProjectState:
    return ProjectState(
        raw_idea="8-минутный YouTube-ролик про заброшенную советскую обсерваторию",
        brief=sample_brief,
        concepts=Concepts(concepts=[sample_concept]),
        selected_concept_index=0,
        structure=sample_structure,
        draft_v1=sample_draft,
        critique=sample_critique,
        draft_v2=sample_draft,
        current_step=10,
    )
