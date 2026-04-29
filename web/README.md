# SceneForge Web UI

Этот каталог содержит экспериментальный Next.js-фронтенд для SceneForge.

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
```

## Текущее ограничение

Web UI — прототип. Страница проекта сейчас ожидает более богатые поля шагов/статусов, чем возвращает бэкенд. До синхронизации frontend adapter с `GET /api/projects/{project_dir}/state` используйте CLI или API напрямую как надёжный интерфейс.

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
