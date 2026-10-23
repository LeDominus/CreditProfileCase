'use client'

import { motion } from 'framer-motion'
import { useState } from 'react'

import { ROLE_LABELS } from '@/fsd/entities/user/model/role-labels'
import {
  loginFormSchema,
  registerFormSchema,
  type UserRole,
  userRoleSchema,
} from '@/fsd/entities/user/model/schemas'
import { useLogin } from '@/fsd/features/auth/model/use-login'
import { useRegister } from '@/fsd/features/auth/model/use-register'
import { Button } from '@/fsd/shared/ui/button'
import { Card, CardContent } from '@/fsd/shared/ui/card'
import { Input } from '@/fsd/shared/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/fsd/shared/ui/select'
import { Tabs, TabsList, TabsPanel, TabsTab } from '@/fsd/shared/ui/tabs'
import { AlfaLogo } from '@/fsd/widgets/app-chrome/app-chrome'

type FormErrors = Record<string, string[] | undefined>

function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return <p className="text-xs text-negative">{message}</p>
}

function LoginForm() {
  const { mutate, isPending } = useLogin()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [errors, setErrors] = useState<FormErrors>({})

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    const parsed = loginFormSchema.safeParse({ username, password })
    if (!parsed.success) {
      setErrors(parsed.error.flatten().fieldErrors)
      return
    }
    setErrors({})
    mutate(parsed.data)
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
      <div className="flex flex-col gap-1.5">
        <label htmlFor="login-username" className="text-sm font-medium">
          Логин
        </label>
        <Input
          id="login-username"
          autoComplete="username"
          placeholder="ivanov"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          aria-invalid={Boolean(errors.username)}
        />
        <FieldError message={errors.username?.[0]} />
      </div>
      <div className="flex flex-col gap-1.5">
        <label htmlFor="login-password" className="text-sm font-medium">
          Пароль
        </label>
        <Input
          id="login-password"
          type="password"
          autoComplete="current-password"
          placeholder="••••••••"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          aria-invalid={Boolean(errors.password)}
        />
        <FieldError message={errors.password?.[0]} />
      </div>
      <Button type="submit" size="lg" className="mt-2 w-full" disabled={isPending}>
        {isPending ? 'Входим…' : 'Войти'}
      </Button>
    </form>
  )
}

function RegisterForm() {
  const { mutate, isPending } = useRegister()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<UserRole>('client')
  const [errors, setErrors] = useState<FormErrors>({})

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    const parsed = registerFormSchema.safeParse({ username, password, role })
    if (!parsed.success) {
      setErrors(parsed.error.flatten().fieldErrors)
      return
    }
    setErrors({})
    mutate(parsed.data)
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-4" noValidate>
      <div className="flex flex-col gap-1.5">
        <label htmlFor="reg-username" className="text-sm font-medium">
          Логин
        </label>
        <Input
          id="reg-username"
          autoComplete="username"
          placeholder="От 3 до 64 символов"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          aria-invalid={Boolean(errors.username)}
        />
        <FieldError message={errors.username?.[0]} />
      </div>
      <div className="flex flex-col gap-1.5">
        <label htmlFor="reg-password" className="text-sm font-medium">
          Пароль
        </label>
        <Input
          id="reg-password"
          type="password"
          autoComplete="new-password"
          placeholder="От 4 до 128 символов"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          aria-invalid={Boolean(errors.password)}
        />
        <FieldError message={errors.password?.[0]} />
      </div>
      <div className="flex flex-col gap-1.5">
        <label htmlFor="reg-role" className="text-sm font-medium">
          Роль
        </label>
        <Select value={role} onValueChange={(value) => setRole(value as UserRole)}>
          <SelectTrigger id="reg-role">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {userRoleSchema.options.map((option) => (
              <SelectItem key={option} value={option}>
                {ROLE_LABELS[option]}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <p className="text-xs text-text-secondary">
          Для демо доступна регистрация сотрудников банка без подтверждения.
        </p>
      </div>
      <Button type="submit" size="lg" className="mt-2 w-full" disabled={isPending}>
        {isPending ? 'Создаём аккаунт…' : 'Зарегистрироваться'}
      </Button>
    </form>
  )
}

export function LoginPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-8 bg-bg-secondary px-4 py-10">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: 'easeOut' }}
        className="flex flex-col items-center gap-4"
      >
        <AlfaLogo size="lg" />
        <div className="flex flex-col items-center gap-1 text-center">
          <h1 className="text-2xl font-bold">Умный кредитный кабинет</h1>
          <p className="text-sm text-text-secondary">
            Кредит для бизнеса через диалог с ИИ-ассистентом
          </p>
        </div>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.35, ease: 'easeOut', delay: 0.08 }}
        className="w-full max-w-md"
      >
        <Card className="gap-6 py-6">
          <CardContent>
            <Tabs defaultValue="login">
              <TabsList className="mb-6 flex w-full">
                <TabsTab value="login">Вход</TabsTab>
                <TabsTab value="register">Регистрация</TabsTab>
              </TabsList>
              <TabsPanel value="login">
                <LoginForm />
              </TabsPanel>
              <TabsPanel value="register">
                <RegisterForm />
              </TabsPanel>
            </Tabs>
          </CardContent>
        </Card>
      </motion.div>

      <p className="text-xs text-text-secondary">Хакатон «Альфа-Будущее» · прототип</p>
    </div>
  )
}
