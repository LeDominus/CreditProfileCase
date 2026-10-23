'use client'

import { useMutation } from '@tanstack/react-query'
import { HTTPError } from 'ky'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'

import { useSession } from '@/fsd/entities/session/model/session-store'
import { register } from '@/fsd/entities/user/api/auth-api'
import type { RegisterFormValues } from '@/fsd/entities/user/model/schemas'
import { homeForRole } from '@/fsd/shared/config/routes'

function registerErrorMessage(error: unknown): string {
  if (error instanceof HTTPError) {
    if (error.response.status === 409) return 'Такой логин уже занят'
    if (error.response.status === 422 && error.message) return error.message
  }
  return error instanceof Error ? error.message : 'Не удалось зарегистрироваться'
}

export function useRegister() {
  const router = useRouter()
  const setSession = useSession((s) => s.setSession)

  return useMutation({
    mutationFn: (values: RegisterFormValues) => register(values),
    onSuccess: ({ token, user }) => {
      setSession(token, user)
      toast.success('Аккаунт создан')
      router.replace(homeForRole(user.role))
    },
    onError: (error) => {
      toast.error(registerErrorMessage(error))
    },
  })
}
