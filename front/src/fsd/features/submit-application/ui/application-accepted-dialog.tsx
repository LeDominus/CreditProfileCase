'use client'

import { CheckCircle2Icon } from 'lucide-react'

import { NEXT_STEP_HINTS, STATUS_LABELS } from '@/fsd/entities/application/model/status-labels'
import { useApplicationDraft } from '@/fsd/features/submit-application/model/draft-store'
import { formatMoney } from '@/fsd/shared/lib/format'
import { Badge } from '@/fsd/shared/ui/badge'
import { Button } from '@/fsd/shared/ui/button'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/fsd/shared/ui/dialog'
import { usePanelStore } from '@/fsd/widgets/right-panel/model/panel-store'

/**
 * «Заявка принята»: number, params, status with the next-step hint
 * (NEXT_STEP_HINTS), «Перейти к заявкам» switches the right panel to the
 * applications tab. Covers the draft-only case (submit failed) too.
 */
export function ApplicationAcceptedDialog() {
  const accepted = useApplicationDraft((s) => s.accepted)
  const setAccepted = useApplicationDraft((s) => s.setAccepted)
  const reset = useApplicationDraft((s) => s.reset)
  const setActiveTab = usePanelStore((s) => s.setActiveTab)

  const close = () => {
    setAccepted(null)
    reset()
  }

  const goToApplications = () => {
    setActiveTab('applications')
    close()
  }

  const application = accepted?.application
  const explanation = application?.decisionDetails?.explanation
  const hint = accepted?.submitted
    ? NEXT_STEP_HINTS[application?.status as keyof typeof NEXT_STEP_HINTS]
    : 'Заявка сохранена как черновик. Отправьте её на обработку во вкладке «Заявки», когда будете готовы.'

  return (
    <Dialog open={accepted != null} onOpenChange={(open) => !open && close()}>
      <DialogContent>
        <DialogHeader>
          <div className="flex items-center gap-2">
            <CheckCircle2Icon className="size-6 text-positive-dark" />
            <DialogTitle>Заявка принята</DialogTitle>
          </div>
        </DialogHeader>
        {application && (
          <div className="flex flex-col gap-4">
            <p className="text-sm">Ваша заявка принята. Данные направлены в банк.</p>
            <div className="grid grid-cols-3 gap-3 rounded-xl bg-bg-secondary p-3 text-center">
              <div className="flex flex-col gap-0.5">
                <span className="text-[11px] text-text-secondary">Сумма</span>
                <span className="text-sm font-bold">
                  {formatMoney(application.requestedAmount)}
                </span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-[11px] text-text-secondary">Срок</span>
                <span className="text-sm font-bold">{application.termMonths} мес.</span>
              </div>
              <div className="flex flex-col gap-0.5">
                <span className="text-[11px] text-text-secondary">Платёж</span>
                <span className="text-sm font-bold">{formatMoney(application.monthlyPayment)}</span>
              </div>
            </div>
            <div className="flex flex-wrap items-center gap-2 text-sm">
              <span className="font-medium">{application.productName}</span>
              <span className="text-text-secondary">·</span>
              <span className="text-text-secondary">Заявка № {application.id}</span>
              <Badge variant="info">{STATUS_LABELS[application.status]}</Badge>
            </div>
            {hint && (
              <p className="rounded-lg bg-info/10 px-3 py-2 text-xs leading-relaxed text-info">
                {hint}
              </p>
            )}
            {typeof explanation === 'string' && explanation && (
              <p className="text-xs text-text-secondary">{explanation}</p>
            )}
            <p className="text-[11px] text-text-secondary">
              Отправка заявки не означает одобрение кредита. Решение демонстрационное и не является
              офертой банка.
            </p>
            <div className="flex justify-end gap-2">
              <Button variant="ghost" onClick={close}>
                Закрыть
              </Button>
              <Button onClick={goToApplications}>Перейти к заявкам</Button>
            </div>
          </div>
        )}
      </DialogContent>
    </Dialog>
  )
}
