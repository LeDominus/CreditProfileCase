'use client'

import { Checkbox as CheckboxPrimitive } from '@base-ui/react/checkbox'
import { CheckIcon } from 'lucide-react'

import { cn } from '@/fsd/shared/lib/utils'

function Checkbox({ className, ...props }: CheckboxPrimitive.Root.Props) {
  return (
    <CheckboxPrimitive.Root
      data-slot="checkbox"
      className={cn(
        'inline-flex size-5 shrink-0 cursor-pointer items-center justify-center rounded-sm border border-border-strong bg-bg-primary transition-colors outline-none focus-visible:ring-3 focus-visible:ring-accent/20 disabled:pointer-events-none disabled:opacity-50 data-[checked]:border-accent data-[checked]:bg-accent data-[checked]:text-white',
        className,
      )}
      {...props}
    >
      <CheckboxPrimitive.Indicator className="flex items-center justify-center">
        <CheckIcon className="size-3.5" />
      </CheckboxPrimitive.Indicator>
    </CheckboxPrimitive.Root>
  )
}

export { Checkbox }
