'use client'

import { useRouter } from 'next/navigation'
import { type ReactNode, useEffect } from 'react'

import { useSession } from '@/fsd/entities/session/model/session-store'
import type { UserRole } from '@/fsd/entities/user/model/schemas'
import { homeForRole, LOGIN_ROUTE } from '@/fsd/shared/config/routes'
import { Skeleton } from '@/fsd/shared/ui/skeleton'

function GateFallback() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 bg-bg-secondary">
      <div className="size-10 animate-pulse rounded-xl bg-accent" />
      <Skeleton className="h-4 w-40" />
    </div>
  )
}

/**
 * Route guard: no session → /login; a role outside `allow` → that role's
 * home page. Renders children only for an authenticated, allowed user.
 */
export function AuthGate({ allow, children }: { allow: UserRole[]; children: ReactNode }) {
  const router = useRouter()
  const status = useSession((s) => s.status)
  const user = useSession((s) => s.user)

  const allowed = status === 'auth' && user !== null && allow.includes(user.role)

  useEffect(() => {
    if (status === 'guest') {
      router.replace(LOGIN_ROUTE)
    } else if (status === 'auth' && user && !allow.includes(user.role)) {
      router.replace(homeForRole(user.role))
    }
  }, [status, user, allow, router])

  if (!allowed) return <GateFallback />
  return children
}
