'use client'

import type { Application } from '@/fsd/entities/application/model/schemas'
import { useRescore } from '@/fsd/features/application-actions/model/use-application-actions'
import { Button } from '@/fsd/shared/ui/button'

/**
 * needs_info: the reason (manager's needs_info_reason or scoring
 * missing_fields) + «Обработать повторно» after the profile is completed.
 */
export function NeedsInfoActions({ application }: { application: Application }) {
  const rescore = useRescore(application.id)
  const details = application.decisionDetails
  const missing = details?.missingFields ?? []

  return (
    <div className="flex flex-col gap-2">
      {details?.needsInfoReason && (
        <p className="rounded-lg bg-attention/10 px-3 py-2 text-xs leading-relaxed text-attention">
          Запрос сотрудника банка: {details.needsInfoReason}
        </p>
      )}
      <p className="rounded-lg bg-attention/10 px-3 py-2 text-xs leading-relaxed text-attention">
        Уточните данные о бизнесе в диалоге с ассистентом
        {missing.length > 0 ? `: ${missing.join(', ')}` : ''} — затем отправьте заявку на повторную
        обработку.
      </p>
      <Button
        size="sm"
        variant="outline"
        onClick={() => rescore.mutate()}
        disabled={rescore.isPending}
      >
        {rescore.isPending ? 'Обрабатываем…' : 'Обработать повторно'}
      </Button>
    </div>
  )
}
