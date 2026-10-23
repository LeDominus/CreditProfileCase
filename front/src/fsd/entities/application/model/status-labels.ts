import type { ApplicationStatus } from './schemas'

/** Russian status labels (mirrors STATUS_LABELS in frontend/app.py). */
export const STATUS_LABELS: Record<ApplicationStatus, string> = {
  draft: 'Черновик',
  submitted: 'Отправлена',
  data_check: 'Проверка данных',
  scoring: 'На скоринге',
  needs_info: 'Нужны данные',
  manual_review: 'Ручная экспертиза',
  approved: 'Одобрена',
  approved_with_changes: 'Одобрена с изменениями',
  rejected: 'Отказ',
  offer_ready: 'Предложение готово',
  accepted: 'Условия приняты',
  signed: 'Подписана',
  issued: 'Выдана',
  client_declined: 'Вы отказались от предложения',
}

/** «Что дальше» по финальному статусу (аналог NEXT_STEP_HINTS в app.py). */
export const NEXT_STEP_HINTS: Partial<Record<ApplicationStatus, string>> = {
  submitted: 'Заявка принята банком и обрабатывается автоматически.',
  data_check: 'Заявка на автоматической проверке данных.',
  scoring: 'Заявка на автоматическом скоринге.',
  manual_review:
    'Заявка передана кредитному аналитику банка (ручная экспертиза). ' +
    'Следите за статусом во вкладке «Заявки» — решение появится там.',
  needs_info:
    'Банк запросил уточнения по заявке. Причина — во вкладке «Заявки»: ' +
    'уточните данные и отправьте заявку на повторную обработку.',
  offer_ready: 'Предложение банка готово! Примите или отклоните условия во вкладке «Заявки».',
  rejected:
    'По заявке получен отказ. Причина и возможные альтернативные продукты — во вкладке «Заявки».',
}

export type StatusBadgeVariant = 'neutral' | 'info' | 'attention' | 'positive' | 'negative'

/** Semantic badge color per status (PRD §6.1). */
export const STATUS_BADGE_VARIANTS: Record<ApplicationStatus, StatusBadgeVariant> = {
  draft: 'neutral',
  submitted: 'info',
  data_check: 'info',
  scoring: 'info',
  needs_info: 'attention',
  manual_review: 'attention',
  approved: 'positive',
  approved_with_changes: 'positive',
  rejected: 'negative',
  offer_ready: 'positive',
  accepted: 'info',
  signed: 'info',
  issued: 'positive',
  client_declined: 'negative',
}

/** Statuses where the pipeline works without the client (progress block). */
export const IN_PROGRESS_STATUSES: ApplicationStatus[] = [
  'submitted',
  'data_check',
  'scoring',
  'manual_review',
]

/** Ordered pipeline steps for the in-progress indicator. */
export const PIPELINE_STEPS: { status: ApplicationStatus; label: string }[] = [
  { status: 'submitted', label: 'Отправлена' },
  { status: 'data_check', label: 'Проверка данных' },
  { status: 'scoring', label: 'Скоринг' },
  { status: 'manual_review', label: 'Решение' },
]

/** Подсказки «действия не требуются» для статусов (ADMIN_NO_ACTION_HINTS в app.py). */
export const ADMIN_NO_ACTION_HINTS: Record<ApplicationStatus, string> = {
  draft: 'Черновик клиента — заявка ещё не отправлена в банк.',
  submitted: 'Заявка получена и обрабатывается автоматически.',
  data_check: 'Автоматическая проверка данных — действий сотрудника не требуется.',
  scoring: 'Автоматический скоринг — действий сотрудника не требуется.',
  needs_info: 'Ожидает уточнений от клиента — запрос уже отправлен.',
  manual_review: 'Заявка на ручной экспертизе — решение принимает кредитный аналитик.',
  approved: 'Одобрена автоматически — предложение сформировано, ожидается решение клиента.',
  approved_with_changes: 'Одобрена с изменениями автоматически — предложение сформировано.',
  rejected: 'Отказ по стоп-факторам или скорингу — действия сотрудника не требуются.',
  offer_ready: 'Предложение готово — ожидается решение клиента (принять/отклонить).',
  accepted: 'Клиент принял условия — ожидается подписание договора.',
  signed: 'Договор подписан клиентом — ожидается выдача финансирования.',
  issued: 'Финансирование выдано — заявка закрыта.',
  client_declined: 'Клиент отклонил предложение банка.',
}

/** Статусы, в которых менеджер может запросить уточнения / передать аналитику. */
export const MANAGER_ACTION_STATUSES: ApplicationStatus[] = [
  'data_check',
  'scoring',
  'manual_review',
]

/** Статусы, из которых менеджер может передать заявку аналитику. */
export const ASSIGN_ANALYST_STATUSES: ApplicationStatus[] = ['data_check', 'scoring']
