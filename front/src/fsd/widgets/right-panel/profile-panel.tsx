'use client'

import { useState } from 'react'
import { useMyProfile } from '@/fsd/entities/profile/model/queries'
import type { BusinessProfile } from '@/fsd/entities/profile/model/schemas'
import {
  useCreateProfile,
  useUpdateProfile,
} from '@/fsd/features/edit-profile/model/use-save-profile'
import { formatMoney } from '@/fsd/shared/lib/format'
import { Button } from '@/fsd/shared/ui/button'
import { Input } from '@/fsd/shared/ui/input'
import { Skeleton } from '@/fsd/shared/ui/skeleton'

interface FieldDef {
  key: keyof Pick<
    BusinessProfile,
    | 'businessName'
    | 'industry'
    | 'fundingPurpose'
    | 'requestedAmount'
    | 'businessAgeMonths'
    | 'monthlyRevenue'
    | 'monthlyProfit'
    | 'preferredTermMonths'
    | 'maxMonthlyPayment'
  >
  label: string
  kind: 'text' | 'money' | 'months'
}

const FIELD_DEFS: FieldDef[] = [
  { key: 'businessName', label: 'Название бизнеса', kind: 'text' },
  { key: 'industry', label: 'Отрасль', kind: 'text' },
  { key: 'fundingPurpose', label: 'Цель финансирования', kind: 'text' },
  { key: 'requestedAmount', label: 'Желаемая сумма', kind: 'money' },
  { key: 'businessAgeMonths', label: 'Стаж бизнеса', kind: 'months' },
  { key: 'monthlyRevenue', label: 'Выручка в месяц', kind: 'money' },
  { key: 'monthlyProfit', label: 'Прибыль в месяц', kind: 'money' },
  { key: 'preferredTermMonths', label: 'Желаемый срок', kind: 'months' },
  { key: 'maxMonthlyPayment', label: 'Комфортный платёж', kind: 'money' },
]

// camelCase form key → snake_case wire key (extra="forbid" on the backend).
const WIRE_KEYS = {
  businessName: 'business_name',
  industry: 'industry',
  fundingPurpose: 'funding_purpose',
  requestedAmount: 'requested_amount',
  businessAgeMonths: 'business_age_months',
  monthlyRevenue: 'monthly_revenue',
  monthlyProfit: 'monthly_profit',
  preferredTermMonths: 'preferred_term_months',
  maxMonthlyPayment: 'max_monthly_payment',
} as const

function formatFieldValue(field: FieldDef, value: string | number | null): string {
  if (value == null || value === '') return '—'
  if (field.kind === 'money') return formatMoney(Number(value))
  if (field.kind === 'months') return `${value} мес.`
  return String(value)
}

type FormValues = Record<FieldDef['key'], string>

function profileToFormValues(profile: BusinessProfile | null): FormValues {
  const values = {} as FormValues
  for (const field of FIELD_DEFS) {
    const raw = profile?.[field.key]
    values[field.key] = raw == null ? '' : String(raw)
  }
  return values
}

function ProfileForm({
  profile,
  onDone,
}: {
  /** null → create mode (POST), profile → edit mode (PATCH). */
  profile: BusinessProfile | null
  onDone: () => void
}) {
  const isCreate = profile == null
  const createProfile = useCreateProfile()
  const updateProfile = useUpdateProfile(profile?.id ?? -1)
  const [values, setValues] = useState<FormValues>(() => profileToFormValues(profile))
  const [error, setError] = useState<string | null>(null)

  const isPending = createProfile.isPending || updateProfile.isPending
  const visibleFields = isCreate
    ? FIELD_DEFS.filter((f) => f.key === 'industry' || f.key === 'fundingPurpose')
    : FIELD_DEFS

  const handleSubmit = (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    const payload: Record<string, string | number> = {}
    for (const field of visibleFields) {
      const raw = values[field.key].trim()
      if (raw === '') continue
      if (field.kind === 'text') {
        payload[WIRE_KEYS[field.key]] = raw
      } else {
        const parsed = Number(raw.replace(/\s/g, '').replace(',', '.'))
        if (!Number.isFinite(parsed) || parsed < 0) {
          setError(`Поле «${field.label}» должно быть неотрицательным числом`)
          return
        }
        payload[WIRE_KEYS[field.key]] = parsed
      }
    }
    if (isCreate) {
      if (!payload.industry || !payload.funding_purpose) {
        setError('Заполните отрасль и цель финансирования')
        return
      }
      createProfile.mutate(payload as never, { onSuccess: onDone })
    } else {
      updateProfile.mutate(payload, { onSuccess: onDone })
    }
  }

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3" noValidate>
      {visibleFields.map((field) => (
        <div key={field.key} className="flex flex-col gap-1">
          <label htmlFor={`profile-${field.key}`} className="text-xs font-medium">
            {field.label}
            {isCreate && <span className="text-negative"> *</span>}
          </label>
          <Input
            id={`profile-${field.key}`}
            value={values[field.key]}
            onChange={(e) => setValues((prev) => ({ ...prev, [field.key]: e.target.value }))}
            inputMode={field.kind === 'text' ? undefined : 'decimal'}
            placeholder={field.kind === 'text' ? undefined : '0'}
          />
        </div>
      ))}
      {error && <p className="text-xs text-negative">{error}</p>}
      <div className="mt-1 flex gap-2">
        <Button type="submit" size="sm" disabled={isPending}>
          {isPending ? 'Сохраняем…' : 'Сохранить'}
        </Button>
        <Button type="button" size="sm" variant="ghost" onClick={onDone} disabled={isPending}>
          Отмена
        </Button>
      </div>
    </form>
  )
}

/**
 * Right-panel tab «Мой профиль»: business profile filled by the assistant
 * (or manually), with edit (PATCH) and create (POST) modes.
 */
export function ProfilePanel() {
  const profileQuery = useMyProfile()
  const [mode, setMode] = useState<'view' | 'form'>('view')

  if (profileQuery.isLoading) {
    return (
      <div className="flex flex-col gap-3">
        {FIELD_DEFS.slice(0, 6).map((field) => (
          <Skeleton key={field.key} className="h-8 w-full" />
        ))}
      </div>
    )
  }

  const profile = profileQuery.data ?? null

  if (mode === 'form') {
    return <ProfileForm profile={profile} onDone={() => setMode('view')} />
  }

  if (profile == null) {
    return (
      <div className="flex flex-col items-center gap-3 py-10 text-center">
        <p className="text-sm font-bold">Профиль ещё не заполнен</p>
        <p className="text-xs leading-relaxed text-text-secondary">
          Профиль заполнится в диалоге с ассистентом — или создайте его вручную.
        </p>
        <Button size="sm" variant="outline" onClick={() => setMode('form')}>
          Создать профиль
        </Button>
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-4">
      <dl className="flex flex-col divide-y divide-border">
        {FIELD_DEFS.map((field) => (
          <div key={field.key} className="flex items-baseline justify-between gap-3 py-2">
            <dt className="text-xs text-text-secondary">{field.label}</dt>
            <dd className="text-right text-sm font-medium">
              {formatFieldValue(field, profile[field.key])}
            </dd>
          </div>
        ))}
      </dl>
      <Button size="sm" variant="outline" onClick={() => setMode('form')}>
        Редактировать
      </Button>
    </div>
  )
}
