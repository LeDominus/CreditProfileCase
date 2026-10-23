import { cva, type VariantProps } from 'class-variance-authority'
import type { ComponentProps } from 'react'

import { cn } from '@/fsd/shared/lib/utils'

const badgeVariants = cva(
  'inline-flex w-fit shrink-0 items-center justify-center gap-1 rounded-pill px-2.5 py-0.5 text-xs font-medium whitespace-nowrap [&_svg]:size-3',
  {
    variants: {
      variant: {
        neutral: 'bg-bg-secondary text-text-secondary',
        accent: 'bg-accent/10 text-accent',
        positive: 'bg-positive/10 text-positive-dark',
        negative: 'bg-negative/10 text-negative',
        attention: 'bg-attention/10 text-attention',
        info: 'bg-info/10 text-info',
        outline: 'border border-border text-text-primary',
      },
    },
    defaultVariants: {
      variant: 'neutral',
    },
  },
)

function Badge({
  className,
  variant = 'neutral',
  ...props
}: ComponentProps<'span'> & VariantProps<typeof badgeVariants>) {
  return <span data-slot="badge" className={cn(badgeVariants({ variant, className }))} {...props} />
}

export { Badge, badgeVariants }
