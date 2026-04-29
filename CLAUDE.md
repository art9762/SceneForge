# SceneForge

> AI writers' room — мультиагентный пайплайн для разработки сценариев видео.

## Что это

SceneForge принимает сырую идею (например: «8-минутный YouTube-ролик про заброшенную советскую обсерваторию») и проводит её через цепочку из 9 специализированных AI-агентов, имитируя настоящую сценарную комнату. На выходе — полный сценарный пакет: бриф, структура, сценарий по сценам, критика, переписанный черновик, шот-лист, монтажные заметки и текст для телесуфлёра.

---

## Быстрый старт

### Установка

```bash
cd /Users/artem/Documents/SceneForge

# Python-окружение
python -m venv .venv
source .venv/bin/activate
pip install -e .

# Настроить ключи
cp .env.example .env
# Отредактировать .env — вписать TRINITY_CLAUDE_API_KEY и TRINITY_OPENAI_API_KEY
```

### CLI

```bash
# Полный прогон
sceneforge run "8-минутный YouTube-ролик про заброшенную советскую обсерваторию"

# С параметрами
sceneforge run "идея" --name my-project --provider openai --model gpt-5.4

# Продолжить незавершённый проект
sceneforge resume projects/my-project

# Посмотреть статус
sceneforge status projects/my-project
```

### Web UI

```bash
# Терминал 1 — API
python -m api.main

# Терминал 2 — фронтенд
cd web && npm install && npm run dev
```

Открыть http://localhost:3000.

---

## Архитектура

```
SceneForge/
├── core/                    # Ядро — не зависит от интерфейса
│   ├── agents/              # 9 агентов пайплайна
│   │   ├── base.py          # BaseAgent — абстрактный базовый класс
│   │   ├── brief.py         # BriefAgent — сырая идея → структурированный бриф
│   │   ├── concept.py       # ConceptAgent — бриф → 3 креативных направления
│   │   ├── architect.py     # StoryArchitect — бриф + концепция → драматургическая структура
│   │   ├── writer.py        # SceneWriter — структура → первый черновик по сценам
│   │   ├── critic.py        # CriticAgent — черновик → критика с оценкой 1-10
│   │   ├── rewriter.py      # RewriteAgent — черновик + критика → улучшенный черновик
│   │   ├── producer.py      # ProducerAgent — черновик → шот-лист, локации, реквизит
│   │   ├── editor.py        # EditorAgent — черновик → монтажные заметки
│   │   └── assembler.py     # FinalAssembler — сборка всего в markdown (без LLM)
│   ├── schemas/             # Pydantic v2 модели данных
│   │   ├── brief.py         # BriefInput, Brief
│   │   ├── concept.py       # Concept, ConceptInput, Concepts
│   │   ├── structure.py     # StructureSection, StructureInput, StoryStructure
│   │   ├── scene.py         # Scene, SceneInput, ScriptDraft
│   │   ├── critique.py      # CritiqueItem, CritiqueInput, Critique
│   │   ├── production.py    # Shot, ProductionNotes, PacingNote, BRollItem, EditNotes
│   │   └── project.py       # ProjectState — весь стейт проекта
│   ├── llm/                 # LLM-провайдеры
│   │   ├── provider.py      # LLMProvider (ABC) + get_provider() фабрика
│   │   ├── claude.py        # ClaudeProvider — anthropic SDK → Trinity aurora/v1
│   │   └── openai_provider.py  # OpenAIProvider — openai SDK → Trinity orion/v1
│   ├── pipeline.py          # Pipeline — движок пайплайна (10 шагов)
│   └── config.py            # Settings — pydantic-settings из .env
├── cli/
│   └── main.py              # Typer CLI: run, resume, status
├── api/
│   └── main.py              # FastAPI: REST API для web UI
├── web/                     # Next.js фронтенд (TypeScript, Tailwind, App Router)
│   ├── lib/api.ts           # Fetch-обёртка для API
│   ├── app/page.tsx         # Главная — ввод идеи
│   └── app/project/[...path]/page.tsx  # Страница проекта — прогресс, выбор концепции
├── projects/                # Сохранённые проекты (в .gitignore)
├── pyproject.toml           # Python-зависимости и entrypoint
├── .env.example             # Шаблон переменных окружения
└── .gitignore
```

---

## Пайплайн: 10 шагов

```
Raw Idea
  │
  ▼
┌─────────────────┐
│  1. BriefAgent  │  Сырая идея → Brief (формат, аудитория, тон, платформа, цель)
└────────┬────────┘
         ▼
┌─────────────────┐
│ 2. ConceptAgent │  Brief → 3 концепции (безопасная, смелая, экспериментальная)
└────────┬────────┘
         ▼
┌─────────────────┐
│ 3. User Choice  │  Пользователь выбирает одну из трёх концепций (интерактивный шаг)
└────────┬────────┘
         ▼
┌─────────────────┐
│ 4. StoryArchitect│  Brief + Concept → StoryStructure (hook→setup→conflict→...→CTA)
└────────┬────────┘
         ▼
┌─────────────────┐
│  5. SceneWriter │  Brief + Concept + Structure → ScriptDraft v1 ([VIDEO]/[VO]/[SOUND]/[EDIT])
└────────┬────────┘
         ▼
┌─────────────────┐
│  6. CriticAgent │  Brief + Draft v1 → Critique (оценка 1-10, сильные/слабые стороны)
└────────┬────────┘
         ▼
┌─────────────────┐
│ 7. RewriteAgent │  Brief + Draft v1 + Critique → ScriptDraft v2
└────────┬────────┘
         ▼
┌─────────────────┐
│ 8. ProducerAgent│  Brief + Draft v2 → ProductionNotes (шот-лист, локации, реквизит, архивы)
└────────┬────────┘
         ▼
┌─────────────────┐
│  9. EditorAgent │  Brief + Draft v2 → EditNotes (пейсинг, б-ролл, музыка, звук, переходы)
└────────┬────────┘
         ▼
┌──────────────────┐
│ 10. FinalAssembler│  Всё → script.md + teleprompter.md (без LLM, чистая сборка)
└──────────────────┘
```

После каждого шага состояние сохраняется в `projects/<name>/project.json`. Можно перезапустить с любого шага командой `sceneforge resume`.

---

## Ключевые модели данных

### Brief (бриф)
```
title, format, duration_minutes, target_audience, tone, style,
platform, goal, constraints[], keywords[]
```

### Concept (концепция)
```
name, direction, logline, synopsis, tone_description, why_it_works
```

### StoryStructure (структура)
8 секций: hook, setup, conflict, escalation, midpoint, climax, resolution, cta  
Каждая секция: title, description, duration_hint, notes

### Scene (сцена)
```
scene_number, title, video, voiceover, sound, edit_notes, duration_hint, notes
```

### Critique (критика)
```
overall_score (1-10), strengths[], weaknesses[{area, issue, suggestion}], suggestions[]
```

### ProductionNotes
```
shot_list[{scene_number, shot_type, description, notes}],
locations[], props[], archive_footage[], graphics[], challenges[]
```

### EditNotes
```
pacing_notes[{scene, note}], broll_suggestions[{timestamp_hint, description, source_suggestion}],
music_notes, sound_design[], transitions[]
```

### ProjectState
Содержит все вышеперечисленные модели + raw_idea, current_step, id, timestamps.  
Методы: `save(path)`, `load(path)`.

---

## LLM-провайдеры

Два провайдера через Trinity proxy:

| Провайдер | SDK | Base URL | Модель по умолчанию |
|-----------|-----|----------|---------------------|
| `claude` | `anthropic` | `https://gate.trinity.tg/aurora/v1` | `claude-sonnet-4-6` |
| `openai` | `openai` | `https://gate.trinity.tg/orion/v1` | `gpt-5.4` |

Абстракция `LLMProvider`:
- `generate(system, messages, model, temperature)` → `str`
- `generate_structured(system, messages, model, schema)` → `BaseModel` — добавляет JSON-схему в system prompt, парсит ответ в Pydantic-модель

Каждый агент использует `generate_structured` для получения типизированного вывода.

---

## API endpoints (FastAPI)

| Метод | Путь | Описание |
|-------|------|----------|
| POST | `/api/projects` | Создать проект и запустить пайплайн в фоне |
| GET | `/api/projects/{dir}/state` | Получить текущее состояние проекта |
| POST | `/api/projects/{id}/select-concept` | Выбрать концепцию (для интерактивного шага) |
| GET | `/api/projects/{dir}/final/{file}` | Скачать финальный файл |

---

## Переменные окружения (.env)

```
TRINITY_CLAUDE_API_KEY=...       # API-ключ для Claude через Trinity
TRINITY_OPENAI_API_KEY=...       # API-ключ для ChatGPT через Trinity
TRINITY_CLAUDE_BASE_URL=https://gate.trinity.tg/aurora/v1
TRINITY_OPENAI_BASE_URL=https://gate.trinity.tg/orion/v1
DEFAULT_CLAUDE_MODEL=claude-sonnet-4-6
DEFAULT_OPENAI_MODEL=gpt-5.4
PROJECTS_DIR=projects
```

---

## Как добавить нового агента

1. Создать Pydantic-схему в `core/schemas/` (input + output модели)
2. Создать агента в `core/agents/`:
   ```python
   class MyAgent(BaseAgent):
       name = "my_agent"
       description = "..."
       system_prompt = "..."           # Детальный промпт на русском
       input_schema = MyInput
       output_schema = MyOutput
       default_provider = "claude"     # или "openai"
   ```
3. Зарегистрировать в `core/agents/__init__.py`
4. Добавить шаг в `Pipeline._build_steps()` в `core/pipeline.py`
5. Добавить поле в `ProjectState` в `core/schemas/project.py`

---

## Как работает BaseAgent

```python
class BaseAgent(ABC):
    # ClassVar поля: name, description, system_prompt, input/output_schema, default_provider/model
    
    async def run(self, input_data, provider=None, model=None) -> BaseModel:
        # 1. Если provider не передан — создаёт из default_provider
        # 2. Конвертирует input_data в user message через build_user_message()
        # 3. Вызывает provider.generate_structured(system_prompt, messages, model, output_schema)
        # 4. Возвращает валидированную Pydantic-модель
    
    def build_user_message(self, input_data) -> str:
        # По умолчанию: input_data.model_dump_json(indent=2)
        # Можно переопределить для кастомного форматирования (как в RewriteAgent)
```

---

## Дальнейшая разработка (TODO)

### Приоритет 1 — Стабилизация MVP
- [ ] Добавить обработку ошибок LLM (retry с экспоненциальным backoff)
- [ ] Добавить логирование (structlog или loguru) — каждый шаг пайплайна, время выполнения, модель
- [ ] Валидация .env при старте (если ключи не заданы — понятная ошибка)
- [ ] Добавить `--debug` флаг в CLI для вывода промптов и raw-ответов LLM
- [ ] Тесты: unit-тесты для schemas (валидация), mock-тесты для агентов

### Приоритет 2 — Новые агенты
- [ ] **ResearchAgent** — опциональный, собирает фактическую базу (веб-поиск или RAG)
- [ ] **VoiceStyleAgent** — переписывает текст в заданном авторском стиле, убирает AI-клише
- [ ] **ConflictStakesAgent** — усиливает напряжение, ищет провисания, добавляет интригу

### Приоритет 3 — Model Debate
- [ ] Настройка разных моделей для разных агентов в конфиге:
  ```json
  {
    "writer": {"provider": "claude", "model": "claude-sonnet-4-6"},
    "critic": {"provider": "openai", "model": "gpt-5.4"}
  }
  ```
- [ ] Claude пишет → ChatGPT критикует → Claude переписывает
- [ ] Конфигурируемые пары debate для любого шага

### Приоритет 4 — Режимы проекта
- [ ] `youtube_documentary` (текущий), `short_film`, `commercial`, `tiktok_reels`, `cinematic_vlog`, `explainer`, `custom`
- [ ] Режим определяет: system prompts, длительности, структурные шаблоны
- [ ] Хранить шаблоны режимов в `core/modes/`

### Приоритет 5 — Расширенные функции
- [ ] Интерактивный перезапуск отдельного шага: `sceneforge rerun projects/X --step 5`
- [ ] Сравнение draft_v1 и draft_v2 (diff-view)
- [ ] Экспорт в PDF, Google Docs, Fountain (.fountain)
- [ ] История версий внутри проекта (draft_v3, draft_v4...)
- [ ] Streaming: отображение генерации в реальном времени
- [ ] WebSocket вместо polling в web UI
- [ ] Аутентификация и multi-user в web UI
- [ ] Хранение проектов в БД (SQLite / PostgreSQL) вместо файлов

### Приоритет 6 — Дополнительные выходные артефакты
- [ ] Варианты названий видео (5-10 вариантов)
- [ ] Идеи для thumbnail (описание + промпт для генерации картинки)
- [ ] YouTube description + теги
- [ ] Chapters/timestamps для YouTube
- [ ] Social media тизер (для анонса в Telegram/Twitter)

---

## Известные ограничения

1. **Нет retry-логики** — если LLM вернёт невалидный JSON, пайплайн упадёт
2. **Web UI polling** — каждые 3 секунды; лучше переделать на WebSocket
3. **Один режим** — пока только youtube_documentary; промпты заточены под него
4. **Нет streaming** — каждый шаг ждёт полный ответ, может занимать 30-60 секунд
5. **select-concept в web** — использует asyncio.Queue, работает только если API и пайплайн в одном процессе
6. **Нет тестов** — нужно добавить как минимум тесты для схем и pipeline
