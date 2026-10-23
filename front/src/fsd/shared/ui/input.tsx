import type { ComponentProps } from 'react'

import { cn } from '@/fsd/shared/lib/utils'

function Input({ className, type, ...props }: ComponentProps<'input'>) {
  return (
    <input
      type={type}
      data-slot="input"
      className={cn(
        'h-10 w-full min-w-0 rounded-lg border border-border bg-bg-primary px-3 text-sm text-text-primary transition-colors outline-none placeholder:text-text-secondary focus-visible:border-accent focus-visible:ring-3 focus-visible:ring-accent/20 disabled:pointer-events-none disabled:opacity-50 aria-invalid:border-negative aria-invalid:ring-3 aria-invalid:ring-negative/15',
        className,
      )}
      {...props}
    />
  )
}

export { Input }
