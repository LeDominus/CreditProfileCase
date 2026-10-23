'use client'

import {
  BotIcon,
  FileTextIcon,
  HomeIcon,
  LifeBuoyIcon,
  PercentIcon,
  PlusIcon,
  UserIcon,
} from 'lucide-react'
import { toast } from 'sonner'

import { useChatStore } from '@/fsd/entities/conversation/model/chat-store'
import { useConversations } from '@/fsd/entities/conversation/model/queries'
import { useCreateConversation } from '@/fsd/features/create-conversation/model/use-create-conversation'
import { formatDateTime } from '@/fsd/shared/lib/format'
import { cn } from '@/fsd/shared/lib/utils'
import { Button } from '@/fsd/shared/ui/button'
import { Skeleton } from '@/fsd/shared/ui/skeleton'

import { usePanelStore } from '../right-panel/model/panel-store'

// Sidebar nav maps onto the right-panel tabs (see front/AGENTS.md):
// Главная/Кредиты → products, Заявки → applications, Профиль → profile.
// Кредиты и Поддержка — stubs until their stages.
const NAV_ITEMS = [
  { id: 'home', label: 'Главная', icon: HomeIcon, tab: 'products' as const },
  { id: 'credits', label: 'Кредиты', icon: PercentIcon, tab: 'products' as const },
  { id: 'applications', label: 'Заявки', icon: FileTextIcon, tab: 'applications' as const },
  { id: 'profile', label: 'Профиль', icon: UserIcon, tab: 'profile' as const },
  { id: 'support', label: 'Поддержка', icon: LifeBuoyIcon, tab: null },
]

const ACTIVE_NAV_BY_TAB = {
  products: 'home',
  applications: 'applications',
  profile: 'profile',
} as const

/**
 * Left column of the client cabinet: navigation, «Новая заявка» (creates a
 * fresh dialog), dialog history, assistant promo card.
 */
export function AppSidebar() {
  const activeTab = usePanelStore((s) => s.activeTab)
  const setActiveTab = usePanelStore((s) => s.setActiveTab)
  const activeConversationId = useChatStore((s) => s.activeConversationId)
  const setActiveConversation = useChatStore((s) => s.setActiveConversation)

  const conversationsQuery = useConversations()
  const createConversation = useCreateConversation()

  const activeNav = ACTIVE_NAV_BY_TAB[activeTab]

  const handleNav = (item: (typeof NAV_ITEMS)[number]) => {
    if (item.tab == null) {
      toast.info('Раздел в разработке')
      return
    }
    if (item.id === 'credits') {
      toast.info('Каталог кредитов появится в подборе продуктов')
    }
    setActiveTab(item.tab)
  }

  return (
    <aside className="hidden w-[260px] shrink-0 flex-col gap-4 overflow-hidden rounded-xl border border-border bg-bg-primary shadow-card md:flex">
      <nav className="flex flex-col gap-0.5 px-3 pt-4">
        {NAV_ITEMS.map((item) => (
          <button
            key={item.id}
            type="button"
            onClick={() => handleNav(item)}
            className={cn(
              'flex cursor-pointer items-center gap-2.5 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
              activeNav === item.id
                ? 'bg-accent/10 text-accent'
                : 'text-text-primary hover:bg-bg-secondary',
            )}
          >
            <item.icon className="size-4" />
            {item.label}
          </button>
        ))}
      </nav>

      <div className="px-3">
        <Button
          className="w-full"
          size="sm"
          onClick={() => createConversation.mutate()}
          disabled={createConversation.isPending}
        >
          <PlusIcon />
          {createConversation.isPending ? 'Создаём…' : 'Новая заявка'}
        </Button>
      </div>

      <div className="flex min-h-0 flex-1 flex-col gap-1 overflow-y-auto border-t border-border px-3 py-3">
        <p className="px-1 pb-1 text-xs font-bold tracking-wider text-text-secondary uppercase">
          История диалогов
        </p>
        {conversationsQuery.isLoading && (
          <div className="flex flex-col gap-2 px-1">
            <Skeleton className="h-9 w-full" />
            <Skeleton className="h-9 w-full" />
          </div>
        )}
        {conversationsQuery.data?.length === 0 && (
          <p className="px-1 text-xs text-text-secondary">
            Диалогов пока нет — начните с кнопки «Новая заявка» или просто напишите ассистенту.
          </p>
        )}
        {conversationsQuery.data?.map((conversation) => (
          <button
            key={conversation.id}
            type="button"
            onClick={() => setActiveConversation(conversation.id)}
            className={cn(
              'flex cursor-pointer flex-col gap-0.5 rounded-lg px-3 py-2 text-left transition-colors',
              activeConversationId === conversation.id ? 'bg-accent/10' : 'hover:bg-bg-secondary',
            )}
          >
            <span
              className={cn(
                'text-sm font-medium',
                activeConversationId === conversation.id ? 'text-accent' : 'text-text-primary',
              )}
            >
              Диалог №{conversation.id}
            </span>
            <span className="text-xs text-text-secondary">
              {formatDateTime(conversation.updatedAt)}
            </span>
          </button>
        ))}
      </div>

      <div className="mx-3 mb-4 flex items-start gap-3 rounded-xl bg-accent/10 p-3.5">
        <span className="inline-flex size-9 shrink-0 items-center justify-center rounded-full bg-accent text-white">
          <BotIcon className="size-4.5" />
        </span>
        <div className="flex flex-col gap-0.5">
          <span className="text-sm font-bold">ИИ-ассистент</span>
          <span className="text-xs leading-relaxed text-text-secondary">
            Отвечает на вопросы и заполняет профиль за вас
          </span>
        </div>
      </div>
    </aside>
  )
}
