import { api } from '@/fsd/shared/api/http'

import {
  type AuthResponse,
  authResponseSchema,
  type LoginFormValues,
  meResponseSchema,
  type RegisterFormValues,
  type User,
} from '../model/schemas'

/** POST /api/auth/login — 401 on bad credentials. */
export async function login(values: LoginFormValues): Promise<AuthResponse> {
  const data = await api.post('auth/login', { json: values }).json()
  return authResponseSchema.parse(data)
}

/** POST /api/auth/register — 409 on taken username, 422 on bad role/fields. */
export async function register(values: RegisterFormValues): Promise<AuthResponse> {
  const data = await api.post('auth/register', { json: values }).json()
  return authResponseSchema.parse(data)
}

/** GET /api/auth/me — session restore by token; 401 means "logged out". */
export async function fetchMe(): Promise<User> {
  const data = await api.get('auth/me').json()
  return meResponseSchema.parse(data).user
}
