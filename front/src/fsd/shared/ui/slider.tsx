'use client'

import { Slider as SliderPrimitive } from '@base-ui/react/slider'

import { cn } from '@/fsd/shared/lib/utils'

function Slider({ className, ...props }: SliderPrimitive.Root.Props) {
  return (
    <SliderPrimitive.Root
      data-slot="slider"
      className={cn('flex w-full touch-none items-center select-none', className)}
      {...props}
    >
      <SliderPrimitive.Control className="flex w-full items-center py-2">
        <SliderPrimitive.Track className="relative h-1.5 w-full rounded-full bg-border">
          <SliderPrimitive.Indicator className="absolute h-full rounded-full bg-accent" />
          <SliderPrimitive.Thumb className="block size-4 rounded-full border border-accent bg-bg-primary shadow-card transition-colors outline-none focus-visible:ring-3 focus-visible:ring-accent/20" />
        </SliderPrimitive.Track>
      </SliderPrimitive.Control>
    </SliderPrimitive.Root>
  )
}

export { Slider }
