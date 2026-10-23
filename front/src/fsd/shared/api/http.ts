import ky, { type KyInstance } from 'ky'

import { getSession } from '@/fsd/entities/session/model/session-store'
import { LOGIN_ROUTE } from '@/fsd/shared/config/routes'

/**
 * Shared ky instance for the backend API.
 *
 * - Base is the same-origin `/api`; next.config rewrites proxy it to the
 *   FastAPI backend, so no CORS is involved.
 * - Every request carries the Bearer token from the session store.
 * - On 401 (outside /auth/*) the session is dropped and the app routes to
 *   /login — the token is non-expiring, so a 401 always means "invalid".
 * - FastAPI error bodies `{detail}` are unwrapped in beforeError: a plain
 *   string surfaces as-is, a 422 array becomes "field: msg; ...".
 * - Timeout is generous: LLM endpoints (messages, explain) take tens of
 *   seconds.
 */
export const api: KyInstance = ky.create({
  prefix: '/api',
  retry: 0,
  timeout: 120_000,
  hooks: {
    beforeRequest: [
      ({ request }) => {
        const { token } = getSession()
        if (token) request.headers.set('Authorization', `Bearer ${token}`)
      },
    ],
    afterResponse: [
      ({ request, response }) => {
        if (response.status !== 401) return
        if (new URL(request.url).pathname.includes('/auth/')) return
        getSession().clear()
        if (typeof window !== 'undefined' && window.location.pathname !== LOGIN_ROUTE) {
          window.location.assign(LOGIN_ROUTE)
        }
      },
    ],
    beforeError: [
      async ({ error }) => {
        const response = (error as { response?: Response }).response
        if (!response) return error
        try {
          const body = (await response.clone().json()) as {
            detail?: string | Array<{ loc?: Array<string | number>; msg?: string }>
          }
          const detail = body?.detail
          if (typeof detail === 'string' && detail) {
            error.message = detail
          } else if (Array.isArray(detail) && detail.length > 0) {
            error.message = detail
              .map((item) => {
                const field = item.loc?.filter((part) => part !== 'body').join('.')
                return field ? `${field}: ${item.msg}` : item.msg
              })
              .filter(Boolean)
              .join('; ')
          }
        } catch {
          // Non-JSON error body — keep ky's default message.
        }
        return error
      },
    ],
  },
})
