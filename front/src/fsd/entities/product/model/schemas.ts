import { z } from 'zod'

/**
 * API contract for the product catalog and recommendations (backend:
 * src/schemas/product_schemas.py, FRONTEND_GUIDE §4.3–4.4). Recommendations
 * extend the product with a payment calculation; the full panel UI arrives
 * in the products stage, the store and schemas are laid down with the chat.
 */

const productApiSchema = z.object({
  id: z.number(),
  name: z.string(),
  tagline: z.string(),
  purpose: z.string(),
  min_amount: z.number(),
  max_amount: z.number(),
  min_term: z.number(),
  max_term: z.number(),
  min_age: z.number(),
  rate: z.number(),
  badge: z.string().nullable(),
  description: z.string(),
})

const productCamel = (raw: z.infer<typeof productApiSchema>) => ({
  id: raw.id,
  name: raw.name,
  tagline: raw.tagline,
  purpose: raw.purpose,
  minAmount: raw.min_amount,
  maxAmount: raw.max_amount,
  minTerm: raw.min_term,
  maxTerm: raw.max_term,
  minAge: raw.min_age,
  rate: raw.rate,
  badge: raw.badge,
  description: raw.description,
})

export const productSchema = productApiSchema.transform(productCamel)
export type Product = z.infer<typeof productSchema>

const recommendationApiSchema = productApiSchema.extend({
  monthly_payment: z.number(),
  total_repayment: z.number(),
  overpayment: z.number(),
  affordable: z.boolean(),
  purpose_match: z.boolean(),
})

export const recommendationSchema = recommendationApiSchema.transform((raw) => ({
  ...productCamel(raw),
  monthlyPayment: raw.monthly_payment,
  totalRepayment: raw.total_repayment,
  overpayment: raw.overpayment,
  affordable: raw.affordable,
  purposeMatch: raw.purpose_match,
}))
export type Recommendation = z.infer<typeof recommendationSchema>
