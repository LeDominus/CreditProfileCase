import { AppSidebar } from '@/fsd/widgets/app-sidebar/app-sidebar'
import { ChatPanel } from '@/fsd/widgets/chat-panel/chat-panel'
import { RightPanel } from '@/fsd/widgets/right-panel/right-panel'

/**
 * Client cabinet home («Бизнес.Плюс» concept): sidebar / chat / tabbed right
 * panel inside AppChrome. Height = viewport minus the chrome header (4rem)
 * and main padding (2×2rem).
 */
export function ClientHomePage() {
  return (
    <div className="flex h-[calc(100dvh-8rem)] gap-5">
      <AppSidebar />
      <ChatPanel />
      <RightPanel />
    </div>
  )
}
