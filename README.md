# SceneForge

SceneForge — AI writers' room для разработки сценариев видео. Проект принимает сырую идею и проводит её через типизированный, возобновляемый мультиагентный пайплайн: от брифа и концепций до финального сценария, продакшн-заметок и текста для телесуфлёра.

Основной рабочий интерфейс сейчас — Python CLI. FastAPI-бэкенд можно использовать напрямую. Next.js Web UI уже есть, но пока остаётся прототипом: страница проекта требует синхронизации контракта с текущим API.

## Что генерирует SceneForge

Для каждого проекта создаются:

- Структурированный бриф.
- Три альтернативные креативные концепции.
- Выбранная концепция.
- Драматургическая структура видео.
- Первый посценный черновик.
- Критика с оценкой, слабостями и рекомендациями.
- Улучшенный второй черновик.
- Продакшн-заметки: шот-лист, локации, реквизит, архивы, графика, сложности.
- Монтажные заметки: пейсинг, B-roll, музыка, саунд-дизайн, переходы.
- Финальные файлы в `projects/<name>/final/`:
  - `script.md` — полный сценарный пакет.
  - `teleprompter.md` — чистый текст voiceover для озвучки.

## Требования

- Python `>=3.12`.
- Node.js и npm для опционального Web UI.
- API-ключ хотя бы одного провайдера:
  - `TRINITY_CLAUDE_API_KEY` для `--provider claude`.
  - `TRINITY_OPENAI_API_KEY` для `--provider openai`.

Python-зависимости описаны в `pyproject.toml`: `anthropic`, `openai`, `pydantic`, `pydantic-settings`, `typer`, `fastapi`, `uvicorn`, `python-dotenv`, `rich`, `loguru`.

## Установка

Из корня репозитория:

```bash
cd /Users/artem/Documents/SceneForge

python3 -m venv .venv
source .venv/bin/activate

python3 -m pip install -e .
python3 -m pip install -e ".[dev]"
```

Создать локальный конфиг:

```bash
cp .env.example .env
```

Отредактировать `.env` и добавить ключ выбранного провайдера:

```dotenv
TRINITY_CLAUDE_API_KEY=your-claude-key
TRINITY_OPENAI_API_KEY=your-openai-key
TRINITY_CLAUDE_BASE_URL=https://gate.trinity.tg/aurora/v1
TRINITY_OPENAI_BASE_URL=https://gate.trinity.tg/orion/v1
```

Дополнительные переменные, которые поддерживает `core/config.py`:

```dotenv
DEFAULT_CLAUDE_MODEL=claude-sonnet-4-6
DEFAULT_OPENAI_MODEL=gpt-5.4
PROJECTS_DIR=projects
```

Валидируется только выбранный провайдер. Например, для `--provider claude` нужен только `TRINITY_CLAUDE_API_KEY`.

## CLI

Запустить новый проект:

```bash
sceneforge run "8-минутный YouTube-ролик про заброшенную советскую обсерваторию"
```

Запустить с явным именем папки и провайдером:

```bash
sceneforge run "идея видео" --name my-project --provider openai --model gpt-5.4
```

Включить debug-режим:

```bash
sceneforge run "идея видео" --debug
```

Продолжить незавершённый проект:

```bash
sceneforge resume projects/my-project
```

Показать статус:

```bash
sceneforge status projects/my-project
```

Команды и опции:

| Команда / опция | Назначение |
| --- | --- |
| `sceneforge run IDEA` | Создать или продолжить проект и пройти пайплайн. |
| `sceneforge resume PROJECT_PATH` | Продолжить проект из папки с `project.json`. |
| `sceneforge status PROJECT_PATH` | Показать сохранённый прогресс. |
| `--name`, `-n` | Имя папки проекта для `run`. |
| `--provider`, `-p` | `claude` или `openai`; по умолчанию `claude`. |
| `--model`, `-m` | Переопределить модель провайдера. |
| `--debug`, `-d` | Логировать фрагменты промптов и структурированных ответов. |

На шаге выбора концепции CLI показывает три карточки и просит выбрать номер.

## API

Запустить бэкенд:

```bash
python3 -m api.main
```

API слушает `http://localhost:8000` и разрешает CORS с `http://localhost:3000`.

Создать проект:

```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "raw_idea": "8-минутный YouTube-ролик про заброшенную советскую обсерваторию",
    "project_name": "observatory",
    "provider": "claude"
  }'
```

Получить состояние:

```bash
curl http://localhost:8000/api/projects/projects/observatory/state
```

Выбрать концепцию, когда пайплайн ждёт ввода:

```bash
curl -X POST http://localhost:8000/api/projects/<project_id>/select-concept \
  -H "Content-Type: application/json" \
  -d '{"concept_index": 0}'
```

`project_id` — UUID из ответа `POST /api/projects`; он также доступен как `state.id` в `project.json`.

Получить финальные файлы:

```bash
curl http://localhost:8000/api/projects/projects/observatory/final/script.md
curl http://localhost:8000/api/projects/projects/observatory/final/teleprompter.md
```

Эндпоинты финальных файлов возвращают JSON с полем `content`, а не сырой Markdown.

## Web UI

Фронтенд находится в `web/` и использует Next.js `16.2.4`, React `19.2.4`, TypeScript и Tailwind CSS.

Запустить API и фронтенд в двух терминалах:

```bash
# Терминал 1
cd /Users/artem/Documents/SceneForge
source .venv/bin/activate
python3 -m api.main
```

```bash
# Терминал 2
cd /Users/artem/Documents/SceneForge/web
npm install
npm run dev
```

Открыть `http://localhost:3000`.

Опционально задать URL API:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Текущее ограничение Web UI: страница проекта ожидает более богатые поля шагов/статусов, чем сейчас возвращает бэкенд. До обновления фронтенд-адаптера используйте CLI или прямые API-запросы как источник правды.

## Файлы проекта

Каждый запуск пишет проект в `PROJECTS_DIR`:

```text
projects/<name>/
├── project.json
└── final/
    ├── script.md
    └── teleprompter.md
```

`project.json` — возобновляемое состояние. `current_step` — zero-based индекс следующего шага. После полного завершения `current_step` равен `10`.

## Тесты

Запустить все тесты:

```bash
python3 -m pytest tests/ -v
```

Запустить отдельные наборы:

```bash
python3 -m pytest tests/test_schemas.py -v
python3 -m pytest tests/test_agents.py -v
```

Тесты используют mock LLM-провайдеры и не требуют реальных API-ключей.

## Документация

Полная документация находится в `docs/`:

- [Индекс документации](docs/README.md)
- [Руководство по использованию](docs/usage.md)
- [Архитектура](docs/architecture.md)
- [API reference](docs/api.md)
- [Модели данных](docs/data-models.md)
- [Руководство разработчика](docs/development.md)

`CLAUDE.md` остаётся исходными проектными заметками и roadmap. Документация выше — сводная версия, сверенная с текущим кодом.
