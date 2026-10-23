/**
 * Field visibility by audience. The backend returns score/factors/
 * analyst_decision to the application owner too — the CLIENT cabinet must
 * never render them (PRD §5.2: балл скоринга клиенту не показывается);
 * they exist in the parsed types only for the bank АРМ (stage 6).
 */

/** Bank-only fields of Application / DecisionDetails. */
export const BANK_ONLY_APPLICATION_FIELDS = ['score'] as const
export const BANK_ONLY_DECISION_FIELDS = ['score', 'factors', 'analystDecision'] as const

/** Client-safe: has the bank made any decision (gates «Объяснить решение»). */
export const hasDecision = (decision: string | null): boolean => decision != null
