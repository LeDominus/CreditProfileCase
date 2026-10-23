'use client'

import type { Application } from '@/fsd/entities/application/model/schemas'
import { useSign } from '@/fsd/features/application-actions/model/use-application-actions'
import { Button } from '@/fsd/shared/ui/button'

/** accepted: «Подписать договор» — ЭП моделируется кнопкой (→ issued). */
export function SignAction({ application }: { application: Application }) {
  const sign = useSign(application.id)

  return (
    <div className="flex flex-col gap-2">
      <p className="text-xs leading-relaxed text-text-secondary">
        Условия приняты. Подпишите кредитный договор — электронная подпись моделируется кнопкой.
      </p>
      <Button size="sm" onClick={() => sign.mutate()} disabled={sign.isPending}>
        {sign.isPending ? 'Подписываем…' : 'Подписать договор'}
      </Button>
    </div>
  )
}
