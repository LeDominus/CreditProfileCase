'use client'

import { useEffect, useRef } from 'react'
import { useSession } from '@/fsd/entities/session/model/session-store'
import { fetchMe } from '@/fsd/entities/user/api/auth-api'

/**
 * Session restore on app start: if a persisted token exists, validate it via
 * GET /api/auth/me (401 → drop the session, the http layer also guards this);
 * without a token the status flips straight to `guest`.
 */
export function SessionBootstrap() {
  const started = useRef(false)

  useEffect(() => {
    if (started.current) return
    started.current = true

    const { token, status, setUser, setGuest, clear } = useSession.getState()
    if (status !== 'unknown') return
    if (!token) {
      setGuest()
      return
    }
    fetchMe()
      .then(setUser)
      .catch(() => clear())
  }, [])

  return null
}
