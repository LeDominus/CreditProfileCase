import type { ComponentProps } from 'react'

import { cn } from '@/fsd/shared/lib/utils'

function Textarea({ className, ...props }: ComponentProps<'textarea'>) {
  return (
    <textarea
      data-slot="textarea"
      className={cn(
        'min-h-20 w-full min-w-0 rounded-lg border border-border bg-bg-primary px-3 py-2 text-sm text-text-primary transition-colors outline-none placeholder:text-text-secondary focus-visible:border-accent focus-visible:ring-3 focus-visible:ring-accent/20 disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-negative aria-invalid:ring-3 aria-invalid:ring-negative/15',
        className,
      )}
      {...props}
    />
  )
}

export { Textarea }
