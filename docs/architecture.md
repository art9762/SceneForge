# Архитектура

SceneForge построен вокруг небольшого Python-ядра, которое не зависит от CLI, API и Web UI. Все интерфейсы вызывают один и тот же `Pipeline` и сохраняют одно и то же состояние `ProjectState`.

## Структура репозитория

```text
SceneForge/
├── api/
│   └── main.py                 # FastAPI-бэкенд.
├── cli/
│   └── main.py                 # Typer CLI.
├── core/
│   ├── agents/                 # Агенты пайплайна.
│   ├── llm/                    # Абстракция провайдеров и retry.
│   ├── schemas/                # Pydantic-модели.
│   ├── config.py               # pydantic-settings конфигурация.
│   └── pipeline.py             # Оркестрация пайплайна.
├── docs/                       # Документация проекта.
├── projects/                   # Локальные сгенерированные проекты, игнорируются git.
├── tests/                      # Pytest-набор.
├── web/                        # Next.js frontend-прототип.
├── CLAUDE.md                   # Исходные заметки и roadmap.
└── pyproject.toml              # Python-зависимости и CLI entrypoint.
```

## Основной поток

Пайплайн состоит из 10 шагов:

```text
raw idea
  -> brief
  -> concepts
  -> select_concept
  -> structure
  -> draft_v1
  -> critique
  -> draft_v2
  -> production
  -> edit_notes
  -> assemble
```

Список шагов определён в `Pipeline._build_steps()` в `core/pipeline.py`.

| Шаг | Агент или действие | Поле результата |
| ---: | --- | --- |
| 1 | `BriefAgent` | `brief` |
| 2 | `ConceptAgent` | `concepts` |
| 3 | Интерактивный callback | `selected_concept_index` |
| 4 | `StoryArchitect` | `structure` |
| 5 | `SceneWriter` | `draft_v1` |
| 6 | `CriticAgent` | `critique` |
| 7 | `RewriteAgent` | `draft_v2` |
| 8 | `ProducerAgent` | `production_notes` |
| 9 | `EditorAgent` | `edit_notes` |
| 10 | `FinalAssembler` | `final_script`, `final/script.md`, `final/teleprompter.md` |

## Сохранение состояния

`ProjectState` из `core/schemas/project.py` — единый источник правды.

Каждый шаг:

1. Загружает или получает текущее состояние.
2. Выполняет текущий шаг пайплайна.
3. Увеличивает `current_step`.
4. Обновляет `updated_at`.
5. Сохраняет `project.json`.

Благодаря этому проект можно продолжить. Если `project.json` уже существует, `Pipeline.run()` стартует с `current_step`.

## Контракт агента

Все LLM-агенты наследуются от `BaseAgent`.

Каждый агент объявляет:

- `name`.
- `description`.
- `system_prompt`.
- `input_schema`.
- `output_schema`.
- `default_provider`.
- `default_model`.

`BaseAgent.run()`:

1. Определяет провайдера и модель.
2. Конвертирует input-модель в user message.
3. Вызывает `provider.generate_structured()`.
4. Валидирует ответ в output Pydantic-модель.
5. Логирует время и debug-фрагменты.

`RewriteAgent` переопределяет `build_user_message()`, чтобы передать бриф, первый драфт и критику отдельными секциями.

`FinalAssembler` переопределяет `run()` и не вызывает LLM. Он локально собирает Markdown и текст для телесуфлёра.

## LLM-провайдеры

Провайдеры реализуют `LLMProvider` из `core/llm/provider.py`.

| Имя | Класс | SDK | Base URL по умолчанию | Модель по умолчанию |
| --- | --- | --- | --- | --- |
| `claude` | `ClaudeProvider` | `anthropic` | `https://gate.trinity.tg/aurora/v1` | `claude-sonnet-4-6` |
| `openai` | `OpenAIProvider` | `openai` | `https://gate.trinity.tg/orion/v1` | `gpt-5.4` |

`get_provider(name)` проверяет ключ выбранного провайдера перед созданием клиента.

## Структурированный вывод

`LLMProvider.generate_structured()` добавляет JSON Schema output-модели в system prompt и просит модель вернуть только raw JSON.

Обработка включает:

- Удаление случайных Markdown code fences.
- Pydantic-валидацию.
- До 3 попыток при ошибке JSON parsing/validation.

Сетевые и провайдерские сбои отдельно ретраятся через `retry_async()`.

## Retry

`core/llm/retry.py` повторяет запросы при:

- `TimeoutError`.
- `ConnectionError`.
- `OSError`.
- HTTP/status `429`.
- HTTP/status `5xx`.

Значения по умолчанию:

- `max_retries=3`, то есть до 4 попыток всего.
- `base_delay=1.0`.
- `max_delay=30.0`.
- jitter до 25% текущей задержки.

Не ретраятся неретраибельные client errors, например неправильная авторизация или bad request.

## Интерфейсы

### CLI

`cli/main.py` предоставляет:

- `run`.
- `resume`.
- `status`.

Выбор концепции в CLI реализован через `rich.prompt.IntPrompt`.

### API

`api/main.py` предоставляет создание проекта, чтение состояния, выбор концепции и чтение финальных файлов. Фоновые пайплайны хранятся в памяти как `asyncio.Task`.

Выбор концепции в API-режиме использует in-memory `asyncio.Queue`, привязанную к UUID проекта.

### Web

Фронтенд — Next.js-приложение в `web/`.

Ключевые файлы:

- `web/app/page.tsx` — форма создания проекта.
- `web/app/project/[...path]/page.tsx` — страница проекта.
- `web/lib/api.ts` — fetch-обёртка для FastAPI.

Текущая страница проекта ожидает более богатую форму ответа API, чем бэкенд возвращает сейчас. До исправления контракта Web UI следует считать прототипом.

## Известные архитектурные ограничения

- Проекты хранятся в файловой системе, не в БД.
- API background tasks и очереди выбора концепции живут только в одном процессе.
- Streaming отсутствует: каждый шаг ждёт полный ответ LLM.
- Нет per-agent маршрутизации провайдеров/моделей.
- Сейчас есть один режим, заточенный под YouTube/documentary-видео.
- Web UI использует polling, не WebSocket.
