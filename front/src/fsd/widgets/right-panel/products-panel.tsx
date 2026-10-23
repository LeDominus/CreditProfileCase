'use client'

import { SparklesIcon } from 'lucide-react'
import { useRecommendationsStore } from '@/fsd/entities/product/model/recommendations-store'
import type { Recommendation } from '@/fsd/entities/product/model/schemas'
import { useMyProfile } from '@/fsd/entities/profile/model/queries'
import { usePickRecommendations } from '@/fsd/features/pick-products/model/use-pick-recommendations'
import { CompareProductsDialog } from '@/fsd/features/pick-products/ui/compare-products-dialog'
import { ApplicationParams } from '@/fsd/features/select-product/ui/application-params'
import { useApplicationDraft } from '@/fsd/features/submit-application/model/draft-store'
import { formatMoney, formatRate } from '@/fsd/shared/lib/format'
import { Badge } from '@/fsd/shared/ui/badge'
import { Button } from '@/fsd/shared/ui/button'

function ProductCard({
  item,
  isBest,
  isSelected,
  onSelect,
}: {
  item: Recommendation
  isBest: boolean
  isSelected: boolean
  onSelect: () => void
}) {
  return (
    <div
      className={
        isSelected
          ? 'flex flex-col gap-2 rounded-xl border border-accent p-3.5'
          : 'flex flex-col gap-2 rounded-xl border border-border p-3.5'
      }
    >
      <div className="flex items-center justify-between gap-2">
        <span className="text-sm font-bold">{item.name}</span>
        {isBest && <Badge variant="accent">Лучший выбор</Badge>}
      </div>
      <p className="text-xs text-text-secondary">{item.tagline}</p>
      <div className="flex items-baseline justify-between text-sm">
        <span className="text-xs text-text-secondary">Сумма</span>
        <span className="font-medium">
          {formatMoney(item.minAmount)} — {formatMoney(item.maxAmount)}
        </span>
      </div>
      <div className="flex items-baseline justify-between text-sm">
        <span className="text-xs text-text-secondary">Срок</span>
        <span className="font-medium">
          {item.minTerm}–{item.maxTerm} мес.
        </span>
      </div>
      <div className="flex items-baseline justify-between text-sm">
        <span className="text-xs text-text-secondary">Ставка</span>
        <span className="font-medium">{formatRate(item.rate)}</span>
      </div>
      <div className="flex items-baseline justify-between text-sm">
        <span className="text-xs text-text-secondary">Платёж в месяц</span>
        <span className="font-medium">{formatMoney(item.monthlyPayment)}</span>
      </div>
      <Button size="sm" variant={isSelected ? 'secondary' : 'outline'} onClick={onSelect}>
        {isSelected ? 'Выбран' : 'Выбрать'}
      </Button>
    </div>
  )
}

/**
 * Right-panel tab «Рекомендуемые продукты»: gated product picker, full cards
 * from the recommendations store (chat pipeline or manual pick), catalog
 * comparison and the application params block.
 */
export function ProductsPanel() {
  const recommendations = useRecommendationsStore((s) => s.recommendations)
  const profileQuery = useMyProfile()
  const pick = usePickRecommendations()
  const selectedProduct = useApplicationDraft((s) => s.selectedProduct)
  const selectProduct = useApplicationDraft((s) => s.selectProduct)

  const profile = profileQuery.data ?? null

  const handleSelect = (item: Recommendation) => {
    if (selectedProduct?.id === item.id) return
    const amount = Math.min(
      Math.max(profile?.requestedAmount ?? item.minAmount, item.minAmount),
      item.maxAmount,
    )
    const term = Math.min(
      Math.max(profile?.preferredTermMonths ?? item.minTerm, item.minTerm),
      item.maxTerm,
    )
    selectProduct(item, amount, term)
  }

  return (
    <div className="flex flex-col gap-3">
      <Button
        size="sm"
        onClick={() => pick.mutate()}
        disabled={!pick.isComplete || pick.isPending}
        title={
          pick.isComplete
            ? undefined
            : 'Заполните в диалоге стаж, выручку, прибыль, сумму и срок — и подбор станет доступен'
        }
      >
        {pick.isPending ? 'Подбираем…' : 'Подобрать продукты'}
      </Button>
      {!pick.isComplete && (
        <p className="text-[11px] leading-relaxed text-text-secondary">
          Кнопка активна, когда в профиле заполнены стаж бизнеса, выручка и прибыль в месяц,
          желаемая сумма и срок. Ассистент заполнит их из диалога.
        </p>
      )}

      {recommendations.length === 0 ? (
        <div className="flex flex-col items-center gap-3 py-8 text-center">
          <span className="inline-flex size-11 items-center justify-center rounded-full bg-accent/10 text-accent">
            <SparklesIcon className="size-5" />
          </span>
          <p className="text-sm font-bold">Подбор пока пуст</p>
          <p className="max-w-[260px] text-xs leading-relaxed text-text-secondary">
            Рекомендации появятся в диалоге, когда ассистент соберёт профиль, — или нажмите
            «Подобрать продукты».
          </p>
        </div>
      ) : (
        recommendations.map((item, index) => (
          <ProductCard
            key={item.id}
            item={item}
            isBest={index === 0}
            isSelected={selectedProduct?.id === item.id}
            onSelect={() => handleSelect(item)}
          />
        ))
      )}

      <ApplicationParams />

      <CompareProductsDialog />
    </div>
  )
}
