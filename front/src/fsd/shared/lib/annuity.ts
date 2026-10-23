/**
 * Local annuity fallback (mirrors backend src/core/calc_payment.py) — used
 * when POST /api/profile/{id}/payment is unavailable. Formula:
 * payment = P · r(1+r)^n / ((1+r)^n − 1), r = annualRate/100/12.
 */
export interface AnnuityResult {
  monthlyPayment: number
  totalRepayment: number
  overpayment: number
}

export function calcAnnuity(principal: number, annualRate: number, months: number): AnnuityResult {
  if (principal <= 0 || months <= 0) {
    return { monthlyPayment: 0, totalRepayment: 0, overpayment: 0 }
  }
  const r = annualRate / 100 / 12
  const factor = (1 + r) ** months
  const monthlyPayment = (principal * r * factor) / (factor - 1)
  const totalRepayment = monthlyPayment * months
  return {
    monthlyPayment,
    totalRepayment,
    overpayment: totalRepayment - principal,
  }
}
