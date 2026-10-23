'use client'

import type { Application, ApplicationStatus } from '@/fsd/entities/application/model/schemas'
import { NEXT_STEP_HINTS, PIPELINE_STEPS } from '@/fsd/entities/application/model/status-labels'
import { cn } from '@/fsd/shared/lib/utils'

/** In-work statuses: pipeline step indicator + next-step hint. */
export function InProgressInfo({ application }: { application: Application }) {
  const status = application.status
  const currentIndex = PIPELINE_STEPS.findIndex((step) => step.status === status)
  // manual_review sits after scoring in the flow.
  const activeIndex = status === 'manual_review' ? PIPELINE_STEPS.length - 1 : currentIndex
  const hint = NEXT_STEP_HINTS[status as ApplicationStatus]

  return (
    <div className="flex flex-col gap-2">
      <div className="flex items-center gap-1">
        {PIPELINE_STEPS.map((step, index) => (
          <div key={step.status} className="flex flex-1 flex-col gap-1">
            <div
              className={cn('h-1 rounded-full', index <= activeIndex ? 'bg-info' : 'bg-border')}
            />
            <span
              className={cn(
                'text-[10px] leading-tight',
                index === activeIndex ? 'font-bold text-info' : 'text-text-secondary',
              )}
            >
              {step.label}
            </span>
          </div>
        ))}
      </div>
      {hint && (
        <p className="rounded-lg bg-info/10 px-3 py-2 text-xs leading-relaxed text-info">{hint}</p>
      )}
    </div>
  )
}
