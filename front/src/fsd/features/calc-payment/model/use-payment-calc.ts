'use client'

import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect, useState } from 'react'

import { calcProfilePayment } from '@/fsd/entities/application/api/application-api'
import type { PaymentCalculation } from '@/fsd/entities/application/model/schemas'
import { updateProfile } from '@/fsd/entities/profile/api/profile-api'
import { useMyProfile } from '@/fsd/entities/profile/model/queries'
import { queryKeys } from '@/fsd/shared/api/query-keys'
import { calcAnnuity } from '@/fsd/shared/lib/annuity'

export interface PaymentState {
  calculation: PaymentCalculation | null
  isLoading: boolean
  /** 'api' — backend calculation; 'local' — annuity fallback. */
  source: 'api' | 'local' | null
}

/**
 * Debounced annuity calculation for the chosen amount/term.
 *
 * The payment endpoint computes from PROFILE fields, so the chosen params are
 * first PATCHed into the profile (this also keeps the profile in sync), then
 * POST /api/profile/{id}/payment runs. Any API failure falls back to the
 * local annuity formula — the block never shows an error state.
 */
export function usePaymentCalc(
  productRate: number | null,
  amount: number | null,
  term: number | null,
): PaymentState {
  const profileQuery = useMyProfile()
  const profileId = profileQuery.data?.id ?? null
  const queryClient = useQueryClient()

  // Debounce: the query key follows the debounced params, not every keystroke.
  const [debounced, setDebounced] = useState<{ amount: number; term: number } | null>(null)
  useEffect(() => {
    if (amount == null || term == null || amount <= 0 || term <= 0) {
      setDebounced(null)
      return
    }
    const timer = setTimeout(() => setDebounced({ amount, term }), 500)
    return () => clearTimeout(timer)
  }, [amount, term])

  const paymentQuery = useQuery({
    queryKey: queryKeys.payment(profileId ?? -1, debounced?.amount ?? 0, debounced?.term ?? 0),
    enabled: profileId != null && debounced != null,
    retry: false,
    staleTime: 30_000,
    queryFn: async (): Promise<PaymentCalculation> => {
      const { amount: a, term: t } = debounced as { amount: number; term: number }
      const profileIdSafe = profileId as number
      await updateProfile(profileIdSafe, { requested_amount: a, preferred_term_months: t })
      queryClient.invalidateQueries({ queryKey: queryKeys.myProfile })
      return calcProfilePayment(profileIdSafe)
    },
  })

  if (debounced == null || productRate == null) {
    return { calculation: null, isLoading: false, source: null }
  }
  if (paymentQuery.data) {
    return { calculation: paymentQuery.data, isLoading: false, source: 'api' }
  }
  if (paymentQuery.isError || profileId == null) {
    const local = calcAnnuity(debounced.amount, productRate, debounced.term)
    return {
      calculation: {
        profileId: profileId ?? 0,
        product: { id: 0, name: '', rate: productRate },
        requestedAmount: debounced.amount,
        termMonths: debounced.term,
        ...local,
      },
      isLoading: false,
      source: 'local',
    }
  }
  return { calculation: null, isLoading: true, source: null }
}
