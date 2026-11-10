# Проверка npm-зависимостей — 23 октября 2026

До обновления `npm audit` находил 15 записей пакетов: 1 critical, 12 high, 1 moderate и 1 low. После совместимых обновлений осталось 5 high в одной цепочке dev-зависимостей ESLint. `npm audit --omit=dev` возвращает 0 находок.

Next.js и `eslint-config-next` обновлены с точных версий `16.2.4` до точных `16.4.2`. Остальные исправления установлены обычным `npm audit fix`, без `--force`, major-миграции и ослабления диапазонов. Точные версии React и React DOM не менялись.

| Пакет | До: уровень | До: fixAvailable | Установленные версии до → после |
| --- | --- | --- | --- |
| `@babel/core` | low | `true` | 7.29.0 → 7.29.7 |
| `@next/eslint-plugin-next` | high | `eslint-config-next@14.2.35; isSemVerMajor=true` | 16.2.4 → 16.4.2 |
| `baseline-browser-mapping` | moderate | `true` | 2.10.24 → 2.11.31 |
| `brace-expansion` | high | `true` | 1.1.14, 5.0.5 → 1.1.21, 5.0.12 |
| `braces` | high | `eslint-config-next@14.2.35; isSemVerMajor=true` | 3.0.3 → 3.0.3 |
| `browserslist` | high | `true` | 4.28.2 → 4.29.4 |
| `eslint-config-next` | high | `eslint-config-next@14.2.35; isSemVerMajor=true` | 16.2.4 → 16.4.2 |
| `fast-glob` | high | `eslint-config-next@14.2.35; isSemVerMajor=true` | 3.3.1 → 3.3.1 |
| `js-yaml` | high | `true` | 4.1.1 → 4.3.2 |
| `micromatch` | high | `eslint-config-next@14.2.35; isSemVerMajor=true` | 4.0.8 → 4.0.8 |
| `nanoid` | high | `true` | 3.3.11 → 3.3.20 |
| `next` | critical | `next@16.4.2; isSemVerMajor=false` | 16.2.4 → 16.4.2 |
| `postcss` | high | `next@16.4.2; isSemVerMajor=false` | 8.4.31, 8.5.12 → 8.5.23 |
| `sharp` | high | `next@16.4.2; isSemVerMajor=false` | 0.34.5 → 0.35.5 |
| `source-map-js` | high | `true` | 1.2.1 → 1.2.2 |

## Что осталось

Остались `eslint-config-next`, `@next/eslint-plugin-next`, `fast-glob`, `micromatch` и `braces`, все с уровнем high. Это распространение одной [уязвимости braces: stack-exhaustion DoS в глубоко вложенных шаблонах](https://github.com/advisories/GHSA-vfj7-8cjw-p6xm) по цепочке линтера.

По данным npm registry на дату проверки последняя версия `braces` — `3.0.3`; она входит в уязвимый диапазон. Даже `@next/eslint-plugin-next@16.4.2` использует `fast-glob@3.3.1`, ведущий к этой версии `braces`. Для всех пяти записей npm предлагает `eslint-config-next@14.2.35` с `isSemVerMajor: true`. Это откат между основными версиями с изменением конфигурации линтера, поэтому автоматически он не применяется. Совместимого исправленного релиза в этой цепочке пока нет.

Это dev-зависимости; production-проверка `npm audit --omit=dev` чистая. Полный `npm audit` продолжает возвращать ненулевой код из-за пяти оставшихся записей.

После обновления успешно повторены ESLint, TypeScript, production build и все 10 Playwright-проверок для desktop/mobile. Миграция исходного кода не потребовалась.

## Воспроизведение

```bash
cd web
npm ci
npm audit
npm audit --omit=dev
npm run lint
npx tsc --noEmit
npm run build
npx playwright install chromium
npm run test:e2e
```
