'use client'

import type { ReactNode } from 'react'
import { Toaster } from 'sonner'

import { SessionBootstrap } from '@/fsd/features/auth/session-bootstrap'

import { QueryProvider } from './query-provider'

/** Client-side providers for the whole app. */
export function Providers({ children }: { children: ReactNode }) {
  return (
    <QueryProvider>
      {children}
      <SessionBootstrap />
      <Toaster position="top-right" richColors closeButton />
    </QueryProvider>
  )
}
