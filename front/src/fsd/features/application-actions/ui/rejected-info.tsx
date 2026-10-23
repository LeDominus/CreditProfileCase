'use client'

import { AlertTriangleIcon } from 'lucide-react'

import type { Application } from '@/fsd/entities/application/model/schemas'
import { useMyProfile } from '@/fsd/entities/profile/model/queries'
import { useCreateAlternative } from '@/fsd/features/application-actions/model/use-application-actions'
import { formatMoney, formatRate } from '@/fsd/shared/lib/format'
import { Button } from '@/fsd/shared/ui/button'

/**
 * rejected: stop-factors in plain language (NO score — bank-only) and
 * alternative products from decision_details with «Оформить заявку»
 * (creates a new draft on the alternative).
 */
export function RejectedInfo({ application }: { application: Application }) {
  const profileQuery = useMyProfile()
  const createAlternative = useCreateAlternative(profileQuery.data?.id ?? null)
  const details = application.decisionDetails
  const stopFactors = details?.stopFactors ?? []
  const alternatives = details?.alternatives ?? []

  return (
    <div className="flex flex-col gap-3">
      {stopFactors.length > 0 && (
        <div className="flex items-start gap-2 rounded-lg bg-negative/10 px-3 py-2">
          <AlertTriangleIcon className="mt-0.5 size-4 shrink-0 text-negative" />
          <div className="flex flex-col gap-0.5">
            <span className="text-xs font-bold text-negative">Отказ до скоринга</span>
            <span className="text-xs leading-relaxed text-negative">
              {stopFactors.map((factor) => factor.label).join('; ')}.
            </span>
          </div>
        </div>
      )}
      {!stopFactors.length && details?.explanation && (
        <p className="rounded-lg bg-negative/10 px-3 py-2 text-xs leading-relaxed text-negative">
          {details.explanation}
        </p>
      )}

      {alternatives.length > 0 && (
        <div className="flex flex-col gap-2">
          <p className="text-xs font-bold">Альтернативные предложения</p>
          <p className="text-[11px] leading-relaxed text-text-secondary">
            Запрошенный продукт не подошёл профилю бизнеса — вот ближайшие альтернативы банка.
          </p>
          {alternatives.map((alt) => (
            <div key={alt.id} className="flex flex-col gap-2 rounded-xl border border-border p-3">
              <div className="flex items-center justify-between gap-2">
                <span className="text-sm font-bold">{alt.name}</span>
                <span className="text-xs text-text-secondary">{formatRate(alt.rate)}</span>
              </div>
              <p className="text-xs text-text-secondary">
                {formatMoney(alt.amount)} на {alt.termMonths} мес · платёж ≈{' '}
                {formatMoney(alt.monthlyPayment)}/мес
                {alt.amountReduced ? ' · сумма снижена' : ''}
              </p>
              <Button
                size="sm"
                variant="outline"
                onClick={() => createAlternative.mutate(alt)}
                disabled={createAlternative.isPending}
              >
                {createAlternative.isPending ? 'Создаём…' : 'Оформить заявку'}
              </Button>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
