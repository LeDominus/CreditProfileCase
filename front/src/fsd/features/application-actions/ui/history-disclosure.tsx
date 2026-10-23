'use client'

import { ChevronDownIcon } from 'lucide-react'
import { useState } from 'react'
import { useApplicationHistory } from '@/fsd/entities/application/model/queries'
import type { Application, ApplicationStatus } from '@/fsd/entities/application/model/schemas'
import { STATUS_LABELS } from '@/fsd/entities/application/model/status-labels'
import { formatDateTime } from '@/fsd/shared/lib/format'
import { cn } from '@/fsd/shared/lib/utils'
import { Skeleton } from '@/fsd/shared/ui/skeleton'

function statusLabel(status: string | null): string {
  if (status == null) return '—'
  return STATUS_LABELS[status as ApplicationStatus] ?? status
}

/**
 * Status history of the client's own application (safe for the client:
 * transitions of their own request; factors/score stay hidden — see
 * entities/application/model/visibility.ts).
 */
export function HistoryDisclosure({ application }: { application: Application }) {
  const [open, setOpen] = useState(false)
  const historyQuery = useApplicationHistory(application.id, open)

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
          {historyQuery.isLoading && (
            <>
              <Skeleton className="h-4 w-full" />
              <Skeleton className="h-4 w-2/3" />
            </>
          )}
          {historyQuery.data?.length === 0 && (
            <p className="text-xs text-text-secondary">История пока пуста.</p>
          )}
          {historyQuery.data?.map((entry) => (
            <div key={entry.id} className="flex flex-col gap-0.5">
              <span className="text-xs font-medium">
                {statusLabel(entry.fromStatus)} → {statusLabel(entry.toStatus)}
                <span className="ml-2 font-normal text-text-secondary">
                  {formatDateTime(entry.createdAt)}
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
