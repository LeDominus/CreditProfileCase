'use client'

import { useState } from 'react'

import type { Application } from '@/fsd/entities/application/model/schemas'
import { useProducts } from '@/fsd/entities/product/model/queries'
import {
  useSubmitDraft,
  useUpdateDraft,
} from '@/fsd/features/application-actions/model/use-application-actions'
import { calcAnnuity } from '@/fsd/shared/lib/annuity'
import { formatMoney } from '@/fsd/shared/lib/format'
import { Button } from '@/fsd/shared/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from '@/fsd/shared/ui/dialog'
import { Input } from '@/fsd/shared/ui/input'

function EditDraftDialog({
  application,
  open,
  onClose,
}: {
  application: Application
  open: boolean
  onClose: () => void
}) {
  const productsQuery = useProducts()
  const updateDraft = useUpdateDraft(application.id)
  const product = productsQuery.data?.find((p) => p.id === application.productId)

  const [amount, setAmount] = useState(application.requestedAmount)
  const [term, setTerm] = useState(application.termMonths)
  const [error, setError] = useState<string | null>(null)

  const preview = product != null ? calcAnnuity(amount, product.rate, term) : null

  const handleSave = () => {
    if (product == null) return
    if (amount < product.minAmount || amount > product.maxAmount) {
      setError(
        `Сумма по продукту — от ${formatMoney(product.minAmount)} до ${formatMoney(product.maxAmount)}`,
      )
      return
    }
    if (term < product.minTerm || term > product.maxTerm) {
      setError(`Срок по продукту — от ${product.minTerm} до ${product.maxTerm} мес.`)
      return
    }
    setError(null)
    updateDraft.mutate({ requested_amount: amount, term_months: term }, { onSuccess: onClose })
  }

  return (
    <Dialog open={open} onOpenChange={(next) => !next && onClose()}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Изменить сумму и срок</DialogTitle>
          <DialogDescription>
            {application.productName}: {formatMoney(product?.minAmount ?? 0)} —{' '}
            {formatMoney(product?.maxAmount ?? 0)}, {product?.minTerm}–{product?.maxTerm} мес.
          </DialogDescription>
        </DialogHeader>
        <div className="flex flex-col gap-3">
          <div className="flex flex-col gap-1">
            <label htmlFor="edit-amount" className="text-xs font-medium">
              Сумма заявки, ₽
            </label>
            <Input
              id="edit-amount"
              inputMode="numeric"
              value={amount}
              onChange={(e) => {
                const parsed = Number(e.target.value.replace(/\D/g, ''))
                if (Number.isFinite(parsed)) setAmount(parsed)
              }}
            />
          </div>
          <div className="flex flex-col gap-1">
            <label htmlFor="edit-term" className="text-xs font-medium">
              Срок, месяцев
            </label>
            <Input
              id="edit-term"
              inputMode="numeric"
              value={term}
              onChange={(e) => {
                const parsed = Number(e.target.value.replace(/\D/g, ''))
                if (Number.isFinite(parsed)) setTerm(parsed)
              }}
            />
          </div>
          {preview && (
            <p className="text-xs text-text-secondary">
              Платёж ≈ {formatMoney(preview.monthlyPayment)}/мес · всего к возврату{' '}
              {formatMoney(preview.totalRepayment)}
            </p>
          )}
          {error && <p className="text-xs text-negative">{error}</p>}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" size="sm" onClick={onClose} disabled={updateDraft.isPending}>
              Отмена
            </Button>
            <Button
              size="sm"
              onClick={handleSave}
              disabled={updateDraft.isPending || product == null}
            >
              {updateDraft.isPending ? 'Сохраняем…' : 'Сохранить изменения'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}

/** draft: «Отправить заявку» (submit + pipeline) + «Изменить сумму и срок». */
export function DraftActions({ application }: { application: Application }) {
  const submitDraft = useSubmitDraft(application.id)
  const [editOpen, setEditOpen] = useState(false)

  return (
    <div className="flex flex-col gap-2">
      <Button size="sm" onClick={() => submitDraft.mutate()} disabled={submitDraft.isPending}>
        {submitDraft.isPending ? 'Отправляем…' : 'Отправить заявку'}
      </Button>
      <Button size="sm" variant="outline" onClick={() => setEditOpen(true)}>
        Изменить сумму и срок
      </Button>
      {editOpen && (
        <EditDraftDialog
          application={application}
          open={editOpen}
          onClose={() => setEditOpen(false)}
        />
      )}
    </div>
  )
}
