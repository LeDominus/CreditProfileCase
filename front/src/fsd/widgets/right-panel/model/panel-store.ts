import { create } from 'zustand'

export type ClientPanelTab = 'products' | 'profile' | 'applications'

/**
 * Active tab of the client cabinet right panel. Lives in a store (not local
 * state) so the sidebar nav can switch tabs, and the tab survives chat
 * interactions.
 */
interface PanelState {
  activeTab: ClientPanelTab
  setActiveTab: (tab: ClientPanelTab) => void
}

export const usePanelStore = create<PanelState>()((set) => ({
  activeTab: 'products',
  setActiveTab: (tab) => set({ activeTab: tab }),
}))
