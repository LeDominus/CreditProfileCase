'use client'

import { useState } from 'react'

import type { Application } from '@/fsd/entities/application/model/schemas'
import { useOfferResponse } from '@/fsd/features/application-actions/model/use-application-actions'
import { formatMoney } from '@/fsd/shared/lib/format'
import { Button } from '@/fsd/shared/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/fsd/shared/ui/dialog'
import { Textarea } from '@/fsd/shared/ui/textarea'

function DeclineDialog({
  applicationId,
  open,
  onClose,
}: {
  applicationId: number
  open: boolean
  onClose: () => void
}) {
  const offerResponse = useOfferResponse(applicationId)
  const [reason, setReason] = useState('')
  const [error, setError] = useState<string | null>(null)

  const handleDecline = () => {
    if (reason.trim().length < 3) {
      setError('Укажите причину отказа (от 3 символов)')
      return
    }
    setError(null)
    offerResponse.mutate({ accept: false, declineReason: reason.trim() }, { onSuccess: onClose })
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Отклонить предложение</DialogTitle>
          <DialogDescription>
            Укажите причину — банк учтёт её в дальнейшей работе с вами.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          <Textarea
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            placeholder="Например: не устраивает ставка"
            aria-invalid={Boolean(error)}
          />
          {error && <p className="text-xs text-negative">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={onClose} disabled={offerResponse.isPending}>
              Отмена
            </Button>
            <Button
              size="sm"
              variant="destructive"
              onClick={handleDecline}
              disabled={offerResponse.isPending}
            >
              {offerResponse.isPending ? 'Отправляем…' : 'Отклонить предложение'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

function OfferRow({ label, value, changed }: { label: string; value: string; changed?: boolean }) {
  return (
    <div className="flex items-baseline justify-between text-sm">
      <span className="text-xs text-text-secondary">{label}</span>
      <span className={changed ? 'font-bold text-accent' : 'font-medium'}>{value}</span>
    </div>
  )
}

/**
 * offer_ready: the bank's offer. For approved_with_changes the suggested
 * terms are shown as «было → стало» against the requested ones.
 */
export function OfferActions({ application }: { application: Application }) {
  const offerResponse = useOfferResponse(application.id)
  const [declineOpen, setDeclineOpen] = useState(false)

  const details = application.decisionDetails
  const withChanges =
    details?.decision === 'approved_with_changes' && details.suggestedAmount != null

  const offerAmount = withChanges
    ? (details?.suggestedAmount as number)
    : application.requestedAmount
  const offerTerm = withChanges
    ? (details?.suggestedTermMonths ?? application.termMonths)
    : application.termMonths
  const offerPayment = withChanges
    ? (details?.suggestedMonthlyPayment ?? application.monthlyPayment)
    : application.monthlyPayment

  return (
    <div className="flex flex-col gap-3">
      <div className="flex flex-col gap-1.5 rounded-lg bg-positive/10 p-3">
        <p className="text-xs font-bold text-positive-dark">Предложение банка</p>
        {withChanges && (
          <p className="text-[11px] leading-relaxed text-text-secondary">
            Одобрено на иных условиях: запрошено {formatMoney(application.requestedAmount)} на{' '}
            {application.termMonths} мес. (платёж {formatMoney(application.monthlyPayment)}/мес)
          </p>
        )}
        <OfferRow
          label="Сумма"
          value={formatMoney(offerAmount)}
          changed={withChanges && offerAmount !== application.requestedAmount}
        />
        <OfferRow
          label="Срок"
          value={`${offerTerm} мес.`}
          changed={withChanges && offerTerm !== application.termMonths}
        />
        <OfferRow
          label="Платёж в месяц"
          value={formatMoney(offerPayment)}
          changed={withChanges && offerPayment !== application.monthlyPayment}
        />
        {!withChanges && (
          <OfferRow label="Переплата" value={formatMoney(application.overpayment)} />
        )}
      </div>
      <div className="flex gap-2">
        <Button
          size="sm"
          className="flex-1"
          onClick={() => offerResponse.mutate({ accept: true })}
          disabled={offerResponse.isPending}
        >
          {offerResponse.isPending ? 'Отправляем…' : 'Принять условия'}
        </Button>
        <Button
          size="sm"
          variant="outline"
          className="flex-1"
          onClick={() => setDeclineOpen(true)}
          disabled={offerResponse.isPending}
        >
          Отклонить
        </Button>
      </div>
      {declineOpen && (
        <DeclineDialog
          applicationId={application.id}
          open={declineOpen}
          onClose={() => setDeclineOpen(false)}
        />
      )}
    </div>
  )
}
