# Модели данных

SceneForge использует Pydantic v2 модели из `core/schemas/`. Эти модели задают контракт между агентами, сохранённым состоянием проекта, тестами, API-ответами и финальной сборкой.

## ProjectState

Определён в `core/schemas/project.py`.

```text
id: str
raw_idea: str
current_step: int
brief: Brief | None
concepts: Concepts | None
selected_concept_index: int | None
structure: StoryStructure | None
draft_v1: ScriptDraft | None
critique: Critique | None
draft_v2: ScriptDraft | None
production_notes: ProductionNotes | None
edit_notes: EditNotes | None
final_script: str | None
created_at: datetime
updated_at: datetime
```

Методы:

- `save(path)` пишет `model_dump_json(indent=2)`.
- `load(path)` валидирует JSON и возвращает `ProjectState`.

## Brief

Input:

```text
BriefInput.raw_idea: str
```

Output:

```text
title: str
format: str
duration_minutes: float
target_audience: str
tone: str
style: str
platform: str
goal: str
constraints: list[str]
keywords: list[str]
```

Назначение: превратить сырую идею в конкретный продакшн-бриф.

## Concepts

Input:

```text
ConceptInput.brief: Brief
```

Один concept:

```text
name: str
direction: str
logline: str
synopsis: str
tone_description: str
why_it_works: str
```

Output:

```text
Concepts.concepts: list[Concept]
```

`ConceptAgent` промптом просит сгенерировать ровно три концепции.

## StoryStructure

Input:

```text
StructureInput.brief: Brief
StructureInput.concept: Concept
```

Каждая секция — `StructureSection`:

```text
title: str
description: str
duration_hint: str
notes: str
```

Секции `StoryStructure`:

```text
hook
setup
conflict
escalation
midpoint
climax
resolution
cta
```

## ScriptDraft

Input:

```text
SceneInput.brief: Brief
SceneInput.concept: Concept
SceneInput.structure: StoryStructure
```

Scene:

```text
scene_number: int
title: str
video: str
voiceover: str
sound: str
edit_notes: str
duration_hint: str
notes: str
```

Draft:

```text
ScriptDraft.scenes: list[Scene]
```

Промпт сценариста ожидает, что каждая сцена будет соответствовать блокам `[VIDEO]`, `[VOICEOVER]`, `[SOUND]`, `[EDIT]`.

## Critique

Input:

```text
CritiqueInput.brief: Brief
CritiqueInput.draft: ScriptDraft
```

Critique item:

```text
area: str
issue: str
suggestion: str
```

Output:

```text
overall_score: int  # 1 <= score <= 10
strengths: list[str]
weaknesses: list[CritiqueItem]
suggestions: list[str]
```

## RewriteInput

Определён в `core/agents/rewriter.py`, а не в `core/schemas/`.

```text
brief: Brief
draft: ScriptDraft
critique: Critique
```

Output — новый `ScriptDraft`, который сохраняется как `draft_v2`.

## ProductionNotes

Input:

```text
ProductionInput.brief: Brief
ProductionInput.draft: ScriptDraft
```

Shot:

```text
scene_number: int
shot_type: str
description: str
notes: str
```

Output:

```text
shot_list: list[Shot]
locations: list[str]
props: list[str]
archive_footage: list[str]
graphics: list[str]
challenges: list[str]
```

## EditNotes

Input:

```text
EditInput.brief: Brief
EditInput.draft: ScriptDraft
```

Pacing note:

```text
scene: int
note: str
```

B-roll item:

```text
timestamp_hint: str
description: str
source_suggestion: str
```

Output:

```text
pacing_notes: list[PacingNote]
broll_suggestions: list[BRollItem]
music_notes: str
sound_design: list[str]
transitions: list[str]
```

## Модели финальной сборки

Определены в `core/agents/assembler.py`.

```text
AssemblerInput.project: ProjectState
```

```text
AssemblerOutput.script_markdown: str
AssemblerOutput.teleprompter_text: str
```

`FinalAssembler` использует `draft_v2`, если он есть, иначе берёт `draft_v1`.

## Важные имена полей

Эти имена важны для API- и frontend-клиентов:

- Название концепции хранится в `name`, не в `title`.
- Оценка критики хранится в `overall_score`, не в `score`.
- Выбранная концепция хранится как `selected_concept_index`, не как объект `selected_concept`.
- API возвращает `ProjectState` JSON внутри ключа `state`.
