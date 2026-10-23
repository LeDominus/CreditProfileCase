import { api } from '@/fsd/shared/api/http'

import {
  type ApplicationHistoryEntry,
  applicationHistoryResponseSchema,
  type ExplainResponse,
  explainResponseSchema,
} from '../model/decision-details-schema'
import {
  type Application,
  type ApplicationCreatePayload,
  type ApplicationSubmitResponse,
  applicationCreatedResponseSchema,
  applicationSubmitResponseSchema,
  myApplicationsResponseSchema,
  type PaymentCalculation,
  paymentResponseSchema,
} from '../model/schemas'

/** POST /api/applications → 201 — draft with computed annuity. */
export async function createApplication(payload: ApplicationCreatePayload): Promise<Application> {
  const data = await api.post('applications', { json: payload }).json()
  return applicationCreatedResponseSchema.parse(data).application
}

/**
 * POST /api/applications/{id}/submit — submit + run the pipeline
 * (data_check → scoring → decision) synchronously.
 */
export async function submitApplication(applicationId: number): Promise<ApplicationSubmitResponse> {
  const data = await api.post(`applications/${applicationId}/submit`).json()
  return applicationSubmitResponseSchema.parse(data)
}

/** GET /api/me/applications — all user's applications across profiles. */
export async function fetchMyApplications(): Promise<Application[]> {
  const data = await api.get('me/applications').json()
  return myApplicationsResponseSchema.parse(data).applications
}

/**
 * POST /api/profile/{id}/payment — annuity by the best matching product.
 * 422 when the profile lacks requested_amount/preferred_term_months — callers
 * PATCH the profile with the chosen params first (see use-payment-calc).
 */
export async function calcProfilePayment(profileId: number): Promise<PaymentCalculation> {
  const data = await api.post(`profile/${profileId}/payment`).json()
  return paymentResponseSchema.parse(data)
}

export interface ApplicationPatchPayload {
  requested_amount?: number
  term_months?: number
}

/** PATCH /api/applications/{id} — edit a DRAFT (409 otherwise). */
export async function updateApplication(
  applicationId: number,
  payload: ApplicationPatchPayload,
): Promise<Application> {
  const data = await api.patch(`applications/${applicationId}`, { json: payload }).json()
  return applicationCreatedResponseSchema.parse(data).application
}

/** POST /api/applications/{id}/scoring — reprocess from needs_info/submitted. */
export async function rescoreApplication(
  applicationId: number,
): Promise<ApplicationSubmitResponse> {
  const data = await api.post(`applications/${applicationId}/scoring`).json()
  return applicationSubmitResponseSchema.parse(data)
}

/** POST /api/applications/{id}/offer-response — accept/decline the offer. */
export async function respondToOffer(
  applicationId: number,
  accept: boolean,
  declineReason?: string,
): Promise<Application> {
  const json: { accept: boolean; decline_reason?: string } = { accept }
  if (!accept && declineReason) json.decline_reason = declineReason
  const data = await api.post(`applications/${applicationId}/offer-response`, { json }).json()
  return applicationCreatedResponseSchema.parse(data).application
}

/** POST /api/applications/{id}/sign — accepted → signed → issued (ЭП-модель). */
export async function signApplication(applicationId: number): Promise<Application> {
  const data = await api.post(`applications/${applicationId}/sign`).json()
  return applicationCreatedResponseSchema.parse(data).application
}

/**
 * POST /api/applications/{id}/explain — LLM explanation (SLOW, tens of
 * seconds; 409 when there is no decision yet).
 */
export async function explainApplication(
  applicationId: number,
  audience: 'client' | 'analyst' = 'client',
): Promise<ExplainResponse> {
  const data = await api
    .post(`applications/${applicationId}/explain`, { json: { audience } })
    .json()
  return explainResponseSchema.parse(data)
}

/** GET /api/applications/{id}/history — status transitions, oldest first. */
export async function fetchApplicationHistory(
  applicationId: number,
): Promise<ApplicationHistoryEntry[]> {
  const data = await api.get(`applications/${applicationId}/history`).json()
  return applicationHistoryResponseSchema.parse(data).history
}

/** GET /api/admin/applications?status=… — bank queue (bank roles only, 403 for client). */
export async function fetchAdminApplications(status?: string | null): Promise<Application[]> {
  const data = await api
    .get('admin/applications', { searchParams: status ? { status } : {} })
    .json()
  return myApplicationsResponseSchema.parse(data).applications
}

/** POST /api/admin/applications/{id}/request-info — bank_manager only. */
export async function adminRequestInfo(
  applicationId: number,
  message: string,
): Promise<Application> {
  const data = await api
    .post(`admin/applications/${applicationId}/request-info`, { json: { message } })
    .json()
  return applicationCreatedResponseSchema.parse(data).application
}

/** POST /api/admin/applications/{id}/assign-analyst — bank_manager only. */
export async function adminAssignAnalyst(applicationId: number): Promise<Application> {
  const data = await api.post(`admin/applications/${applicationId}/assign-analyst`).json()
  return applicationCreatedResponseSchema.parse(data).application
}

export type AnalystDecisionValue = 'approved' | 'approved_with_changes' | 'rejected'

/** POST /api/admin/applications/{id}/decision — bank_analyst only, manual_review. */
export async function adminDecision(
  applicationId: number,
  decision: AnalystDecisionValue,
  reason: string,
): Promise<Application> {
  const data = await api
    .post(`admin/applications/${applicationId}/decision`, { json: { decision, reason } })
    .json()
  return applicationCreatedResponseSchema.parse(data).application
}
