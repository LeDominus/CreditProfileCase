'use client'

import { ChevronDownIcon, SparklesIcon } from 'lucide-react'
import { useState } from 'react'

import type { Application } from '@/fsd/entities/application/model/schemas'
import { useExplain } from '@/fsd/features/application-actions/model/use-application-actions'
import { cn } from '@/fsd/shared/lib/utils'
import { Button } from '@/fsd/shared/ui/button'
import { Markdown } from '@/fsd/shared/ui/markdown'

/**
 * «Объяснить решение (ИИ)»: slow LLM endpoint — locked spinner button while
 * pending, result renders as markdown inline. Rendered only when the bank
 * has made a decision (409 otherwise).
 */
export function ExplainBlock({ application }: { application: Application }) {
  const explain = useExplain(application.id)
  const [expanded, setExpanded] = useState(true)

  if (application.decision == null) return null

  const result = explain.data

  return (
    <div className="flex flex-col gap-2">
      <Button
        size="sm"
        variant="ghost"
        onClick={() => explain.mutate()}
        disabled={explain.isPending}
      >
        <SparklesIcon />
        {explain.isPending ? 'Ассистент анализирует решение…' : 'Объяснить решение (ИИ)'}
      </Button>
      {result && (
        <div className="rounded-lg border border-border">
          <button
            type="button"
            onClick={() => setExpanded((prev) => !prev)}
            className="flex w-full cursor-pointer items-center justify-between px-3 py-2 text-xs font-bold"
          >
            Объяснение ассистента
            <ChevronDownIcon
              className={cn('size-3.5 transition-transform', expanded && 'rotate-180')}
            />
          </button>
          {expanded && (
            <div className="border-t border-border px-3 py-2 text-sm">
              <Markdown content={result.explanation} />
              {result.source === 'fallback' && (
                <p className="mt-2 text-[11px] text-text-secondary">
                  Сформулировано автоматически без участия ИИ.
                </p>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  )
}
