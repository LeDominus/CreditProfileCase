# THIRD_PARTY NOTICES

Проект — прототип для хакатона «Альфа-Будущее 2026» (кейс «Умный кредитный
кабинет»). Ниже — сторонние компоненты и условия их использования.

## Шрифты

- **Alfa Interface Sans** (woff2, regular/medium/bold) — проприетарный шрифт
  АО «Альфа-Банк». Файлы получены с публичного CDN Альфа-Банка
  (`alfabank.servicecdn.ru/media/fonts/`) и зафиксированы локально в
  `front/public/fonts/` для независимости от сети. Используется исключительно
  для воспроизведения фирменного стиля заказчика кейса в рамках хакатонного
  прототипа; права на шрифт принадлежат АО «Альфа-Банк».

## Open-source зависимости (frontend, `front/`)

Все перечисленные пакеты распространяются под permissive-лицензиями
(MIT, если не указано иное; текущие лицензии — в `node_modules/<pkg>/LICENSE`
и в реестре npm):

- Next.js (MIT), React / React DOM (MIT) — фреймворк и рантайм UI.
- Tailwind CSS (MIT), @tailwindcss/postcss, tw-animate-css (MIT) — стили.
- @base-ui/react (MIT) — headless UI-примитивы.
- ky (MIT) — HTTP-клиент.
- zustand (MIT) — клиентский стейт.
- @tanstack/react-query (MIT) — серверный стейт.
- zod (MIT) — валидация контрактов.
- react-markdown (MIT), remark-gfm (MIT) — рендер markdown ответов ассистента.
- sonner (MIT) — уведомления.
- framer-motion (MIT) — анимации.
- lucide-react (ISC) — иконки.
- clsx (MIT), tailwind-merge (MIT), class-variance-authority (Apache-2.0).
- TypeScript (Apache-2.0), Biome (MIT OR Apache-2.0) — инструментарий.

Backend-зависимости — по `requirements.txt` (FastAPI, SQLAlchemy, Pydantic,
Uvicorn, openai и др. — MIT/BSD/Apache-2.0).

## Внешние сервисы и симуляции

- **LLM — YandexGPT** (Yandex Foundation Models, OpenAI-совместимый API):
  внешний платный API, используется для диалога ассистента, извлечения полей
  профиля и объяснения решений. ВНИМАНИЕ: ТЗ кейса рекомендует LLM с открытыми
  весами — текущий провайдер закрытый; провайдер меняется конфигурацией
  (`BASE_URL`/`YANDEX_API_KEY`/`MODEL_NAME` в `.env`) без правок кода, замена
  на open-weights модель с OpenAI-совместимым endpoint — задача бэкенда.
- **Реестр юрлиц по ИНН** — симуляция (мок на синтетических данных,
  `src/config/registry.py`), не является выпиской из ЕГРЮЛ/ЕГРИП.
- **Электронная подпись** — моделируется кнопкой; реальная ЭП не используется.
- Название и фирменный стиль «Альфа-Банк» принадлежат АО «Альфа-Банк» и
  используются по условиям кейса хакатона.
