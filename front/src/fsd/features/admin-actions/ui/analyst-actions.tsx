'use client'

import { useState } from 'react'

import type { AnalystDecisionValue } from '@/fsd/entities/application/api/application-api'
import type { Application } from '@/fsd/entities/application/model/schemas'
import { useDecision } from '@/fsd/features/admin-actions/model/use-admin-actions'
import { cn } from '@/fsd/shared/lib/utils'
import { Button } from '@/fsd/shared/ui/button'
import { Textarea } from '@/fsd/shared/ui/textarea'

const REASON_MIN = 3
const REASON_MAX = 1000

const DECISION_OPTIONS: { value: AnalystDecisionValue; label: string; hint?: string }[] = [
  { value: 'approved', label: 'Одобрить' },
  {
    value: 'approved_with_changes',
    label: 'Одобрить с изменениями',
    hint: 'Условия будут скорректированы бэкендом — клиент увидит скорректированное предложение.',
  },
  { value: 'rejected', label: 'Отклонить' },
]

/** bank_analyst actions (manual_review only): decision + mandatory reason. */
export function AnalystActions({ application }: { application: Application }) {
  const decisionMutation = useDecision(application.id)
  const [decision, setDecision] = useState<AnalystDecisionValue>('approved')
  const [reason, setReason] = useState('')

  if (application.status !== 'manual_review') return null

  const isValid = reason.trim().length >= REASON_MIN
  const selectedHint = DECISION_OPTIONS.find((o) => o.value === decision)?.hint

  return (
    <div className="flex flex-col gap-3">
      <p className="text-xs font-bold tracking-wider text-text-secondary uppercase">
        Решение аналитика
      </p>
      <div className="flex gap-1 rounded-pill bg-bg-secondary p-1">
        {DECISION_OPTIONS.map((option) => (
          <button
            key={option.value}
            type="button"
            onClick={() => setDecision(option.value)}
            className={cn(
              'h-8 flex-1 cursor-pointer rounded-pill px-3 text-xs font-medium whitespace-nowrap transition-colors',
              decision === option.value
                ? 'bg-bg-primary text-text-primary shadow-card'
                : 'text-text-secondary hover:text-text-primary',
            )}
          >
            {option.label}
          </button>
        ))}
      </div>
      {selectedHint && (
        <p className="rounded-lg bg-attention/10 px-3 py-2 text-xs leading-relaxed text-attention">
          {selectedHint}
        </p>
      )}
      <div className="flex flex-col gap-1">
        <label htmlFor="analyst-reason" className="text-xs font-medium">
          Причина решения (обязательна)
        </label>
        <Textarea
          id="analyst-reason"
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value.slice(0, REASON_MAX))}
          placeholder="Например: одобрено при снижении суммы до 800000"
        />
        <span className="text-right text-[11px] text-text-secondary">
          {reason.trim().length}/{REASON_MAX} (минимум {REASON_MIN})
        </span>
      </div>
      <Button
        size="sm"
        onClick={() => decisionMutation.mutate({ decision, reason: reason.trim() })}
        disabled={!isValid || decisionMutation.isPending}
      >
        {decisionMutation.isPending ? 'Фиксируем…' : 'Принять решение'}
      </Button>
    </div>
  )
}
