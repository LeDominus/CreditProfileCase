import { z } from 'zod'

/**
 * API contract for business profiles (backend: src/schemas/profile_schema.py).
 * FastAPI speaks snake_case; schemas normalize to camelCase at the boundary.
 * ProfileRequest/Patch and ProfileCreateRequest are extra="forbid" — send
 * only contract fields, snake_case on the wire.
 */

const profileApiSchema = z.object({
  id: z.number(),
  business_name: z.string().nullable(),
  industry: z.string(),
  funding_purpose: z.string(),
  requested_amount: z.number().nullable(),
  business_age_months: z.number().nullable(),
  monthly_revenue: z.number().nullable(),
  monthly_profit: z.number().nullable(),
  preferred_term_months: z.number().nullable(),
  max_monthly_payment: z.number().nullable(),
  // Present in profile endpoints, ABSENT in the profile embedded into
  // ContractExtraction (POST /api/conversations/{id}/messages).
  user_id: z.number().nullable().optional(),
  created_at: z.string().optional(),
  updated_at: z.string().optional(),
})

export const businessProfileSchema = profileApiSchema.transform((raw) => ({
  id: raw.id,
  businessName: raw.business_name,
  industry: raw.industry,
  fundingPurpose: raw.funding_purpose,
  requestedAmount: raw.requested_amount,
  businessAgeMonths: raw.business_age_months,
  monthlyRevenue: raw.monthly_revenue,
  monthlyProfit: raw.monthly_profit,
  preferredTermMonths: raw.preferred_term_months,
  maxMonthlyPayment: raw.max_monthly_payment,
  userId: raw.user_id,
  createdAt: raw.created_at,
  updatedAt: raw.updated_at,
}))
export type BusinessProfile = z.infer<typeof businessProfileSchema>

/**
 * `profile_updates` in ContractExtraction: only the fields the LLM extracted
 * from the last message. `.partial()` before the transform keeps every key
 * optional; the transformed shape is a Partial<BusinessProfile>-like patch.
 */
export const profileUpdatesSchema = profileApiSchema
  .pick({
    business_name: true,
    industry: true,
    funding_purpose: true,
    requested_amount: true,
    business_age_months: true,
    monthly_revenue: true,
    monthly_profit: true,
    preferred_term_months: true,
    max_monthly_payment: true,
  })
  .partial()
  .transform((raw) => ({
    businessName: raw.business_name,
    industry: raw.industry,
    fundingPurpose: raw.funding_purpose,
    requestedAmount: raw.requested_amount,
    businessAgeMonths: raw.business_age_months,
    monthlyRevenue: raw.monthly_revenue,
    monthlyProfit: raw.monthly_profit,
    preferredTermMonths: raw.preferred_term_months,
    maxMonthlyPayment: raw.max_monthly_payment,
  }))
export type ProfileUpdates = z.infer<typeof profileUpdatesSchema>

/** Wire shape for POST /api/profile (industry + funding_purpose required). */
export interface ProfileCreatePayload {
  industry: string
  funding_purpose: string
  business_name?: string
  requested_amount?: number
  business_age_months?: number
  monthly_revenue?: number
  monthly_profit?: number
  preferred_term_months?: number
  max_monthly_payment?: number
}

/** Wire shape for PATCH /api/profile/{id} — any subset of fields. */
export type ProfilePatchPayload = Partial<ProfileCreatePayload>

/** Fields gating product recommendations (FRONTEND_GUIDE §5.3). */
export const RECOMMENDATION_GATE_FIELDS = [
  'requestedAmount',
  'preferredTermMonths',
  'businessAgeMonths',
  'monthlyRevenue',
  'monthlyProfit',
] as const satisfies ReadonlyArray<keyof BusinessProfile>

export function isProfileCompleteForRecommendations(
  profile: Pick<BusinessProfile, (typeof RECOMMENDATION_GATE_FIELDS)[number]> | null,
): boolean {
  if (!profile) return false
  return RECOMMENDATION_GATE_FIELDS.every((field) => profile[field] != null)
}
