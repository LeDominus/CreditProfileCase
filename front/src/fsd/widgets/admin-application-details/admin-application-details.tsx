'use client'

import { ChevronDownIcon, SparklesIcon } from 'lucide-react'
import { useState } from 'react'
import { useAdminQueue } from '@/fsd/entities/application/model/admin-queries'
import type { ClientData } from '@/fsd/entities/application/model/client-data-schema'
import { useApplicationHistory } from '@/fsd/entities/application/model/queries'
import type { Application, ApplicationStatus } from '@/fsd/entities/application/model/schemas'
import {
  ADMIN_NO_ACTION_HINTS,
  STATUS_BADGE_VARIANTS,
  STATUS_LABELS,
} from '@/fsd/entities/application/model/status-labels'
import { useSession } from '@/fsd/entities/session/model/session-store'
import { useExplainAnalyst } from '@/fsd/features/admin-actions/model/use-admin-actions'
import { AnalystActions } from '@/fsd/features/admin-actions/ui/analyst-actions'
import { ManagerActions } from '@/fsd/features/admin-actions/ui/manager-actions'
import { formatDateTime, formatMoney } from '@/fsd/shared/lib/format'
import { cn } from '@/fsd/shared/lib/utils'
import { Badge } from '@/fsd/shared/ui/badge'
import { Button } from '@/fsd/shared/ui/button'
import { Markdown } from '@/fsd/shared/ui/markdown'
import { Skeleton } from '@/fsd/shared/ui/skeleton'
import { useAdminQueueStore } from '../admin-queue/model/admin-queue-store'

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-2 rounded-xl border border-border p-4">
      <h3 className="text-sm font-bold">{title}</h3>
      {children}
    </section>
  )
}

function Row({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <div className="flex items-baseline justify-between gap-4 text-sm">
      <span className="shrink-0 text-xs text-text-secondary">{label}</span>
      <span className="text-right font-medium">{value ?? '—'}</span>
    </div>
  )
}

function ClientDataSection({ clientData }: { clientData: ClientData | null }) {
  if (clientData == null) {
    return (
      <Section title="Данные клиента">
        <p className="text-xs text-text-secondary">
          Пакет данных клиента не передавался (заявка создана без автозаполнения по ИНН).
        </p>
      </Section>
    )
  }
  const { credit, company, supervisor, finance, documents, consents } = clientData
  return (
    <>
      <Section title="Клиент">
        <Row label="Компания" value={company.companyName} />
        <Row label="ИНН" value={company.inn} />
        <Row label="ОГРН" value={company.ogrn} />
        <Row label="Вид деятельности" value={company.typeOfActivity} />
        <Row label="Налогообложение" value={company.taxationSystem} />
        <Row label="Сотрудников" value={company.companyMembersCount} />
        <Row label="Телефон" value={company.companyPhone} />
        <Row label="E-mail" value={company.companyEmail} />
      </Section>
      <Section title="Руководитель">
        <Row label="ФИО" value={supervisor.fullName} />
        <Row label="Паспорт" value={supervisor.passport} />
        <Row label="ИНН физлица" value={supervisor.innFizFace} />
        <Row label="Телефон" value={supervisor.supervisorPhone} />
        <Row label="E-mail" value={supervisor.supervisorEmail} />
        {(supervisor.ownersFullName?.length ?? 0) > 0 && (
          <Row label="Владельцы >25%" value={supervisor.ownersFullName?.join('; ')} />
        )}
      </Section>
      <Section title="Кредит и финансы">
        <Row label="Тип кредита" value={credit.creditProduct} />
        <Row label="Цель" value={credit.creditTarget} />
        <Row label="Выручка за год" value={formatMoney(finance.revenue)} />
        <Row label="Прибыль за год" value={formatMoney(finance.profit)} />
        <Row
          label="Задолженности"
          value={
            finance.hasDebts == null
              ? '—'
              : finance.hasDebts
                ? 'Есть просроченная задолженность'
                : 'Просроченной задолженности нет'
          }
        />
        {(finance.currentLoansAndLeasing?.length ?? 0) > 0 && (
          <Row label="Кредиты и лизинг" value={finance.currentLoansAndLeasing?.join('; ')} />
        )}
      </Section>
      <Section title="Документы и согласия">
        <Row label="Скан паспорта" value={documents.supervisorPassportScan || '—'} />
        <Row
          label="Документы бизнеса"
          value={(documents.businessDoc?.length ?? 0) > 0 ? documents.businessDoc?.join(', ') : '—'}
        />
        <Row label="Форма бизнеса" value={documents.businessType === 'ip' ? 'ИП' : 'ООО'} />
        <Row label="Согласие на ПДн" value={consents.personalDataAgreement ? 'Да' : 'Нет'} />
        <Row
          label="Согласие на кредитную историю"
          value={consents.creditHistoryAgreement ? 'Да' : 'Нет'}
        />
      </Section>
    </>
  )
}

function DecisionBreakdown({ application }: { application: Application }) {
  const details = application.decisionDetails
  if (details == null) return null
  const factors = details.factors ?? []
  const stopFactors = details.stopFactors ?? []
  const missing = details.missingFields ?? []

  return (
    <Section title="Разбор решения">
      {details.explanation && (
        <p className="text-xs leading-relaxed text-text-secondary">{details.explanation}</p>
      )}
      {factors.length > 0 ? (
        <div className="flex flex-col gap-1.5">
          {factors.map((factor) => (
            <div key={factor.name} className="flex items-baseline justify-between gap-3 text-sm">
              <span className="text-xs text-text-secondary">
                {factor.label} — {factor.value}
              </span>
              <span className="text-xs font-medium">
                вклад {factor.contribution >= 0 ? '+' : ''}
                {factor.contribution.toFixed(2)}
              </span>
            </div>
          ))}
        </div>
      ) : application.status === 'manual_review' ? (
        <p className="text-xs text-text-secondary">
          Предварительный скоринг не сохраняется в заявке (особенность бэкенда) — решение принимает
          аналитик на основании данных заявки и профиля клиента.
        </p>
      ) : (
        <p className="text-xs text-text-secondary">Факторы скоринга не рассчитывались.</p>
      )}
      <Row
        label="Полнота данных"
        value={
          missing.length > 0
            ? `Не заполнено: ${missing.join(', ')}`
            : 'Все обязательные поля заполнены'
        }
      />
      <Row
        label="Стоп-факторы"
        value={
          stopFactors.length > 0
            ? stopFactors.map((factor) => factor.label).join('; ')
            : 'Не зафиксированы'
        }
      />
      {details.needsInfoReason && <Row label="Запрос менеджера" value={details.needsInfoReason} />}
      {details.analystDecision && (
        <>
          <Row
            label="Решение аналитика"
            value={
              STATUS_LABELS[details.analystDecision.decision as ApplicationStatus] ??
              details.analystDecision.decision
            }
          />
          <Row label="Причина" value={details.analystDecision.reason} />
          <Row label="Аналитик" value={details.analystDecision.analyst} />
        </>
      )}
    </Section>
  )
}

function AnalystExplainBlock({ application }: { application: Application }) {
  const explain = useExplainAnalyst(application.id)
  if (application.decision == null) return null
  const result = explain.data

  return (
    <div className="flex flex-col gap-2">
      <Button
        size="sm"
        variant="ghost"
        onClick={() => explain.mutate()}
        disabled={explain.isPending}
      >
        <SparklesIcon />
        {explain.isPending ? 'Ассистент анализирует решение…' : 'Объяснить решение (ИИ)'}
      </Button>
      {result && (
        <div className="rounded-lg border border-border px-3 py-2 text-sm">
          <Markdown content={result.explanation} />
          {result.source === 'fallback' && (
            <p className="mt-2 text-[11px] text-text-secondary">
              Сформулировано автоматически без участия ИИ.
            </p>
          )}
        </div>
      )}
    </div>
  )
}

function AdminHistoryDisclosure({ application }: { application: Application }) {
  const [open, setOpen] = useState(false)
  const historyQuery = useApplicationHistory(application.id, open)

  // GET .../history is owner-only on the backend — for bank roles it 404s;
  // hide the block entirely in that case (verified against live backend).
  if (historyQuery.isError) return null

  return (
    <div className="rounded-lg border border-border">
      <button
        type="button"
        onClick={() => setOpen((prev) => !prev)}
        className="flex w-full cursor-pointer items-center justify-between px-3 py-2 text-xs font-bold"
      >
        История статусов
        <ChevronDownIcon className={cn('size-3.5 transition-transform', open && 'rotate-180')} />
      </button>
      {open && (
        <div className="flex flex-col gap-2 border-t border-border px-3 py-2">
          {historyQuery.isLoading && <Skeleton className="h-4 w-full" />}
          {historyQuery.data?.map((entry) => (
            <div key={entry.id} className="flex flex-col gap-0.5">
              <span className="text-xs font-medium">
                {entry.fromStatus
                  ? (STATUS_LABELS[entry.fromStatus as ApplicationStatus] ?? entry.fromStatus)
                  : '—'}{' '}
                → {STATUS_LABELS[entry.toStatus as ApplicationStatus] ?? entry.toStatus}
                <span className="ml-2 font-normal text-text-secondary">
                  {formatDateTime(entry.createdAt)} · {entry.actorType}
                </span>
              </span>
              {entry.comment && (
                <span className="text-[11px] leading-relaxed text-text-secondary">
                  {entry.comment}
                </span>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/**
 * Right column of the АРМ: full application details for bank roles —
 * score/factors/client_data are bank-visible here (visibility.ts).
 */
export function AdminApplicationDetails() {
  const role = useSession((s) => s.user?.role)
  const statusFilter = useAdminQueueStore((s) => s.statusFilter)
  const selectedId = useAdminQueueStore((s) => s.selectedId)
  const queueQuery = useAdminQueue(statusFilter)
  const application = queueQuery.data?.find((a) => a.id === selectedId) ?? null

  if (application == null) {
    return (
      <section className="flex min-w-0 flex-1 flex-col items-center justify-center gap-3 rounded-xl border border-border bg-bg-primary text-center shadow-card">
        <p className="text-lg font-bold">Выберите заявку из очереди</p>
        <p className="max-w-sm text-sm text-text-secondary">
          Слева — все заявки клиентов банка. Очередь обновляется автоматически каждые 15 секунд.
        </p>
      </section>
    )
  }

  const noActionHint = ADMIN_NO_ACTION_HINTS[application.status]
  const showManager = role === 'bank_manager'
  const showAnalyst = role === 'bank_analyst'

  return (
    <section className="flex min-w-0 flex-1 flex-col gap-4 overflow-y-auto rounded-xl border border-border bg-bg-primary p-5 shadow-card">
      <div className="flex flex-wrap items-center gap-3">
        <h2 className="text-lg font-bold">Заявка № {application.id}</h2>
        <Badge variant={STATUS_BADGE_VARIANTS[application.status]}>
          {STATUS_LABELS[application.status]}
        </Badge>
        {application.score != null && (
          <Badge variant="info">Балл скоринга: {application.score}</Badge>
        )}
        {application.decision && (
          <Badge variant="neutral">
            Решение:{' '}
            {STATUS_LABELS[application.decision as ApplicationStatus] ?? application.decision}
          </Badge>
        )}
      </div>

      <Section title="Параметры">
        <Row label="Продукт" value={application.productName} />
        <Row label="Сумма" value={formatMoney(application.requestedAmount)} />
        <Row label="Срок" value={`${application.termMonths} мес.`} />
        <Row label="Платёж в месяц" value={formatMoney(application.monthlyPayment)} />
        <Row label="Всего к возврату" value={formatMoney(application.totalRepayment)} />
        <Row label="Переплата" value={formatMoney(application.overpayment)} />
        <Row label="Обновлена" value={formatDateTime(application.updatedAt)} />
      </Section>

      <ClientDataSection clientData={application.clientData} />
      <DecisionBreakdown application={application} />

      {showManager && <ManagerActions application={application} />}
      {showAnalyst && <AnalystActions application={application} />}
      {((showManager && !['data_check', 'scoring', 'manual_review'].includes(application.status)) ||
        (showAnalyst && application.status !== 'manual_review') ||
        (!showManager && !showAnalyst)) && (
        <p className="rounded-lg bg-bg-secondary px-3 py-2 text-xs leading-relaxed text-text-secondary">
          {noActionHint}
        </p>
      )}

      <AnalystExplainBlock application={application} />
      <AdminHistoryDisclosure application={application} />
    </section>
  )
}
