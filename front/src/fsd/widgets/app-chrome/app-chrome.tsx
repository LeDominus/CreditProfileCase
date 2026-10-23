'use client'

import type { ReactNode } from 'react'

import { useSession } from '@/fsd/entities/session/model/session-store'
import { ROLE_LABELS } from '@/fsd/entities/user/model/role-labels'
import { LogoutButton } from '@/fsd/features/auth/logout-button'
import { Badge } from '@/fsd/shared/ui/badge'

export function AlfaLogo({ size = 'md' }: { size?: 'md' | 'lg' }) {
  const box = size === 'lg' ? 'size-12 rounded-2xl text-2xl' : 'size-9 rounded-xl text-lg'
  return (
    <span
      className={`inline-flex shrink-0 items-center justify-center bg-accent font-bold text-white ${box}`}
      aria-hidden
    >
      A
    </span>
  )
}

/**
 * Top chrome for the authenticated areas (client cabinet and bank АРМ):
 * brand, current user with role badge, logout. Sidebar/panels of the final
 * layout arrive in later stages on top of this shell.
 */
export function AppChrome({ title, children }: { title: string; children: ReactNode }) {
  const user = useSession((s) => s.user)

  return (
    <div className="flex min-h-screen flex-col bg-bg-secondary">
      <header className="sticky top-0 z-40 flex h-16 items-center gap-3 border-b border-border bg-bg-primary px-6">
        <AlfaLogo />
        <div className="flex flex-col">
          <span className="text-sm leading-tight font-bold">Альфа-Банк</span>
          <span className="text-xs leading-tight text-text-secondary">{title}</span>
        </div>
        <div className="ml-auto flex items-center gap-3">
          {user && (
            <>
              <Badge variant="accent">{ROLE_LABELS[user.role]}</Badge>
              <span className="text-sm font-medium">{user.username}</span>
            </>
          )}
          <LogoutButton />
        </div>
      </header>
      <main className="mx-auto w-full max-w-[1440px] flex-1 px-6 py-8">{children}</main>
    </div>
  )
}
