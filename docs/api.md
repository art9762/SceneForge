# API Reference

Бэкенд описан в `api/main.py`.

Запуск:

```bash
python3 -m api.main
```

Base URL:

```text
http://localhost:8000
```

CORS разрешён для:

```text
http://localhost:3000
```

## POST /api/projects

Создаёт проект, сохраняет начальный `project.json` и запускает пайплайн в фоновой задаче.

### Request

```json
{
  "raw_idea": "8-минутный YouTube-ролик про заброшенную советскую обсерваторию",
  "project_name": "observatory",
  "provider": "claude",
  "model": null
}
```

Поля:

| Поле | Тип | Обязательное | По умолчанию | Примечание |
| --- | --- | --- | --- | --- |
| `raw_idea` | string | да | нет | Исходная идея сценария. |
| `project_name` | string или null | нет | первые 40 символов идеи, пробелы заменены на `-`, lowercased | Имя папки внутри `PROJECTS_DIR`. |
| `provider` | string | нет | `claude` | `claude` или `openai`. |
| `model` | string или null | нет | модель провайдера по умолчанию | Переопределяет модель. |

### Response

```json
{
  "project_id": "2cda9ad1-6122-47db-a5e2-353c86d7c08d",
  "project_dir": "projects/observatory"
}
```

`project_id` используется для выбора концепции. `project_dir` используется для чтения состояния и финальных файлов.

### Пример

```bash
curl -X POST http://localhost:8000/api/projects \
  -H "Content-Type: application/json" \
  -d '{
    "raw_idea": "8-минутный YouTube-ролик про заброшенную советскую обсерваторию",
    "project_name": "observatory",
    "provider": "claude"
  }'
```

## GET /api/projects/{project_dir:path}/state

Читает сохранённое состояние проекта с диска.

Если `project_dir` равен `projects/observatory`, URL будет:

```text
/api/projects/projects/observatory/state
```

### Response

```json
{
  "state": {
    "id": "2cda9ad1-6122-47db-a5e2-353c86d7c08d",
    "raw_idea": "...",
    "current_step": 2,
    "brief": {},
    "concepts": {},
    "selected_concept_index": null,
    "structure": null,
    "draft_v1": null,
    "critique": null,
    "draft_v2": null,
    "production_notes": null,
    "edit_notes": null,
    "final_script": null,
    "created_at": "2026-04-29T...",
    "updated_at": "2026-04-29T..."
  },
  "steps": [
    "brief",
    "concepts",
    "select_concept",
    "structure",
    "draft_v1",
    "critique",
    "draft_v2",
    "production",
    "edit_notes",
    "assemble"
  ],
  "total_steps": 10
}
```

`current_step` находится внутри `state`, а не на верхнем уровне ответа.

### Как вычислить статус шага

API сейчас возвращает только имена шагов. Клиент может вычислять статус так:

```ts
function statusFor(index: number, currentStep: number) {
  if (index < currentStep) return "done";
  if (index === currentStep) return "running_or_waiting";
  return "pending";
}
```

Если `current_step === 2`, `state.concepts` уже есть, а `state.selected_concept_index === null`, пайплайн ждёт выбора концепции.

## POST /api/projects/{project_id}/select-concept

Отправляет выбранный concept index для текущего API-пайплайна.

### Request

```json
{
  "concept_index": 0
}
```

`concept_index` — zero-based.

### Response

```json
{
  "status": "ok"
}
```

### Важное поведение

Очереди выбора концепции хранятся в памяти. Эндпоинт работает только пока запущен тот же API-процесс, который создал проект.

Если бэкенд перезапустился, пока проект ждал выбора концепции, используйте CLI resume-flow или начните новый API-flow.

## GET /api/projects/{project_dir:path}/final/{filename}

Читает сгенерированный финальный файл.

Файлы, которые создаёт пайплайн:

- `script.md`
- `teleprompter.md`

### Response

```json
{
  "content": "# Script markdown..."
}
```

Эндпоинт возвращает JSON, а не raw file bytes.

### Примеры

```bash
curl http://localhost:8000/api/projects/projects/observatory/final/script.md
curl http://localhost:8000/api/projects/projects/observatory/final/teleprompter.md
```

## Ошибки

API возвращает `404`, если:

- `project.json` не найден.
- Не найдена очередь выбора концепции для `project_id`.
- Финальный файл не найден.

Ошибки конфигурации провайдера происходят внутри background task и печатаются в stdout бэкенда как `Pipeline error: ...`.

## Текущие пробелы API

- Нет эндпоинта для статуса background task и деталей exception.
- Нет endpoint для отмены пайплайна.
- Нет raw Markdown download endpoint.
- Нет WebSocket или server-sent events.
- Статусы шагов не возвращаются напрямую.
