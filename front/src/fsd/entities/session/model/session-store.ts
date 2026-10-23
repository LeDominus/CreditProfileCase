import { create } from 'zustand'
import { persist } from 'zustand/middleware'

import type { User } from '@/fsd/entities/user/model/schemas'

/**
 * Session state. The backend token is a non-expiring opaque string, so it is
 * persisted to localStorage (token + user) and revalidated on app start via
 * GET /api/auth/me (features/auth/session-bootstrap). `status` distinguishes
 * "not checked yet" (unknown) from "checked, anonymous" (guest) and is never
 * persisted.
 */
type SessionStatus = 'unknown' | 'auth' | 'guest'

interface SessionState {
  token: string | null
  user: User | null
  status: SessionStatus
  setSession: (token: string, user: User) => void
  setUser: (user: User) => void
  setGuest: () => void
  clear: () => void
}

export const useSession = create<SessionState>()(
  persist(
    (set) => ({
      token: null,
      user: null,
      status: 'unknown',
      setSession: (token, user) => set({ token, user, status: 'auth' }),
      setUser: (user) => set({ user, status: 'auth' }),
      setGuest: () => set({ token: null, user: null, status: 'guest' }),
      clear: () => set({ token: null, user: null, status: 'guest' }),
    }),
    {
      name: 'alfa-credit-session',
      partialize: ({ token, user }) => ({ token, user }),
    },
  ),
)

/** Non-reactive accessor for the ky hooks. */
export const getSession = () => useSession.getState()
