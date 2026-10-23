import { z } from 'zod'

/**
 * Structured decision_details (backend: ScoringResult §4.6 + stop-factor
 * rejections + bank-staff keys). Two shapes exist:
 * - scoring ran: {score, decision, factors[], explanation, missing_fields,
 *   suggested_*, alternatives?}
 * - stop-factor rejection (before scoring): {stop_factors[], explanation} —
 *   NO score/factors.
 * Extra keys (future backend additions) pass through via looseObject.
 */

const factorApiSchema = z.object({
  name: z.string(),
  label: z.string(),
  value: z.string(),
  normalized: z.number(),
  weight: z.number(),
  contribution: z.number(),
})

const stopFactorApiSchema = z.object({
  code: z.string(),
  label: z.string(),
})

const alternativeApiSchema = z.object({
  id: z.number(),
  name: z.string(),
  tagline: z.string(),
  rate: z.number(),
  amount: z.number(),
  term_months: z.number(),
  monthly_payment: z.number(),
  total_repayment: z.number(),
  overpayment: z.number(),
  amount_reduced: z.boolean(),
  affordable: z.boolean(),
  purpose_match: z.boolean(),
})

export const decisionDetailsSchema = z
  .looseObject({
    score: z.number().nullish(),
    decision: z.string().nullish(),
    factors: z.array(factorApiSchema).nullish(),
    explanation: z.string().nullish(),
    missing_fields: z.array(z.string()).nullish(),
    suggested_amount: z.number().nullish(),
    suggested_term_months: z.number().nullish(),
    suggested_monthly_payment: z.number().nullish(),
    stop_factors: z.array(stopFactorApiSchema).nullish(),
    alternatives: z.array(alternativeApiSchema).nullish(),
    needs_info_reason: z.string().nullish(),
    analyst_decision: z
      .object({ decision: z.string(), reason: z.string(), analyst: z.string() })
      .nullish(),
  })
  .transform((raw) => ({
    score: raw.score ?? null,
    decision: raw.decision ?? null,
    factors: (raw.factors ?? null)?.map((f) => ({
      name: f.name,
      label: f.label,
      value: f.value,
      normalized: f.normalized,
      weight: f.weight,
      contribution: f.contribution,
    })),
    explanation: raw.explanation ?? null,
    missingFields: raw.missing_fields ?? null,
    suggestedAmount: raw.suggested_amount ?? null,
    suggestedTermMonths: raw.suggested_term_months ?? null,
    suggestedMonthlyPayment: raw.suggested_monthly_payment ?? null,
    stopFactors: raw.stop_factors ?? null,
    alternatives: (raw.alternatives ?? null)?.map((a) => ({
      id: a.id,
      name: a.name,
      tagline: a.tagline,
      rate: a.rate,
      amount: a.amount,
      termMonths: a.term_months,
      monthlyPayment: a.monthly_payment,
      totalRepayment: a.total_repayment,
      overpayment: a.overpayment,
      amountReduced: a.amount_reduced,
      affordable: a.affordable,
      purposeMatch: a.purpose_match,
    })),
    needsInfoReason: raw.needs_info_reason ?? null,
    analystDecision: raw.analyst_decision ?? null,
  }))
export type DecisionDetails = z.infer<typeof decisionDetailsSchema>
export type AlternativeProduct = NonNullable<DecisionDetails['alternatives']>[number]
export type StopFactor = NonNullable<DecisionDetails['stopFactors']>[number]

/** GET /api/applications/{id}/history (FRONTEND_GUIDE §4.9). */
const historyEntryApiSchema = z.object({
  id: z.number(),
  application_id: z.number(),
  from_status: z.string().nullable(),
  to_status: z.string(),
  actor_type: z.string(),
  actor_id: z.number().nullable(),
  comment: z.string().nullable(),
  created_at: z.string(),
})

const historyEntrySchema = historyEntryApiSchema.transform((raw) => ({
  id: raw.id,
  applicationId: raw.application_id,
  fromStatus: raw.from_status,
  toStatus: raw.to_status,
  actorType: raw.actor_type,
  actorId: raw.actor_id,
  comment: raw.comment,
  createdAt: raw.created_at,
}))
export type ApplicationHistoryEntry = z.infer<typeof historyEntrySchema>

export const applicationHistoryResponseSchema = z.object({
  status: z.string(),
  application_id: z.number(),
  history: z.array(historyEntrySchema),
})

/** POST /api/applications/{id}/explain */
export const explainResponseSchema = z.object({
  status: z.string(),
  application_id: z.number(),
  audience: z.string(),
  explanation: z.string(),
  source: z.string(), // "llm" | "fallback"
})
export type ExplainResponse = z.infer<typeof explainResponseSchema>
