import { z } from 'zod'

/**
 * API contract for users/auth (backend: src/schemas/auth_schema.py and
 * main.py auth endpoints). FastAPI speaks snake_case; schemas normalize it
 * to camelCase at the boundary.
 */

export const userRoleSchema = z.enum(['client', 'bank_manager', 'bank_analyst'])
export type UserRole = z.infer<typeof userRoleSchema>

const userApiSchema = z.object({
  id: z.number(),
  username: z.string(),
  role: userRoleSchema,
  created_at: z.string(),
})

export const userSchema = userApiSchema.transform((raw) => ({
  id: raw.id,
  username: raw.username,
  role: raw.role,
  createdAt: raw.created_at,
}))
export type User = z.infer<typeof userSchema>

/** POST /api/auth/register and /api/auth/login share the response shape. */
export const authResponseSchema = z.object({
  status: z.string(),
  token: z.string(),
  user: userSchema,
})
export type AuthResponse = z.infer<typeof authResponseSchema>

/** GET /api/auth/me */
export const meResponseSchema = z.object({
  status: z.string(),
  user: userSchema,
})

// Client-side form validation mirrors AuthRegisterRequest (extra="forbid",
// username 3–64, password 4–128).
export const loginFormSchema = z.object({
  username: z.string().min(1, 'Введите логин'),
  password: z.string().min(1, 'Введите пароль'),
})
export type LoginFormValues = z.infer<typeof loginFormSchema>

export const registerFormSchema = z.object({
  username: z.string().min(3, 'Логин — от 3 до 64 символов').max(64, 'Логин — от 3 до 64 символов'),
  password: z
    .string()
    .min(4, 'Пароль — от 4 до 128 символов')
    .max(128, 'Пароль — от 4 до 128 символов'),
  role: userRoleSchema,
})
export type RegisterFormValues = z.infer<typeof registerFormSchema>
