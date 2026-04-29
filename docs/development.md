# Руководство разработчика

Этот документ нужен для расширения и сопровождения SceneForge.

## Локальная разработка

Установить пакет и dev-зависимости:

```bash
cd /Users/artem/Documents/SceneForge
python3 -m venv .venv
source .venv/bin/activate
python3 -m pip install -e ".[dev]"
```

Запустить все тесты:

```bash
python3 -m pytest tests/ -v
```

Только тесты схем:

```bash
python3 -m pytest tests/test_schemas.py -v
```

Только тесты агентов:

```bash
python3 -m pytest tests/test_agents.py -v
```

Текущие тесты используют mock LLM-провайдеры и не вызывают внешние API.

## Логирование

SceneForge использует `loguru`.

На `INFO` логируется:

- Старт агента.
- Провайдер и модель агента.
- Время выполнения агента.
- Время выполнения шага пайплайна.

На `DEBUG` в debug-режиме логируется:

- Фрагменты system prompt.
- Фрагменты user message.
- Фрагменты структурированного output.

На `WARNING` логируется:

- Ретраибельный сбой LLM-вызова.
- Ошибка JSON parsing перед повторной попыткой.

На `ERROR` логируется:

- Финальная ошибка JSON parsing после всех попыток.

Включить debug через CLI:

```bash
sceneforge run "идея" --debug
```

Включить debug из кода:

```python
from core.agents.base import set_debug_mode

set_debug_mode(True)
```

## Как добавить нового агента

1. Добавить input/output схемы в `core/schemas/` или определить локальную input-модель рядом с агентом, если она нужна только одному шагу.

2. Создать агента в `core/agents/`:

```python
from __future__ import annotations

from typing import ClassVar

from pydantic import BaseModel

from .base import BaseAgent
from ..schemas.my_schema import MyInput, MyOutput


class MyAgent(BaseAgent):
    name: ClassVar[str] = "my_agent"
    description: ClassVar[str] = "Что делает агент"
    system_prompt: ClassVar[str] = "Детальный системный промпт на русском."
    input_schema: ClassVar[type[BaseModel]] = MyInput
    output_schema: ClassVar[type[BaseModel]] = MyOutput
    default_provider: ClassVar[str] = "claude"
    default_model: ClassVar[str] = ""
```

3. Экспортировать агента из `core/agents/__init__.py`.

4. Добавить поле в `ProjectState`, если результат нужно сохранять.

5. Добавить шаг в `Pipeline._build_steps()`.

6. Реализовать метод шага в `core/pipeline.py`.

7. Добавить тесты с mock provider.

## Как добавить схему

Используйте Pydantic v2 модели:

```python
from __future__ import annotations

from pydantic import BaseModel, Field


class MyOutput(BaseModel):
    items: list[str] = Field(default_factory=list)
```

Для полей, которые LLM может пропустить, полезны безопасные defaults. Для критичных значений используйте constraints. Пример: `Critique.overall_score` ограничен `ge=1` и `le=10`.

## Провайдеры

Фабрика провайдеров:

```python
from core.llm.provider import get_provider

provider = get_provider("claude")
```

`get_provider()` валидирует ключ выбранного провайдера.

`generate_structured()` просит модель вернуть JSON по output schema, удаляет случайные Markdown fences, валидирует через Pydantic и ретраит ошибки parsing/validation.

## Retry

`retry_async()` повторяет транзиентные сбои:

- Rate limit.
- Server errors.
- Timeouts.
- Network errors.

Не используйте его для произвольных validation errors вне LLM-вызовов, если операция не идемпотентна.

## Финальная сборка

`FinalAssembler` детерминированный и не вызывает LLM.

Он пишет:

- `script.md`.
- `teleprompter.md`.

Он выбирает `draft_v2`, если он есть, и fallback на `draft_v1`.

## Frontend-разработка

Фронтенд находится в `web/`.

```bash
cd /Users/artem/Documents/SceneForge/web
npm install
npm run dev
```

Lint:

```bash
npm run lint
```

Build:

```bash
npm run build
```

Важная инструкция из `web/AGENTS.md`: проект использует Next.js `16.2.4`; перед Next-specific изменениями нужно сверяться с локальной документацией в `node_modules/next/dist/docs/`.

### Что нужно поправить во frontend-контракте

Текущий бэкенд возвращает:

```json
{
  "state": { "current_step": 2, "concepts": { "concepts": [] } },
  "steps": ["brief", "concepts", "select_concept"],
  "total_steps": 10
}
```

Текущая страница проекта ожидает объекты шагов с `name` и `status`, а также aliases вроде `selected_concept`, `critique.score` и concept `title`. Перед использованием Web UI нужно либо обновить frontend adapter, либо изменить форму ответа API.

## Roadmap из проектных заметок

Планы из `CLAUDE.md`:

- ResearchAgent для фактической базы.
- VoiceStyleAgent для авторского стиля.
- ConflictStakesAgent для усиления напряжения.
- Per-agent маршрутизация моделей.
- Model debate flows.
- Несколько режимов проекта.
- Перезапуск отдельного шага.
- Diff-view драфтов.
- Экспорт в PDF, Google Docs и Fountain.
- Версионирование драфтов.
- Streaming generation.
- WebSockets вместо polling.
- Аутентификация и multi-user Web UI.
- Хранение проектов в БД.
- Дополнительные артефакты: названия, thumbnail ideas, YouTube description, tags, chapters, social teasers.

## Checklist перед завершением изменений

- Запустить targeted tests для изменённой области.
- Для core-изменений запустить `python3 -m pytest tests/ -v`.
- Для frontend-изменений запустить `npm run lint` и `npm run build`.
- Обновить документацию, если изменились публичные команды, переменные окружения, API payloads, выходные файлы или схемы.
