# Руководство по использованию

Этот документ описывает локальную установку и ежедневную работу со SceneForge.

## 1. Установка Python-пакета

```bash
cd /Users/artem/Documents/SceneForge

python3 -m venv .venv
source .venv/bin/activate

python3 -m pip install -e .
python3 -m pip install -e ".[dev]"
```

`python3 -m pip install -e .` устанавливает консольную команду `sceneforge` из `pyproject.toml`.

## 2. Настройка окружения

Скопировать шаблон:

```bash
cp .env.example .env
```

Для запусков через Claude:

```dotenv
TRINITY_CLAUDE_API_KEY=your-claude-key
```

Для запусков через OpenAI:

```dotenv
TRINITY_OPENAI_API_KEY=your-openai-key
```

Base URL по умолчанию:

```dotenv
TRINITY_CLAUDE_BASE_URL=https://gate.trinity.tg/aurora/v1
TRINITY_OPENAI_BASE_URL=https://gate.trinity.tg/orion/v1
```

Опциональные переменные, которые поддерживает `Settings`:

```dotenv
DEFAULT_CLAUDE_MODEL=claude-sonnet-4-6
DEFAULT_OPENAI_MODEL=gpt-5.4
PROJECTS_DIR=projects
```

SceneForge проверяет только выбранный провайдер. Если запуск идёт через Claude, OpenAI-ключ не нужен.

## 3. CLI-запуск

Создать новый проект:

```bash
sceneforge run "8-минутный YouTube-ролик про заброшенную советскую обсерваторию"
```

Создать проект с устойчивым именем папки:

```bash
sceneforge run "идея видео" --name observatory
```

Использовать OpenAI через Trinity:

```bash
sceneforge run "идея видео" --provider openai --model gpt-5.4
```

Включить debug-логи:

```bash
sceneforge run "идея видео" --debug
```

Debug-режим логирует:

- Первые 500 символов system prompt каждого агента.
- Первые 500 символов user message.
- Первые 500 символов структурированного выхода агента.
- Старт/финиш агента, провайдер, модель и время выполнения.

## 4. Выбор концепции

После генерации концепций CLI показывает три варианта и просит выбрать номер. Введите `1`, `2` или `3`.

Выбор сохраняется в `project.json` как `selected_concept_index`.

## 5. Продолжение проекта

SceneForge сохраняет состояние после каждого шага. Продолжить с первого незавершённого шага:

```bash
sceneforge resume projects/observatory
```

Продолжить с другим провайдером или моделью:

```bash
sceneforge resume projects/observatory --provider openai --model gpt-5.4
```

Проверить прогресс:

```bash
sceneforge status projects/observatory
```

`current_step` — zero-based индекс следующего шага:

| Значение | Значение состояния |
| ---: | --- |
| `0` | Ничего не завершено; следующий шаг — бриф. |
| `1` | Бриф готов; следующий шаг — концепции. |
| `2` | Концепции готовы; следующий шаг — выбор концепции. |
| `10` | Пайплайн полностью завершён. |

## 6. Выходные файлы

После завершения создаётся:

```text
projects/<name>/
├── project.json
└── final/
    ├── script.md
    └── teleprompter.md
```

`script.md` содержит:

- Бриф.
- Посценный сценарий.
- Продакшн-заметки.
- Монтажные заметки.

`teleprompter.md` содержит только voiceover из финального драфта.

## 7. Запуск API

```bash
cd /Users/artem/Documents/SceneForge
source .venv/bin/activate
python3 -m api.main
```

Бэкенд запускается на `http://localhost:8000`.

Для разработки с reload:

```bash
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

## 8. Запуск Web UI

```bash
cd /Users/artem/Documents/SceneForge/web
npm install
npm run dev
```

Открыть `http://localhost:3000`.

Задать кастомный URL API:

```bash
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
```

Текущее ограничение: страница проекта во фронтенде пока не полностью соответствует форме ответа API. Для рабочих прогонов используйте CLI или прямые API-запросы.

## Troubleshooting

### Не задан API-ключ

Если видите:

```text
TRINITY_CLAUDE_API_KEY не задан
```

или:

```text
TRINITY_OPENAI_API_KEY не задан
```

заполните соответствующий ключ в `.env` или переключите провайдера через `--provider`.

### Проект уже существует

`sceneforge run` использует `projects/<name>/project.json`, если файл уже есть. Повторный запуск с тем же именем продолжит проект, а не начнёт заново. Для нового проекта укажите другое `--name`.

### Нет финальных файлов

`final/script.md` и `final/teleprompter.md` появляются только после шага `assemble`. Проверьте статус:

```bash
sceneforge status projects/<name>
```

### API завис на выборе концепции

API-пайплайн ждёт `POST /api/projects/{project_id}/select-concept`. Процесс API должен оставаться тем же, потому что очереди выбора концепции хранятся в памяти.
