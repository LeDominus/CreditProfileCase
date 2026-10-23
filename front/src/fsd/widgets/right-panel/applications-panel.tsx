'use client'

import { BadgeCheckIcon, FileTextIcon, RefreshCwIcon } from 'lucide-react'

import { useMyApplications } from '@/fsd/entities/application/model/queries'
import type { Application } from '@/fsd/entities/application/model/schemas'
import {
  IN_PROGRESS_STATUSES,
  STATUS_BADGE_VARIANTS,
  STATUS_LABELS,
} from '@/fsd/entities/application/model/status-labels'
import { DraftActions } from '@/fsd/features/application-actions/ui/draft-actions'
import { ExplainBlock } from '@/fsd/features/application-actions/ui/explain-block'
import { HistoryDisclosure } from '@/fsd/features/application-actions/ui/history-disclosure'
import { InProgressInfo } from '@/fsd/features/application-actions/ui/in-progress-info'
import { NeedsInfoActions } from '@/fsd/features/application-actions/ui/needs-info-actions'
import { OfferActions } from '@/fsd/features/application-actions/ui/offer-actions'
import { RejectedInfo } from '@/fsd/features/application-actions/ui/rejected-info'
import { SignAction } from '@/fsd/features/application-actions/ui/sign-action'
import { formatDateTime, formatMoney } from '@/fsd/shared/lib/format'
import { Badge } from '@/fsd/shared/ui/badge'
import { Button } from '@/fsd/shared/ui/button'
import { Skeleton } from '@/fsd/shared/ui/skeleton'

function IssuedInfo({ application }: { application: Application }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-positive/10 px-3 py-2">
      <BadgeCheckIcon className="mt-0.5 size-4 shrink-0 text-positive-dark" />
      <div className="flex flex-col gap-0.5">
        <span className="text-xs font-bold text-positive-dark">Кредит выдан</span>
        <span className="text-xs leading-relaxed text-text-secondary">
          {formatMoney(application.requestedAmount)} · платёж{' '}
          {formatMoney(application.monthlyPayment)}
          /мес · {formatDateTime(application.updatedAt)}
        </span>
      </div>
    </div>
  )
}

function ClientDeclinedInfo() {
  return (
    <p className="rounded-lg bg-bg-secondary px-3 py-2 text-xs leading-relaxed text-text-secondary">
      Вы отклонили предложение банка. Можно оформить новую заявку — выберите продукт во вкладке
      «Продукты».
    </p>
  )
}

function StatusActions({ application }: { application: Application }) {
  switch (application.status) {
    case 'draft':
      return <DraftActions application={application} />
    case 'needs_info':
      return <NeedsInfoActions application={application} />
    case 'offer_ready':
      return <OfferActions application={application} />
    case 'accepted':
      return <SignAction application={application} />
    case 'issued':
      return <IssuedInfo application={application} />
    case 'rejected':
      return <RejectedInfo application={application} />
    case 'client_declined':
      return <ClientDeclinedInfo />
    default:
      if (IN_PROGRESS_STATUSES.includes(application.status)) {
        return <InProgressInfo application={application} />
      }
      return null
  }
}

function ApplicationCard({ application }: { application: Application }) {
  return (
    <div className="flex flex-col gap-3 rounded-xl border border-border p-3.5">
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-bold">Заявка № {application.id}</span>
        <Badge variant={STATUS_BADGE_VARIANTS[application.status]}>
          {STATUS_LABELS[application.status]}
        </Badge>
      </div>
      <p className="text-xs text-text-secondary">{application.productName}</p>
      <div className="flex flex-col gap-1">
        <div className="flex items-baseline justify-between text-sm">
          <span className="text-xs text-text-secondary">Сумма</span>
          <span className="font-medium">{formatMoney(application.requestedAmount)}</span>
        </div>
        <div className="flex items-baseline justify-between text-sm">
          <span className="text-xs text-text-secondary">Срок</span>
          <span className="font-medium">{application.termMonths} мес.</span>
        </div>
        <div className="flex items-baseline justify-between text-sm">
          <span className="text-xs text-text-secondary">Платёж в месяц</span>
          <span className="font-medium">{formatMoney(application.monthlyPayment)}</span>
        </div>
      </div>
      <p className="text-[11px] text-text-secondary">
        Обновлена {formatDateTime(application.updatedAt)}
      </p>

      <StatusActions application={application} />
      <ExplainBlock application={application} />
      <HistoryDisclosure application={application} />
    </div>
  )
}

/**
 * Right-panel tab «Заявки»: all client applications with live status sync
 * (refetchInterval — bank decisions surface without client actions).
 */
export function ApplicationsPanel() {
  const applicationsQuery = useMyApplications()

  return (
    <div className="flex flex-col gap-3">
      <Button
        size="sm"
        variant="ghost"
        onClick={() => applicationsQuery.refetch()}
        disabled={applicationsQuery.isFetching}
      >
        <RefreshCwIcon className={applicationsQuery.isFetching ? 'animate-spin' : undefined} />
        {applicationsQuery.isFetching ? 'Обновляем…' : 'Обновить'}
      </Button>

      {applicationsQuery.isLoading && (
        <>
          <Skeleton className="h-40 w-full rounded-xl" />
          <Skeleton className="h-40 w-full rounded-xl" />
        </>
      )}

      {applicationsQuery.data?.length === 0 && (
        <div className="flex flex-col items-center gap-3 py-10 text-center">
          <span className="inline-flex size-11 items-center justify-center rounded-full bg-info/10 text-info">
            <FileTextIcon className="size-5" />
          </span>
          <p className="text-sm font-bold">Заявок пока нет</p>
          <p className="max-w-[260px] text-xs leading-relaxed text-text-secondary">
            Когда вы выберете продукт из подбора и оформите заявку, её статус будет отслеживаться
            здесь.
          </p>
        </div>
      )}

      {applicationsQuery.data?.map((application) => (
        <ApplicationCard key={application.id} application={application} />
      ))}
    </div>
  )
}
