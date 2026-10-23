import type { UserRole } from '@/fsd/entities/user/model/schemas'

export const LOGIN_ROUTE = '/login'
export const CLIENT_HOME_ROUTE = '/'
export const ADMIN_HOME_ROUTE = '/admin'

export const isBankRole = (role: UserRole) => role !== 'client'

/** Role-based landing page after login/registration or a guard redirect. */
export function homeForRole(role: UserRole): string {
  return isBankRole(role) ? ADMIN_HOME_ROUTE : CLIENT_HOME_ROUTE
}
