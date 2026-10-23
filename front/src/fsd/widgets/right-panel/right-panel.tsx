'use client'

import { ApplicationFormDialog } from '@/fsd/features/fill-application-form/ui/application-form-dialog'
import { ApplicationAcceptedDialog } from '@/fsd/features/submit-application/ui/application-accepted-dialog'
import { Tabs, TabsList, TabsPanel, TabsTab } from '@/fsd/shared/ui/tabs'

import { ApplicationsPanel } from './applications-panel'
import { type ClientPanelTab, usePanelStore } from './model/panel-store'
import { ProductsPanel } from './products-panel'
import { ProfilePanel } from './profile-panel'

/**
 * Right column of the client cabinet. Tab state lives in panel-store so the
 * sidebar nav can switch tabs; content never unmounts the chat. The
 * application form and accepted dialogs are mounted here so they overlay
 * the whole cabinet.
 */
export function RightPanel() {
  const activeTab = usePanelStore((s) => s.activeTab)
  const setActiveTab = usePanelStore((s) => s.setActiveTab)

  return (
    <aside className="hidden w-[380px] shrink-0 flex-col overflow-hidden rounded-xl border border-border bg-bg-primary shadow-card lg:flex">
      <Tabs
        value={activeTab}
        onValueChange={(value) => setActiveTab(value as ClientPanelTab)}
        className="flex min-h-0 flex-1 flex-col"
      >
        <div className="border-b border-border px-4 pt-4 pb-3">
          <TabsList className="flex w-full">
            <TabsTab value="products">Продукты</TabsTab>
            <TabsTab value="profile">Профиль</TabsTab>
            <TabsTab value="applications">Заявки</TabsTab>
          </TabsList>
        </div>
        <div className="min-h-0 flex-1 overflow-y-auto px-4 py-4">
          <TabsPanel value="products">
            <ProductsPanel />
          </TabsPanel>
          <TabsPanel value="profile">
            <ProfilePanel />
          </TabsPanel>
          <TabsPanel value="applications">
            <ApplicationsPanel />
          </TabsPanel>
        </div>
      </Tabs>

      <ApplicationFormDialog />
      <ApplicationAcceptedDialog />
    </aside>
  )
}
