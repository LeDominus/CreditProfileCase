import { z } from 'zod'

import { clientDataSchema } from './client-data-schema'
import { decisionDetailsSchema } from './decision-details-schema'

/**
 * API contract for credit applications (backend: src/schemas/application_schema.py,
 * FRONTEND_GUIDE §4.5). snake_case → camelCase at the boundary.
 * decision_details is structured (model/decision-details-schema.ts);
 * client_data stays a loose record (only the АРМ reads it, stage 6).
 */

export const applicationStatusSchema = z.enum([
  'draft',
  'submitted',
  'data_check',
  'scoring',
  'needs_info',
  'manual_review',
  'approved',
  'approved_with_changes',
  'rejected',
  'offer_ready',
  'accepted',
  'signed',
  'issued',
  'client_declined',
])
export type ApplicationStatus = z.infer<typeof applicationStatusSchema>

const applicationApiSchema = z.object({
  id: z.number(),
  profile_id: z.number(),
  product_id: z.number(),
  product_name: z.string(),
  requested_amount: z.number(),
  term_months: z.number(),
  monthly_payment: z.number(),
  total_repayment: z.number(),
  overpayment: z.number(),
  status: z.string(),
  // Bank-only fields: parsed but NEVER rendered in the client cabinet
  // (see model/visibility.ts).
  score: z.number().nullable(),
  decision: z.string().nullable(),
  decision_details: decisionDetailsSchema.nullable(),
  client_data: clientDataSchema.nullable(),
  created_at: z.string(),
  updated_at: z.string(),
})

export const applicationSchema = applicationApiSchema.transform((raw) => ({
  id: raw.id,
  profileId: raw.profile_id,
  productId: raw.product_id,
  productName: raw.product_name,
  requestedAmount: raw.requested_amount,
  termMonths: raw.term_months,
  monthlyPayment: raw.monthly_payment,
  totalRepayment: raw.total_repayment,
  overpayment: raw.overpayment,
  status: raw.status as ApplicationStatus,
  score: raw.score,
  decision: raw.decision,
  decisionDetails: raw.decision_details,
  clientData: raw.client_data,
  createdAt: raw.created_at,
  updatedAt: raw.updated_at,
}))
export type Application = z.infer<typeof applicationSchema>

/** POST /api/applications → 201 */
export const applicationCreatedResponseSchema = z.object({
  status: z.string(),
  application: applicationSchema,
})

/** POST /api/applications/{id}/submit — application + scoring result. */
export const applicationSubmitResponseSchema = z.object({
  status: z.string(),
  application: applicationSchema,
  scoring: z.record(z.string(), z.unknown()).nullable().optional(),
})
export type ApplicationSubmitResponse = z.infer<typeof applicationSubmitResponseSchema>

/** GET /api/me/applications */
export const myApplicationsResponseSchema = z.object({
  status: z.string(),
  applications: z.array(applicationSchema),
})

/** POST /api/profile/{id}/payment — annuity by the best matching product. */
export const paymentResponseSchema = z
  .object({
    status: z.string(),
    profile_id: z.number(),
    product: z.object({ id: z.number(), name: z.string(), rate: z.number() }),
    requested_amount: z.number(),
    term_months: z.number(),
    monthly_payment: z.number(),
    total_repayment: z.number(),
    overpayment: z.number(),
  })
  .transform((raw) => ({
    profileId: raw.profile_id,
    product: raw.product,
    requestedAmount: raw.requested_amount,
    termMonths: raw.term_months,
    monthlyPayment: raw.monthly_payment,
    totalRepayment: raw.total_repayment,
    overpayment: raw.overpayment,
  }))
export type PaymentCalculation = z.infer<typeof paymentResponseSchema>

/** Wire payload for POST /api/applications. */
export interface ApplicationCreatePayload {
  profile_id: number
  product_id: number
  requested_amount: number
  term_months: number
  client_data?: Record<string, unknown>
}
