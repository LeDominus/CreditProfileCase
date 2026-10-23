import type { Metadata } from 'next'
import type { ReactNode } from 'react'

import { RootShell } from '@/fsd/app/root-shell'
import { AuthGate } from '@/fsd/features/auth/auth-gate'
import { AppChrome } from '@/fsd/widgets/app-chrome/app-chrome'

export const metadata: Metadata = {
  title: 'АРМ — Умный кредитный кабинет',
}

export default function BankLayout({ children }: { children: ReactNode }) {
  return (
    <RootShell>
      <AuthGate allow={['bank_manager', 'bank_analyst']}>
        <AppChrome title="АРМ сотрудника банка">{children}</AppChrome>
      </AuthGate>
    </RootShell>
  )
}
