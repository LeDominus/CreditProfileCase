'use client'

import { LogOutIcon } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { toast } from 'sonner'

import { useSession } from '@/fsd/entities/session/model/session-store'
import { LOGIN_ROUTE } from '@/fsd/shared/config/routes'
import { Button } from '@/fsd/shared/ui/button'

/** Logout = drop the local session; the backend token has no revoke endpoint. */
export function LogoutButton() {
  const router = useRouter()
  const clear = useSession((s) => s.clear)

  const handleLogout = () => {
    clear()
    toast.success('Вы вышли из кабинета')
    router.replace(LOGIN_ROUTE)
  }

  return (
    <Button variant="ghost" size="sm" onClick={handleLogout}>
      <LogOutIcon />
      Выйти
    </Button>
  )
}
