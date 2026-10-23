# SceneForge Web UI

Этот каталог содержит Next.js-фронтенд для SceneForge: создание проекта, прогресс, выбор концепции и скачивание готовых файлов.

[Пример готового проекта с тестовыми данными](../docs/web-project-mobile.png).

## Стек

- Next.js `16.2.4`
- React `19.2.4`
- TypeScript
- Tailwind CSS

## Локальный запуск

Сначала запустите Python API из корня репозитория:

```bash
cd /Users/artem/Documents/SceneForge
source .venv/bin/activate
python3 -m api.main
```

Затем запустите фронтенд:

```bash
cd /Users/artem/Documents/SceneForge/web
npm install
npm run dev
```

Откройте `http://localhost:3000`.

Фронтенд использует:

```text
NEXT_PUBLIC_API_URL=http://localhost:8000
```

Если переменная не задана, `web/lib/api.ts` использует `http://localhost:8000`.

## Скрипты

```bash
npm run dev
npm run lint
npm run build
npm run start

# Браузерные проверки с mock API, без LLM и API-ключей
npx playwright install chromium
npm run build
npm run test:e2e
```

## Контракт и ограничения

Типы в `lib/api.ts` соответствуют текущему API: `steps` — массив имён, прогресс находится в `state.current_step`, концепции — в `state.concepts.concepts`, выбранный индекс — в `state.selected_concept_index`. Выбор отправляется по UUID `state.id`; индекс `0` — полноценный выбор. Кнопки файлов преобразуют JSON `{content}` в скачиваемый Markdown.

Polling выполняется каждые 3 секунды после завершения предыдущего запроса и восстанавливается после ошибки сети. Показан последний сохранённый шаг; API не отдаёт состояние фоновой задачи и её исключения. После рестарта API используйте CLI для продолжения проекта.

Playwright проверяет desktop и mobile, использует `tests/fixtures/project-states.json` и перехватывает API-запросы. `tests/test_web_contract.py` в корне сверяет эти fixtures с реальными ответами FastAPI и моделями Pydantic. Ни один тест не вызывает платный LLM.

## Файлы

- `app/page.tsx` — форма создания проекта.
- `app/project/[...path]/page.tsx` — страница прогресса проекта.
- `lib/api.ts` — fetch-обёртка для FastAPI.
- `AGENTS.md` и `CLAUDE.md` — локальные инструкции для фронтенда.

## Полная документация

См.:

- [../README.md](../README.md)
- [../docs/README.md](../docs/README.md)
- [../docs/api.md](../docs/api.md)

Важно: проект использует новую версию Next.js, поэтому перед Next-specific изменениями нужно читать локальную документацию в `node_modules/next/dist/docs/`.
