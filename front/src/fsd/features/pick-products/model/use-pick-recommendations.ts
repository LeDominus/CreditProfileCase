'use client'

import { useMutation } from '@tanstack/react-query'
import { toast } from 'sonner'

import { fetchRecommendations } from '@/fsd/entities/product/api/product-api'
import { useRecommendationsStore } from '@/fsd/entities/product/model/recommendations-store'
import { useMyProfile } from '@/fsd/entities/profile/model/queries'
import { isProfileCompleteForRecommendations } from '@/fsd/entities/profile/model/schemas'

/**
 * «Подобрать продукты»: POST /api/recommendations with the current profile.
 * Enabled only when the profile has all five gating fields — no picking
 * products "around the dialog".
 */
export function usePickRecommendations() {
  const profileQuery = useMyProfile()
  const setRecommendations = useRecommendationsStore((s) => s.setRecommendations)

  const profile = profileQuery.data ?? null
  const isComplete = isProfileCompleteForRecommendations(profile)

  const mutation = useMutation({
    mutationFn: () =>
      fetchRecommendations({
        requested_amount: profile?.requestedAmount ?? undefined,
        preferred_term_months: profile?.preferredTermMonths ?? undefined,
        business_age_months: profile?.businessAgeMonths ?? undefined,
        monthly_revenue: profile?.monthlyRevenue ?? undefined,
        monthly_profit: profile?.monthlyProfit ?? undefined,
        funding_purpose: profile?.fundingPurpose ?? undefined,
      }),
    onSuccess: (items) => {
      if (items.length === 0) {
        toast.info('По текущим параметрам подходящих продуктов нет — уточните сумму или срок')
        return
      }
      setRecommendations(items)
      toast.success(`Подобрано продуктов: ${items.length}`)
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Не удалось подобрать продукты')
    },
  })

  return { ...mutation, isComplete, profile }
}
