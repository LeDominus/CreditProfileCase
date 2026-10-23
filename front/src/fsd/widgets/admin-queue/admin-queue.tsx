'use client'

import { RefreshCwIcon } from 'lucide-react'
import { useEffect } from 'react'
import { toast } from 'sonner'

import { useAdminQueue } from '@/fsd/entities/application/model/admin-queries'
import { type Application, applicationStatusSchema } from '@/fsd/entities/application/model/schemas'
import {
  STATUS_BADGE_VARIANTS,
  STATUS_LABELS,
} from '@/fsd/entities/application/model/status-labels'
import { useSession } from '@/fsd/entities/session/model/session-store'
import { formatDateTime, formatMoney } from '@/fsd/shared/lib/format'
import { cn } from '@/fsd/shared/lib/utils'
import { Badge } from '@/fsd/shared/ui/badge'
import { Button } from '@/fsd/shared/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/fsd/shared/ui/select'
import { Skeleton } from '@/fsd/shared/ui/skeleton'

import { useAdminQueueStore } from './model/admin-queue-store'

const ALL_STATUSES = 'all'

/** Manager acts in data_check/scoring/manual_review, analyst in manual_review. */
function actionableCount(applications: Application[], role: string | undefined): number {
  const statuses =
    role === 'bank_analyst' ? ['manual_review'] : ['data_check', 'scoring', 'manual_review']
  return applications.filter((a) => statuses.includes(a.status)).length
}

/**
 * Left column of the АРМ: status-filtered, auto-refreshing application
 * queue. Selection lives in admin-queue-store; a selection that drops out
 * of the filtered queue is reset with a notice.
 */
export function AdminQueue() {
  const role = useSession((s) => s.user?.role)
  const statusFilter = useAdminQueueStore((s) => s.statusFilter)
  const setStatusFilter = useAdminQueueStore((s) => s.setStatusFilter)
  const selectedId = useAdminQueueStore((s) => s.selectedId)
  const setSelectedId = useAdminQueueStore((s) => s.setSelectedId)

  const queueQuery = useAdminQueue(statusFilter)
  // Unfiltered queue powers the «требуют действий» counter.
  const allQuery = useAdminQueue(null)

  const applications = queueQuery.data

  // Reset the selection when it disappears from the filtered queue.
  useEffect(() => {
    if (selectedId == null || !applications) return
    if (!applications.some((a) => a.id === selectedId)) {
      setSelectedId(null)
      toast.info('Выбранная заявка больше не соответствует фильтру или изменила статус')
    }
  }, [applications, selectedId, setSelectedId])

  const actionable = actionableCount(allQuery.data ?? [], role)

  return (
    <section className="flex w-[380px] shrink-0 flex-col overflow-hidden rounded-xl border border-border bg-bg-primary shadow-card">
      <div className="flex flex-col gap-3 border-b border-border px-4 py-3.5">
        <div className="flex items-center justify-between gap-2">
          <h2 className="text-sm font-bold">Очередь заявок</h2>
          <Badge variant="attention">Требуют действий: {actionable}</Badge>
        </div>
        <div className="flex items-center gap-2">
          <Select
            value={statusFilter ?? ALL_STATUSES}
            onValueChange={(value) => setStatusFilter(value === ALL_STATUSES ? null : value)}
          >
            <SelectTrigger aria-label="Фильтр по статусу">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={ALL_STATUSES}>Все статусы</SelectItem>
              {applicationStatusSchema.options.map((status) => (
                <SelectItem key={status} value={status}>
                  {STATUS_LABELS[status]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            variant="ghost"
            onClick={() => {
              queueQuery.refetch()
              allQuery.refetch()
            }}
            disabled={queueQuery.isFetching}
          >
            <RefreshCwIcon className={queueQuery.isFetching ? 'animate-spin' : undefined} />
            Обновить
          </Button>
        </div>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-2 overflow-y-auto px-3 py-3">
        {queueQuery.isLoading && (
          <>
            <Skeleton className="h-20 w-full rounded-xl" />
            <Skeleton className="h-20 w-full rounded-xl" />
            <Skeleton className="h-20 w-full rounded-xl" />
          </>
        )}
        {applications?.length === 0 && (
          <p className="px-2 py-6 text-center text-xs text-text-secondary">
            Заявок по выбранному фильтру нет.
          </p>
        )}
        {applications?.map((application) => {
          const company = application.clientData?.company
          const isSelected = application.id === selectedId
          return (
            <button
              key={application.id}
              type="button"
              onClick={() => setSelectedId(application.id)}
              className={cn(
                'flex cursor-pointer flex-col gap-1.5 rounded-xl border px-3.5 py-3 text-left transition-colors',
                isSelected
                  ? 'border-accent bg-accent/5'
                  : 'border-border hover:border-border-strong hover:bg-bg-secondary',
              )}
            >
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-bold">№ {application.id}</span>
                <Badge variant={STATUS_BADGE_VARIANTS[application.status]}>
                  {STATUS_LABELS[application.status]}
                </Badge>
              </div>
              <span className="text-xs font-medium">{application.productName}</span>
              <span className="text-xs text-text-secondary">
                {formatMoney(application.requestedAmount)} · {application.termMonths} мес.
              </span>
              {company && (
                <span className="truncate text-xs text-text-secondary">
                  {company.companyName} · ИНН {company.inn}
                </span>
              )}
              <span className="text-[11px] text-text-secondary">
                Обновлена {formatDateTime(application.updatedAt)}
              </span>
            </button>
          )
        })}
      </div>
    </section>
  )
}
