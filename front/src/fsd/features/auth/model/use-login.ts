'use client'

import { useMutation } from '@tanstack/react-query'
import { HTTPError } from 'ky'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'

import { useSession } from '@/fsd/entities/session/model/session-store'
import { login } from '@/fsd/entities/user/api/auth-api'
import type { LoginFormValues } from '@/fsd/entities/user/model/schemas'
import { homeForRole } from '@/fsd/shared/config/routes'

function loginErrorMessage(error: unknown): string {
  if (error instanceof HTTPError && error.response.status === 401) {
    return 'Неверный логин или пароль'
  }
  return error instanceof Error ? error.message : 'Не удалось войти. Попробуйте ещё раз'
}

export function useLogin() {
  const router = useRouter()
  const setSession = useSession((s) => s.setSession)

  return useMutation({
    mutationFn: (values: LoginFormValues) => login(values),
    onSuccess: ({ token, user }) => {
      setSession(token, user)
      toast.success(`Здравствуйте, ${user.username}`)
      router.replace(homeForRole(user.role))
    },
    onError: (error) => {
      toast.error(loginErrorMessage(error))
    },
  })
}
