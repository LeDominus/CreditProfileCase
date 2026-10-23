'use client'

import { useRouter } from 'next/navigation'
import { type ReactNode, useEffect } from 'react'

import { useSession } from '@/fsd/entities/session/model/session-store'
import { homeForRole } from '@/fsd/shared/config/routes'

/**
 * Inverse of AuthGate for /login: an already authenticated user is routed to
 * their role's home page instead of seeing the auth forms.
 */
export function GuestGate({ children }: { children: ReactNode }) {
  const router = useRouter()
  const status = useSession((s) => s.status)
  const user = useSession((s) => s.user)

  useEffect(() => {
    if (status === 'auth' && user) router.replace(homeForRole(user.role))
  }, [status, user, router])

  if (status !== 'guest') {
    return <div className="min-h-screen bg-bg-secondary" />
  }
  return children
}
