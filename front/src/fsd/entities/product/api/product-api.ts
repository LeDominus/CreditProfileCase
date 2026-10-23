import { z } from 'zod'
import { api } from '@/fsd/shared/api/http'
import {
  type Product,
  productSchema,
  type Recommendation,
  recommendationSchema,
} from '../model/schemas'

/** GET /api/products — bare array, public endpoint. */
export async function fetchProducts(): Promise<Product[]> {
  const data = await api.get('products').json()
  return z.array(productSchema).parse(data)
}

const recommendationsResponseSchema = z.object({
  status: z.string(),
  recommendations: z.array(recommendationSchema),
})

/**
 * POST /api/recommendations — public; body is any subset of profile fields
 * (extra keys are ignored by the backend). Gated client-side by profile
 * completeness — see isProfileCompleteForRecommendations.
 */
export interface RecommendationsPayload {
  requested_amount?: number
  preferred_term_months?: number
  business_age_months?: number
  monthly_revenue?: number
  monthly_profit?: number
  funding_purpose?: string
}

export async function fetchRecommendations(
  payload: RecommendationsPayload,
): Promise<Recommendation[]> {
  const data = await api.post('recommendations', { json: payload }).json()
  return recommendationsResponseSchema.parse(data).recommendations
}
