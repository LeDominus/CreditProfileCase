import { create } from 'zustand'

import type { Recommendation } from './schemas'

/**
 * Latest recommendations from the chat pipeline (ContractExtraction).
 * Filled by send-message; the products panel (next stage) renders them.
 * In-memory only: gated by profile completeness, they reappear as the
 * dialog continues.
 */
interface RecommendationsState {
  recommendations: Recommendation[]
  setRecommendations: (items: Recommendation[]) => void
}

export const useRecommendationsStore = create<RecommendationsState>()((set) => ({
  recommendations: [],
  setRecommendations: (items) => set({ recommendations: items }),
}))
