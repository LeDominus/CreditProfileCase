import type { Metadata } from 'next'
import type { ReactNode } from 'react'

import { RootShell } from '@/fsd/app/root-shell'
import { AuthGate } from '@/fsd/features/auth/auth-gate'
import { AppChrome } from '@/fsd/widgets/app-chrome/app-chrome'

export const metadata: Metadata = {
  title: 'Кабинет клиента — Умный кредитный кабинет',
}

export default function ClientLayout({ children }: { children: ReactNode }) {
  return (
    <RootShell>
      <AuthGate allow={['client']}>
        <AppChrome title="Умный кредитный кабинет">{children}</AppChrome>
      </AuthGate>
    </RootShell>
  )
}
