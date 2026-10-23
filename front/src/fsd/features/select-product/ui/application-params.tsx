'use client'

import { XIcon } from 'lucide-react'

import { usePaymentCalc } from '@/fsd/features/calc-payment/model/use-payment-calc'
import { useApplicationDraft } from '@/fsd/features/submit-application/model/draft-store'
import { formatMoney } from '@/fsd/shared/lib/format'
import { Button } from '@/fsd/shared/ui/button'
import { Checkbox } from '@/fsd/shared/ui/checkbox'
import { Input } from '@/fsd/shared/ui/input'
import { Skeleton } from '@/fsd/shared/ui/skeleton'
import { Slider } from '@/fsd/shared/ui/slider'

const STEP_AMOUNT = 50_000

function clamp(value: number, min: number, max: number): number {
  return Math.min(max, Math.max(min, value))
}

/**
 * «Параметры заявки»: amount/term within the selected product's ranges,
 * debounced annuity calculation, disclaimers and the data-confirmation
 * checkbox gating the «Оформить заявку» button.
 */
export function ApplicationParams() {
  const product = useApplicationDraft((s) => s.selectedProduct)
  const amount = useApplicationDraft((s) => s.amount)
  const term = useApplicationDraft((s) => s.term)
  const dataConfirmed = useApplicationDraft((s) => s.dataConfirmed)
  const setAmount = useApplicationDraft((s) => s.setAmount)
  const setTerm = useApplicationDraft((s) => s.setTerm)
  const setDataConfirmed = useApplicationDraft((s) => s.setDataConfirmed)
  const clearProduct = useApplicationDraft((s) => s.clearProduct)
  const setFormOpen = useApplicationDraft((s) => s.setFormOpen)

  const payment = usePaymentCalc(product?.rate ?? null, amount, term)

  if (product == null || amount == null || term == null) return null

  return (
    <div className="flex flex-col gap-4 rounded-xl border border-accent/30 bg-accent/5 p-4">
      <div className="flex items-start justify-between gap-2">
        <div className="flex flex-col">
          <span className="text-xs font-bold tracking-wider text-accent uppercase">
            Параметры заявки
          </span>
          <span className="text-sm font-bold">{product.name}</span>
        </div>
        <button
          type="button"
          onClick={clearProduct}
          aria-label="Сбросить выбор продукта"
          className="inline-flex size-6 cursor-pointer items-center justify-center rounded-md text-text-secondary hover:bg-bg-secondary hover:text-text-primary"
        >
          <XIcon className="size-3.5" />
        </button>
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-baseline justify-between">
          <label htmlFor="draft-amount" className="text-xs text-text-secondary">
            Сумма кредита
          </label>
          <span className="text-xs text-text-secondary">
            {formatMoney(product.minAmount)} — {formatMoney(product.maxAmount)}
          </span>
        </div>
        <Input
          id="draft-amount"
          inputMode="numeric"
          value={amount}
          onChange={(e) => {
            const parsed = Number(e.target.value.replace(/\D/g, ''))
            if (Number.isFinite(parsed)) setAmount(clamp(parsed, 0, product.maxAmount))
          }}
          onBlur={() => setAmount(clamp(amount, product.minAmount, product.maxAmount))}
        />
        <Slider
          value={amount}
          min={product.minAmount}
          max={product.maxAmount}
          step={STEP_AMOUNT}
          onValueChange={(value) =>
            setAmount(Array.isArray(value) ? Number(value[0]) : (value as number))
          }
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <div className="flex items-baseline justify-between">
          <label htmlFor="draft-term" className="text-xs text-text-secondary">
            Срок, месяцев
          </label>
          <span className="text-xs text-text-secondary">
            {product.minTerm}–{product.maxTerm} мес.
          </span>
        </div>
        <Input
          id="draft-term"
          inputMode="numeric"
          value={term}
          onChange={(e) => {
            const parsed = Number(e.target.value.replace(/\D/g, ''))
            if (Number.isFinite(parsed)) setTerm(clamp(parsed, 0, product.maxTerm))
          }}
          onBlur={() => setTerm(clamp(term, product.minTerm, product.maxTerm))}
        />
        <Slider
          value={term}
          min={product.minTerm}
          max={product.maxTerm}
          step={1}
          onValueChange={(value) =>
            setTerm(Array.isArray(value) ? Number(value[0]) : (value as number))
          }
        />
      </div>

      <div className="flex flex-col gap-1.5 rounded-lg bg-bg-primary p-3">
        {payment.isLoading || payment.calculation == null ? (
          <>
            <Skeleton className="h-5 w-full" />
            <Skeleton className="h-5 w-full" />
            <Skeleton className="h-5 w-full" />
          </>
        ) : (
          <>
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-text-secondary">Платёж в месяц</span>
              <span className="text-base font-bold text-accent">
                {formatMoney(payment.calculation.monthlyPayment)}
              </span>
            </div>
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-text-secondary">Всего к возврату</span>
              <span className="font-medium">{formatMoney(payment.calculation.totalRepayment)}</span>
            </div>
            <div className="flex items-baseline justify-between text-sm">
              <span className="text-text-secondary">Переплата</span>
              <span className="font-medium">{formatMoney(payment.calculation.overpayment)}</span>
            </div>
          </>
        )}
      </div>

      <p className="text-[11px] leading-relaxed text-text-secondary">
        Расчёт предварительный и не является офертой банка. Итоговые условия определяются по
        результатам рассмотрения заявки. Решение демонстрационное.
      </p>

      <div className="flex items-start gap-2.5 text-xs leading-relaxed">
        <Checkbox
          aria-label="Подтверждение корректности данных"
          checked={dataConfirmed}
          onCheckedChange={(checked) => setDataConfirmed(checked === true)}
          className="mt-0.5"
        />
        <span className="select-none">
          Подтверждаю, что указанные данные корректны, и согласен на их проверку банком
        </span>
      </div>

      <Button disabled={!dataConfirmed} onClick={() => setFormOpen(true)}>
        Оформить заявку
      </Button>
    </div>
  )
}
