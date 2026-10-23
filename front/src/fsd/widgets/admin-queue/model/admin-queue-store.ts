import { create } from 'zustand'

/**
 * АРМ queue UI state: status filter and the selected application id.
 * Selection survives the 15 s polling; when the selected application drops
 * out of the (filtered) queue, the queue widget resets it with a notice.
 */
interface AdminQueueState {
  statusFilter: string | null
  selectedId: number | null
  setStatusFilter: (status: string | null) => void
  setSelectedId: (id: number | null) => void
}

export const useAdminQueueStore = create<AdminQueueState>()((set) => ({
  statusFilter: null,
  selectedId: null,
  setStatusFilter: (status) => set({ statusFilter: status }),
  setSelectedId: (id) => set({ selectedId: id }),
}))
