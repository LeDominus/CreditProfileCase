# Agent Guide — CreditProfile Frontend (`front/`)

Web frontend for the hackathon project «Умный кредитный кабинет» (Alfa-Bank):
a credit pipeline for small business with an LLM assistant. Backend is
FastAPI on :5555 (`../main.py`, do NOT change). Legacy Streamlit UI lives in
`../frontend/` as a behaviour reference — untouched.

Stack: Next.js 16.3.1 (App Router, `reactCompiler: true`, `distDir: 'dist'`),
React 19.2.8, Bun, Tailwind v4 (CSS `@theme` config, no tailwind.config),
Base UI primitives, zustand 5 (session, persisted), @tanstack/react-query 5,
ky v2, zod 4, sonner, framer-motion 13, Biome 2.4.2. Port **8502**.

## Commands

- `bun run dev` / `bun run build` / `bun start` — dev/prod on :8502
- `bun run lint` (biome check), `bunx tsc --noEmit`

## Conventions

- FSD: `src/app` is thin routing only (route groups `(auth)`, `(client)`,
  `(bank)`); everything else in `src/fsd/{app,pages,widgets,features,entities,shared}`.
  Alias `@/*` → `./src/*`.
- There is NO `src/app/layout.tsx` — each route group has its own root layout
  rendering `fsd/app/root-shell.tsx` (fonts via @font-face, Providers).
- Biome: 2 spaces, single quotes, semicolons asNeeded, width 100; kebab-case
  files; PascalCase named exports (default only for Next pages/layouts);
  `cn()` from `@/fsd/shared/lib/utils`; `'use client'` for interactive code.
- UI copy is Russian, hardcoded inline; code comments in English, minimal.

## Design tokens (Alfa-Bank, light theme only)

All in `fsd/app/styles/globals.css` `@theme`: accent `#ef3124`
(hover/press variants), positive/negative/attention/info, text-primary
`#0b1f35`, text-secondary `#898991`, bg-primary/secondary, border; radii
4–24px + pill; shadows from core-components shadows-indigo. Font: self-hosted
Alfa Interface Sans (400/500/700 woff2 in `public/fonts/`). Buttons are pill,
cards 12–16px radius.

## Auth / API

- Backend token is a non-expiring opaque Bearer; session-store
  (`entities/session/model/session-store.ts`) persists {token, user} to
  localStorage; `SessionBootstrap` revalidates via `GET /api/auth/me` on start
  (401 → drop session). No refresh flow — do not add one.
- `shared/api/http.ts` — the single ky instance: `prefix: '/api'` (proxied by
  next.config rewrites to `BACKEND_URL`, default `http://127.0.0.1:5555`),
  Bearer header, 401 → clear + redirect /login, FastAPI `{detail}` unwrap
  (string or 422 array), timeout 120 s (LLM endpoints are slow).
- Route guards: `features/auth/auth-gate.tsx` (`allow: UserRole[]`), client →
  `/`, bank roles → `/admin`; `guest-gate.tsx` bounces authed users off /login.
- Zod schemas in `entities/*/model/schemas.ts`, snake_case → camelCase
  normalization via `.transform`; FastAPI models are `extra="forbid"` — send
  only contract fields.

## Contract reference

`~/HakatonChat/files/FRONTEND_GUIDE (1).md` is the API contract source of
truth (27 endpoints; auth, conversations, profile, applications, admin,
registry, products). Public endpoints: products, recommendations, registry —
no token needed.

## Client cabinet (`/`, stage 3)

Three-column layout in `pages/client-home`: `widgets/app-sidebar` (260px) /
`widgets/chat-panel` (fluid) / `widgets/right-panel` (380px, tabs).

- Sidebar nav maps onto right-panel tabs via
  `widgets/right-panel/model/panel-store.ts`: Главная → products (active
  highlight), Кредиты → products + «в разработке» toast, Заявки →
  applications, Профиль → profile, Поддержка → stub toast. «Новая заявка»
  (`features/create-conversation`) creates a dialog and makes it active.
- Chat (`widgets/chat-panel` + `features/send-message`):
  - Send order with no active dialog: POST /api/conversations FIRST, then
    POST /api/conversations/{id}/messages (profile_id attached from the
    profile cache when known).
  - Optimistic UX lives in `entities/conversation/model/chat-store.ts`
    (activeConversationId, pendingUserMessage + pendingConversationId →
    bubble + typing indicator, composer locked while the mutation runs).
  - ContractExtraction on success: confirmed user/assistant messages appended
    to the messages query cache (then invalidated), `profile`/`profile_updates`
    merged into the myProfile cache, non-empty `recommendations` →
    `entities/product/model/recommendations-store.ts` (empty array keeps the
    previous selection — the panel must not flicker empty).
  - Session restore: active dialog = newest from GET /api/conversations;
    messages per dialog = react-query by conversationId (keys in
    `shared/api/query-keys.ts`).
  - Assistant `reply` renders via `shared/ui/markdown.tsx` (react-markdown +
    remark-gfm, raw HTML disabled).
- Right panel tabs: products (`widgets/right-panel/products-panel.tsx`, stage
  4), profile (`widgets/right-panel/profile-panel.tsx` — view, PATCH edit,
  POST create with industry+funding_purpose), applications (stage 5).

## Products & application flow (stage 4)

- «Подобрать продукты» (`features/pick-products`) → POST /api/recommendations
  with profile fields; disabled until `isProfileCompleteForRecommendations`.
  Results go to `entities/product/model/recommendations-store.ts` (same store
  the chat fills). «Сравнить все продукты» — modal table over GET
  /api/products (`useProducts`).
- Product pick → `features/submit-application/model/draft-store.ts`
  (selectedProduct/amount/term/dataConfirmed/formOpen/accepted) →
  `features/select-product/ui/application-params.tsx`: sliders+inputs clamped
  to product ranges, payment block, disclaimers, confirm checkbox.
- Payment (`features/calc-payment/model/use-payment-calc.ts`): 500 ms debounce;
  the payment endpoint computes from PROFILE fields, so params are PATCHed
  into the profile first, then POST /api/profile/{id}/payment; any failure →
  local annuity fallback (`shared/lib/annuity.ts`), never an error state.
- «Данные для заявки» (`features/fill-application-form`): NON-dismissible
  dialog (controlled root swallows Esc/outside click + disablePointerDismissal;
  closes via «Отмена» or successful submit). Scrollable sections layout (as
  the Streamlit reference — chosen over a stepper). «Заполнить по ИНН» → GET
  /api/registry/{inn} (404 → manual-fill notice). Files never leave the
  browser; only names go into documents. Owners list = ФИО+паспорт pairs
  (contract fields; no share/INN in ClientDataRequest). Validation:
  `model/client-data-schema.ts` mirrors ClientDataRequest (ИНН 10/12,
  +7-phone, email, consents), errors shown inline + summary box.
- Submit (`features/submit-application/model/use-submit-application.ts`):
  POST /api/applications → immediately POST .../submit, step labels
  («Создаём черновик…»/«Отправляем на проверку…»). Failed submit keeps the
  draft (submitted=false). Success → `application-accepted-dialog.tsx`
  (params, STATUS_LABELS + NEXT_STEP_HINTS from
  `entities/application/model/status-labels.ts`, «Перейти к заявкам» switches
  the panel tab), invalidates queryKeys.myApplications.

## Applications tab (stage 5)

`widgets/right-panel/applications-panel.tsx` — cards over
`useMyApplications()` (refetchInterval 12 s: bank decisions surface without
client actions) + «Обновить». Status actions live in
`features/application-actions/` (one hook file + a UI block per status):

- draft: submit + «Изменить сумму и срок» dialog (PATCH, product ranges,
  local annuity preview).
- needs_info: needs_info_reason / missing_fields + «Обработать повторно»
  (POST /scoring).
- offer_ready: offer card; approved_with_changes → suggested_* as «было →
  стало» against requested; accept / decline dialog (reason ≥ 3 chars).
- accepted: «Подписать договор» (ЭП-модель → issued). issued: «Кредит выдан».
- rejected: stop_factors in plain language + alternatives cards with
  «Оформить заявку» (new draft via POST /api/applications).
- client_declined / in-work statuses: info block / pipeline stepper +
  NEXT_STEP_HINTS (both in status-labels.ts with STATUS_BADGE_VARIANTS).
- «Объяснить решение (ИИ)» (explain-block.tsx): only when decision != null,
  slow-endpoint spinner, markdown result, source=fallback caption.
- «История статусов» (history-disclosure.tsx): lazy GET .../history — shown
  to the client (own transitions are safe; deviation from PRD's bank-only
  split, documented).
- VISIBILITY: score/factors/analyst_decision are bank-only — never render in
  the client cabinet (`entities/application/model/visibility.ts` lists them
  explicitly; stage 6 АРМ will use them). decision_details is structured by
  `model/decision-details-schema.ts` (looseObject → camelCase; two shapes:
  scoring result vs stop-factor rejection without score/factors).

## Contract notes (verified against live backend 2026-10)

- The `profile` embedded in ContractExtraction OMITS user_id/created_at/
  updated_at (profile endpoints return them) — `businessProfileSchema` marks
  those optional. Do not tighten.
- With a dummy YANDEX_API_KEY the backend returns the fallback reply
  (FALLBACK_REPLY) instead of failing — messages endpoint stays testable.
- POST /api/profile/{id}/payment → 422 when the profile lacks
  requested_amount/preferred_term_months: PATCH the profile with the chosen
  params first, then retry (this is the intended flow, not an error).
- registration_date accepts a bare "YYYY-MM-DD" date string (pydantic coerces
  to datetime) — the form uses a date input.
- Healthy registry company (7701234567, 3 млн/12 мес): submit pipeline ends
  at offer_ready with decision approved, score ~88 — PRD scenario 1.
- Scoring runs off PROFILE fields, NOT client_data.finance — a rejection via
  score needs a bad profile (young business, negative profit); a stop-factor
  rejection needs client_data.finance.has_debts=true or a liquidation INN.
- Stop-factor rejections have decision_details = {stop_factors, explanation}
  ONLY — no alternatives (alternatives appear on scoring rejections).
- Full lifecycle verified live: draft → PATCH → submit → offer_ready →
  offer-response accept → sign → issued; explain returns source=fallback with
  a dummy LLM key (~0.5 s); history records every transition with actor
  (client/system).



## АРМ `/admin` (stage 6)

Two-column layout (`pages/admin-home`): `widgets/admin-queue` (380 px) /
`widgets/admin-application-details` (fluid). Separate interface, no client
sidebar.

- Queue: `useAdminQueue(statusFilter)` (react-query, refetchInterval 15 s) +
  «Обновить»; filter Select («Все статусы» + 14, `?status=`); «требуют
  действий» counter from the UNFILTERED queue (manager: data_check/scoring/
  manual_review, analyst: manual_review). Selection in
  `admin-queue/model/admin-queue-store.ts`; a selection that drops out of
  the filtered queue is reset with a toast.
- Details: params (+score badge when present — bank-visible here),
  client_data read-only sections (`model/client-data-schema.ts`), decision
  breakdown (factors with contributions, completeness, stop factors,
  analyst_decision), role actions, ADMIN_NO_ACTION_HINTS fallback (all in
  `entities/application/model/status-labels.ts` with MANAGER_ACTION_STATUSES /
  ASSIGN_ANALYST_STATUSES).
- Actions (`features/admin-actions`): request-info dialog (3–1000 with
  counter), assign-analyst confirm, analyst decision (segmented control +
  mandatory reason, approved_with_changes hint). 403 → «Недостаточно прав…»
  toast; 409 → backend message.

### Backend quirks found (live, 2026-10)

- GET /api/applications/{id}/history and POST .../explain are OWNER-only —
  bank roles get 404 on client applications. АРМ hides the history block on
  error and the analyst-explain shows an info toast (kept per PRD).
- manual_review: the pipeline does NOT persist scoring into the application
  (score/decision_details stay empty; preliminary scoring exists only in the
  submit/scoring RESPONSE `scoring` field). Details widget says so instead
  of showing empty factors.
- admin decision approved_with_changes does NOT compute suggested_* — the
  client's offer shows the requested terms (no diff).
- assign-analyst works only from data_check/scoring; the pipeline is
  synchronous, so in practice manual_review is reached via the borderline
  score (50–70) and assign-analyst from manual_review → 409.

## Docker / запуск (stage 8)

- `front/Dockerfile` — three stages: `oven/bun:1-slim` (deps) → `node:22-slim`
  (build, ARG `BACKEND_URL` default `http://backend:5555` — baked into
  rewrites at build time) → runner `node:22-slim`, `USER node`,
  `EXPOSE 8502`, `CMD node node_modules/next/dist/bin/next start -p 8502`.
- Root `docker-compose.yaml`: service `frontend` builds `./front`, port
  `${FRONTEND_PORT:-8502}:8502`, depends_on backend (healthy). The legacy
  Streamlit service was removed from compose (code stays in `frontend/`).
- Verified: `docker build` OK (~75 s), container serves the app and proxies
  /api to a reachable backend; `docker compose config` valid (needs `.env`
  for the backend's env_file — any dummy LLM values work for boot).
