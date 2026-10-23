import type { Metadata } from 'next'
import type { ReactNode } from 'react'

import { RootShell } from '@/fsd/app/root-shell'
import { GuestGate } from '@/fsd/features/auth/guest-gate'

export const metadata: Metadata = {
  title: 'Вход — Умный кредитный кабинет',
}

export default function AuthLayout({ children }: { children: ReactNode }) {
  return (
    <RootShell>
      <GuestGate>{children}</GuestGate>
    </RootShell>
  )
}
