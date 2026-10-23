import { create } from 'zustand'

import type { Application } from '@/fsd/entities/application/model/schemas'
import type { Product } from '@/fsd/entities/product/model/schemas'

/**
 * Draft application flow state (product pick → params → form dialog →
 * accepted dialog). In-memory; reset when the flow completes or is abandoned.
 */
interface ApplicationDraftState {
  selectedProduct: Product | null
  amount: number | null
  term: number | null
  dataConfirmed: boolean
  formOpen: boolean
  /** Result of the submit flow for the «Заявка принята» dialog. */
  accepted: { application: Application; submitted: boolean } | null
  selectProduct: (product: Product, amount: number, term: number) => void
  clearProduct: () => void
  setAmount: (amount: number) => void
  setTerm: (term: number) => void
  setDataConfirmed: (value: boolean) => void
  setFormOpen: (open: boolean) => void
  setAccepted: (accepted: { application: Application; submitted: boolean } | null) => void
  reset: () => void
}

export const useApplicationDraft = create<ApplicationDraftState>()((set) => ({
  selectedProduct: null,
  amount: null,
  term: null,
  dataConfirmed: false,
  formOpen: false,
  accepted: null,
  selectProduct: (product, amount, term) =>
    set({ selectedProduct: product, amount, term, dataConfirmed: false }),
  clearProduct: () =>
    set({ selectedProduct: null, amount: null, term: null, dataConfirmed: false }),
  setAmount: (amount) => set({ amount }),
  setTerm: (term) => set({ term }),
  setDataConfirmed: (value) => set({ dataConfirmed: value }),
  setFormOpen: (open) => set({ formOpen: open }),
  setAccepted: (accepted) => set({ accepted }),
  reset: () =>
    set({
      selectedProduct: null,
      amount: null,
      term: null,
      dataConfirmed: false,
      formOpen: false,
      accepted: null,
    }),
}))
