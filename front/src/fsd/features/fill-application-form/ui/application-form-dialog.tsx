'use client'

import { PaperclipIcon, PlusIcon, XIcon } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'
import { toast } from 'sonner'
import type { Product } from '@/fsd/entities/product/model/schemas'
import { useMyProfile } from '@/fsd/entities/profile/model/queries'
import type { BusinessProfile } from '@/fsd/entities/profile/model/schemas'
import { useApplicationDraft } from '@/fsd/features/submit-application/model/draft-store'
import {
  SUBMIT_STEP_LABELS,
  useSubmitApplication,
} from '@/fsd/features/submit-application/model/use-submit-application'
import { formatFileSize } from '@/fsd/shared/lib/format'
import { Button } from '@/fsd/shared/ui/button'
import { Checkbox } from '@/fsd/shared/ui/checkbox'
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/fsd/shared/ui/dialog'
import { Input } from '@/fsd/shared/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/fsd/shared/ui/select'
import { Textarea } from '@/fsd/shared/ui/textarea'

import {
  CONSENT_CREDIT_TEXT,
  CONSENT_PD_TEXT,
  CREDIT_PRODUCT_BY_ID,
  CREDIT_PRODUCT_TYPES,
  clientDataWireSchema,
  TAXATION_SYSTEMS,
} from '../model/client-data-schema'
import { useRegistryLookup } from '../model/use-registry-lookup'

interface OwnerEntry {
  id: number
  fullName: string
  passport: string
}

/** All editable values are strings; numbers/arrays are assembled on submit. */
interface FormState {
  inn: string
  creditProduct: (typeof CREDIT_PRODUCT_TYPES)[number]
  creditSum: string
  creditTerm: string
  creditTarget: string
  companyName: string
  ogrn: string
  registeredAddress: string
  registrationDate: string
  typeOfActivity: string
  companySupervisor: string
  companyMembers: string
  companyPlace: string
  taxationSystem: string
  companyMembersCount: string
  companyPhone: string
  companyEmail: string
  fullName: string
  passport: string
  passportIssuedBy: string
  placeOfBirth: string
  registrationAddress: string
  innFizFace: string
  supervisorPhone: string
  supervisorEmail: string
  owners: OwnerEntry[]
  revenue: string
  profit: string
  loans: string
  hasDebts: boolean
  consentPd: boolean
  consentCredit: boolean
}

let ownerIdCounter = 0

function initialFormState(
  product: Product,
  amount: number,
  term: number,
  profile: BusinessProfile | null,
): FormState {
  return {
    inn: '',
    creditProduct: CREDIT_PRODUCT_BY_ID[product.id] ?? 'оборотный кредит',
    creditSum: String(amount),
    creditTerm: String(term),
    creditTarget: profile?.fundingPurpose ?? product.purpose,
    companyName: '',
    ogrn: '',
    registeredAddress: '',
    registrationDate: '',
    typeOfActivity: '',
    companySupervisor: '',
    companyMembers: '',
    companyPlace: '',
    taxationSystem: TAXATION_SYSTEMS[0],
    companyMembersCount: '1',
    companyPhone: '',
    companyEmail: '',
    fullName: '',
    passport: '',
    passportIssuedBy: '',
    placeOfBirth: '',
    registrationAddress: '',
    innFizFace: '',
    supervisorPhone: '',
    supervisorEmail: '',
    owners: [],
    revenue: '',
    profit: '',
    loans: '',
    hasDebts: false,
    consentPd: false,
    consentCredit: false,
  }
}

function parseNumber(raw: string): number {
  return Number(raw.replace(/\s/g, '').replace(',', '.'))
}

function splitLines(raw: string): string[] {
  return raw
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="flex flex-col gap-3 rounded-xl border border-border p-4">
      <h3 className="text-sm font-bold">{title}</h3>
      {children}
    </section>
  )
}

function FieldError({ message }: { message?: string }) {
  if (!message) return null
  return <p className="text-xs text-negative">{message}</p>
}

function FileChip({ file, onRemove }: { file: File; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-2 rounded-lg bg-bg-secondary px-2.5 py-1.5 text-xs">
      <PaperclipIcon className="size-3.5 text-text-secondary" />
      <span className="max-w-48 truncate font-medium">{file.name}</span>
      <span className="text-text-secondary">{formatFileSize(file.size)}</span>
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Удалить ${file.name}`}
        className="cursor-pointer text-text-secondary hover:text-negative"
      >
        <XIcon className="size-3.5" />
      </button>
    </span>
  )
}

/**
 * «Данные для заявки»: the full ClientDataRequest form. NON-dismissible like
 * the Streamlit reference (@st.dialog dismissible=False): controlled root
 * swallows Esc/outside-click close; only «Отмена» or a successful submit
 * closes it. Sections scroll inside the dialog (same layout as the
 * reference — chosen over a stepper to keep everything visible at once).
 * Attached files never leave the browser; only file names go to the API.
 */
export function ApplicationFormDialog() {
  const formOpen = useApplicationDraft((s) => s.formOpen)
  const setFormOpen = useApplicationDraft((s) => s.setFormOpen)
  const product = useApplicationDraft((s) => s.selectedProduct)
  const amount = useApplicationDraft((s) => s.amount)
  const term = useApplicationDraft((s) => s.term)

  const profileQuery = useMyProfile()
  const lookup = useRegistryLookup()
  const { mutation: submitMutation, step } = useSubmitApplication()

  const [form, setForm] = useState<FormState | null>(null)
  const [errors, setErrors] = useState<Record<string, string>>({})
  const [passportScan, setPassportScan] = useState<File | null>(null)
  const [businessDocs, setBusinessDocs] = useState<File[]>([])

  const passportInputRef = useRef<HTMLInputElement>(null)
  const docsInputRef = useRef<HTMLInputElement>(null)

  // Prefill on open (credit params from the draft, target from the profile).
  // biome-ignore lint/correctness/useExhaustiveDependencies: prefill must run only when the dialog opens, not on every draft/profile change
  useEffect(() => {
    if (formOpen && product && amount != null && term != null) {
      setForm(initialFormState(product, amount, term, profileQuery.data ?? null))
      setErrors({})
      setPassportScan(null)
      setBusinessDocs([])
    }
  }, [formOpen])

  if (product == null) return null

  const set = <K extends keyof FormState>(key: K, value: FormState[K]) =>
    setForm((prev) => (prev ? { ...prev, [key]: value } : prev))

  const isOoo = (form?.inn.trim().length ?? 10) === 10

  const handleLookup = async () => {
    if (!form) return
    if (!lookup.isValidInn(form.inn)) {
      setErrors((prev) => ({ ...prev, 'company.inn': 'ИНН — 10 цифр (ООО) или 12 (ИП)' }))
      return
    }
    const entry = await lookup.mutateAsync(form.inn)
    if (entry == null) return
    setForm((prev) => {
      if (!prev) return prev
      const ownersNames = entry.supervisor.ownersFullName ?? []
      const ownersPassports = entry.supervisor.ownersPassport ?? []
      return {
        ...prev,
        companyName: entry.company.companyName,
        ogrn: entry.company.ogrn,
        registeredAddress: entry.company.registeredAddress,
        registrationDate: entry.company.registrationDate.slice(0, 10),
        typeOfActivity: entry.company.typeOfActivity,
        companySupervisor: entry.company.companySupervisor,
        companyMembers: entry.company.companyMembers.join('\n'),
        companyPlace: entry.company.companyPlace,
        taxationSystem: TAXATION_SYSTEMS.includes(
          entry.company.taxationSystem as (typeof TAXATION_SYSTEMS)[number],
        )
          ? entry.company.taxationSystem
          : TAXATION_SYSTEMS[0],
        companyMembersCount: String(entry.company.companyMembersCount),
        companyPhone: entry.company.companyPhone,
        companyEmail: entry.company.companyEmail,
        fullName: entry.supervisor.fullName,
        passport: entry.supervisor.passport,
        passportIssuedBy: entry.supervisor.passportIssuedBy,
        placeOfBirth: entry.supervisor.placeOfBirth,
        registrationAddress: entry.supervisor.registrationAddress,
        innFizFace: entry.supervisor.innFizFace,
        supervisorPhone: entry.supervisor.supervisorPhone,
        supervisorEmail: entry.supervisor.supervisorEmail,
        owners: ownersNames.map((fullName, index) => ({
          id: ++ownerIdCounter,
          fullName,
          passport: ownersPassports[index] ?? '',
        })),
        revenue: String(entry.finance.revenue),
        profit: String(entry.finance.profit),
        loans: (entry.finance.currentLoansAndLeasing ?? []).join('\n'),
        hasDebts: entry.finance.hasDebts,
      }
    })
    setErrors({})
    toast.success(`Данные заполнены из реестра: ${entry.company.companyName}`)
  }

  const handleSubmit = () => {
    if (!form || !product) return
    const profileId = profileQuery.data?.id
    if (profileId == null) {
      toast.error('Профиль не найден — напишите ассистенту, чтобы он создал профиль')
      return
    }
    const ownersFilled = form.owners.filter((o) => o.fullName.trim() !== '')
    const wire = {
      credit: {
        credit_product: form.creditProduct,
        credit_sum: parseNumber(form.creditSum),
        credit_term_months: Math.trunc(parseNumber(form.creditTerm)),
        credit_target: form.creditTarget.trim(),
      },
      company: {
        inn: form.inn.trim(),
        company_name: form.companyName.trim(),
        ogrn: form.ogrn.trim(),
        registered_address: form.registeredAddress.trim(),
        registration_date: form.registrationDate,
        type_of_activity: form.typeOfActivity.trim(),
        company_supervisor: form.companySupervisor.trim(),
        company_members: splitLines(form.companyMembers),
        company_place: form.companyPlace.trim(),
        taxation_system: form.taxationSystem,
        company_members_count: Math.trunc(parseNumber(form.companyMembersCount)),
        company_phone: form.companyPhone.trim(),
        company_email: form.companyEmail.trim(),
      },
      supervisor: {
        full_name: form.fullName.trim(),
        passport: form.passport.trim(),
        passport_issued_by: form.passportIssuedBy.trim(),
        place_of_birth: form.placeOfBirth.trim(),
        citizenship: 'russian',
        registration_address: form.registrationAddress.trim(),
        inn_fiz_face: form.innFizFace.trim(),
        supervisor_phone: form.supervisorPhone.trim(),
        supervisor_email: form.supervisorEmail.trim(),
        owners_full_name:
          isOoo && ownersFilled.length > 0 ? ownersFilled.map((o) => o.fullName.trim()) : null,
        owners_passport:
          isOoo && ownersFilled.length > 0 ? ownersFilled.map((o) => o.passport.trim()) : null,
      },
      finance: {
        revenue: parseNumber(form.revenue),
        profit: parseNumber(form.profit),
        current_loans_and_leasing: splitLines(form.loans).length ? splitLines(form.loans) : null,
        has_debts: form.hasDebts,
      },
      documents: {
        supervisor_passport_scan: passportScan?.name ?? '',
        business_type: isOoo ? ('ooo' as const) : ('ip' as const),
        business_doc: businessDocs.map((file) => file.name),
      },
      consents: {
        personal_data_agreement: form.consentPd,
        credit_history_agreement: form.consentCredit,
      },
    }

    const parsed = clientDataWireSchema.safeParse(wire)
    if (!parsed.success) {
      const fieldErrors: Record<string, string> = {}
      for (const issue of parsed.error.issues) {
        const path = issue.path.join('.')
        if (!fieldErrors[path]) fieldErrors[path] = issue.message
      }
      setErrors(fieldErrors)
      toast.error('Проверьте обязательные поля формы')
      return
    }
    setErrors({})

    const creditSum = parsed.data.credit.credit_sum
    const creditTerm = parsed.data.credit.credit_term_months
    if (creditSum < product.minAmount || creditSum > product.maxAmount) {
      setErrors({
        'credit.credit_sum': `Сумма по продукту — от ${product.minAmount} до ${product.maxAmount} ₽`,
      })
      return
    }
    if (creditTerm < product.minTerm || creditTerm > product.maxTerm) {
      setErrors({
        'credit.credit_term_months': `Срок по продукту — от ${product.minTerm} до ${product.maxTerm} мес.`,
      })
      return
    }

    submitMutation.mutate({
      profile_id: profileId,
      product_id: product.id,
      requested_amount: creditSum,
      term_months: creditTerm,
      client_data: parsed.data,
    })
  }

  const field = (
    key: keyof FormState & string,
    errorKey: string,
    label: string,
    placeholder?: string,
  ) => (
    <div className="flex flex-col gap-1">
      <label htmlFor={`af-${key}`} className="text-xs font-medium">
        {label}
      </label>
      <Input
        id={`af-${key}`}
        value={(form?.[key] as string) ?? ''}
        onChange={(e) => set(key, e.target.value as never)}
        placeholder={placeholder}
        aria-invalid={Boolean(errors[errorKey])}
      />
      <FieldError message={errors[errorKey]} />
    </div>
  )

  const errorSummary = Object.values(errors).filter(Boolean)
  const isBusy = step !== 'idle'

  return (
    <Dialog
      open={formOpen}
      // Non-dismissible: swallow close requests (Esc/outside click);
      // only «Отмена» or a successful submit closes the dialog.
      onOpenChange={() => {}}
      disablePointerDismissal
    >
      <DialogContent showClose={false} className="max-h-[88vh] max-w-2xl gap-0 overflow-hidden p-0">
        <DialogHeader className="border-b border-border px-6 py-4">
          <DialogTitle>Данные для заявки</DialogTitle>
          <p className="text-xs text-text-secondary">
            Введите ИНН — компания, руководитель и финансы заполнятся из реестра. Проверьте данные,
            прикрепите документы и отметьте согласия.
          </p>
        </DialogHeader>

        <div className="flex min-h-0 flex-1 flex-col gap-4 overflow-y-auto px-6 py-4">
          <Section title="ИНН компании">
            <div className="flex items-start gap-2">
              <div className="flex-1">
                <Input
                  id="af-inn"
                  value={form?.inn ?? ''}
                  onChange={(e) => set('inn', e.target.value.replace(/\D/g, '').slice(0, 12))}
                  placeholder="10 цифр — ООО, 12 цифр — ИП"
                  inputMode="numeric"
                  aria-invalid={Boolean(errors['company.inn'])}
                />
                <FieldError message={errors['company.inn']} />
              </div>
              <Button
                variant="secondary"
                size="md"
                onClick={handleLookup}
                disabled={lookup.isPending || !(form?.inn ?? '').trim()}
              >
                {lookup.isPending ? 'Ищем…' : 'Заполнить по ИНН'}
              </Button>
            </div>
            {lookup.notFound && (
              <p className="text-xs text-attention">
                Компания не найдена в реестре — заполните данные вручную.
              </p>
            )}
          </Section>

          <Section title="О кредите">
            <div className="flex flex-col gap-1">
              <label htmlFor="af-creditProduct" className="text-xs font-medium">
                Тип кредита
              </label>
              <Select
                value={form?.creditProduct ?? 'оборотный кредит'}
                onValueChange={(value) =>
                  set('creditProduct', value as (typeof CREDIT_PRODUCT_TYPES)[number])
                }
              >
                <SelectTrigger id="af-creditProduct">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  {CREDIT_PRODUCT_TYPES.map((type) => (
                    <SelectItem key={type} value={type}>
                      {type}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="grid grid-cols-2 gap-3">
              {field('creditSum', 'credit.credit_sum', `Сумма, ₽ (от ${product.minAmount})`)}
              {field('creditTerm', 'credit.credit_term_months', 'Срок, мес.')}
            </div>
            {field('creditTarget', 'credit.credit_target', 'Цель кредита')}
          </Section>

          <Section title="О компании">
            {field('companyName', 'company.company_name', 'Название компании')}
            <div className="grid grid-cols-2 gap-3">
              {field('ogrn', 'company.ogrn', 'ОГРН')}
              <div className="flex flex-col gap-1">
                <label htmlFor="af-registrationDate" className="text-xs font-medium">
                  Дата регистрации
                </label>
                <Input
                  id="af-registrationDate"
                  type="date"
                  value={form?.registrationDate ?? ''}
                  onChange={(e) => set('registrationDate', e.target.value)}
                  aria-invalid={Boolean(errors['company.registration_date'])}
                />
                <FieldError message={errors['company.registration_date']} />
              </div>
            </div>
            {field('registeredAddress', 'company.registered_address', 'Юридический адрес')}
            {field('typeOfActivity', 'company.type_of_activity', 'Вид деятельности')}
            {field('companySupervisor', 'company.company_supervisor', 'Руководитель (ФИО)')}
            <div className="flex flex-col gap-1">
              <label htmlFor="af-companyMembers" className="text-xs font-medium">
                Участники компании (по одному в строке)
              </label>
              <Textarea
                id="af-companyMembers"
                rows={2}
                value={form?.companyMembers ?? ''}
                onChange={(e) => set('companyMembers', e.target.value)}
                aria-invalid={Boolean(errors['company.company_members'])}
              />
              <FieldError message={errors['company.company_members']} />
            </div>
            {field('companyPlace', 'company.company_place', 'Где фактически ведётся бизнес')}
            <div className="grid grid-cols-2 gap-3">
              <div className="flex flex-col gap-1">
                <label htmlFor="af-taxationSystem" className="text-xs font-medium">
                  Система налогообложения
                </label>
                <Select
                  value={form?.taxationSystem ?? TAXATION_SYSTEMS[0]}
                  onValueChange={(value) =>
                    set('taxationSystem', value as (typeof TAXATION_SYSTEMS)[number])
                  }
                >
                  <SelectTrigger id="af-taxationSystem">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    {TAXATION_SYSTEMS.map((system) => (
                      <SelectItem key={system} value={system}>
                        {system}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
              {field('companyMembersCount', 'company.company_members_count', 'Число сотрудников')}
            </div>
            <div className="grid grid-cols-2 gap-3">
              {field('companyPhone', 'company.company_phone', 'Телефон компании', '+79991234567')}
              {field('companyEmail', 'company.company_email', 'E-mail компании', 'info@company.ru')}
            </div>
          </Section>

          <Section title="О руководителе">
            {field('fullName', 'supervisor.full_name', 'ФИО')}
            <div className="grid grid-cols-2 gap-3">
              {field('passport', 'supervisor.passport', 'Паспорт (серия, номер)', '4509 123456')}
              {field('innFizFace', 'supervisor.inn_fiz_face', 'ИНН физлица', '12 цифр')}
            </div>
            {field(
              'passportIssuedBy',
              'supervisor.passport_issued_by',
              'Кем и когда выдан паспорт',
            )}
            {field(
              'placeOfBirth',
              'supervisor.place_of_birth',
              'Дата и место рождения',
              '01.01.1980, г. Москва',
            )}
            {field('registrationAddress', 'supervisor.registration_address', 'Адрес регистрации')}
            <div className="grid grid-cols-2 gap-3">
              {field(
                'supervisorPhone',
                'supervisor.supervisor_phone',
                'Мобильный телефон',
                '+79991234568',
              )}
              {field('supervisorEmail', 'supervisor.supervisor_email', 'E-mail')}
            </div>
          </Section>

          {isOoo && (
            <Section title="Владельцы с долей более 25%">
              {form?.owners.map((owner, index) => (
                <div key={owner.id} className="flex items-start gap-2">
                  <div className="flex-1">
                    <Input
                      value={owner.fullName}
                      onChange={(e) =>
                        set(
                          'owners',
                          (form?.owners ?? []).map((o, i) =>
                            i === index ? { ...o, fullName: e.target.value } : o,
                          ),
                        )
                      }
                      placeholder="ФИО владельца"
                    />
                  </div>
                  <div className="flex-1">
                    <Input
                      value={owner.passport}
                      onChange={(e) =>
                        set(
                          'owners',
                          (form?.owners ?? []).map((o, i) =>
                            i === index ? { ...o, passport: e.target.value } : o,
                          ),
                        )
                      }
                      placeholder="Паспорт"
                    />
                  </div>
                  <button
                    type="button"
                    aria-label="Удалить владельца"
                    onClick={() =>
                      set(
                        'owners',
                        (form?.owners ?? []).filter((_, i) => i !== index),
                      )
                    }
                    className="mt-2 cursor-pointer text-text-secondary hover:text-negative"
                  >
                    <XIcon className="size-4" />
                  </button>
                </div>
              ))}
              <Button
                variant="ghost"
                size="sm"
                onClick={() =>
                  set('owners', [
                    ...(form?.owners ?? []),
                    { id: ++ownerIdCounter, fullName: '', passport: '' },
                  ])
                }
              >
                <PlusIcon />
                Добавить владельца
              </Button>
              <FieldError message={errors['supervisor.owners_full_name']} />
            </Section>
          )}

          <Section title="О финансах">
            <div className="grid grid-cols-2 gap-3">
              {field('revenue', 'finance.revenue', 'Выручка за последний год, ₽', '48000000')}
              {field('profit', 'finance.profit', 'Прибыль за последний год, ₽', '6000000')}
            </div>
            <div className="flex flex-col gap-1">
              <label htmlFor="af-loans" className="text-xs font-medium">
                Текущие кредиты и лизинг (по одному в строке)
              </label>
              <Textarea
                id="af-loans"
                rows={2}
                value={form?.loans ?? ''}
                onChange={(e) => set('loans', e.target.value)}
                placeholder="Альфа-Банк, остаток 500000, платёж 60000"
              />
            </div>
            <div className="flex items-center gap-2.5 text-sm">
              <Checkbox
                aria-label="Есть долги по налогам и зарплате"
                checked={form?.hasDebts ?? false}
                onCheckedChange={(checked) => set('hasDebts', checked === true)}
              />
              <span className="select-none">Есть долги по налогам и зарплате</span>
            </div>
          </Section>

          <Section title="Документы">
            <div className="flex flex-col gap-2">
              <input
                ref={passportInputRef}
                type="file"
                hidden
                onChange={(e) => setPassportScan(e.target.files?.[0] ?? null)}
              />
              <Button variant="outline" size="sm" onClick={() => passportInputRef.current?.click()}>
                <PaperclipIcon />
                Скан паспорта руководителя
              </Button>
              {passportScan && (
                <FileChip file={passportScan} onRemove={() => setPassportScan(null)} />
              )}
            </div>
            <div className="flex flex-col gap-2">
              <input
                ref={docsInputRef}
                type="file"
                hidden
                multiple
                onChange={(e) =>
                  setBusinessDocs((prev) => [...prev, ...Array.from(e.target.files ?? [])])
                }
              />
              <Button variant="outline" size="sm" onClick={() => docsInputRef.current?.click()}>
                <PaperclipIcon />
                {isOoo ? 'Устав и отчётность ООО' : 'Декларация ИП'}, счёт или договор
              </Button>
              {businessDocs.map((file, index) => (
                <FileChip
                  key={`${file.name}-${index}`}
                  file={file}
                  onRemove={() => setBusinessDocs((prev) => prev.filter((_, i) => i !== index))}
                />
              ))}
            </div>
            <p className="text-[11px] text-text-secondary">
              Файлы не покидают браузер — в заявку передаются только имена (демо-упрощение по ТЗ).
            </p>
          </Section>

          <Section title="Согласия">
            <div className="flex items-start gap-2.5 text-xs leading-relaxed">
              <Checkbox
                aria-label="Согласие на обработку персональных данных"
                className="mt-0.5"
                checked={form?.consentPd ?? false}
                onCheckedChange={(checked) => set('consentPd', checked === true)}
              />
              <span className="select-none">{CONSENT_PD_TEXT}</span>
            </div>
            <FieldError message={errors['consents.personal_data_agreement']} />
            <div className="flex items-start gap-2.5 text-xs leading-relaxed">
              <Checkbox
                aria-label="Согласие на запрос кредитной истории"
                className="mt-0.5"
                checked={form?.consentCredit ?? false}
                onCheckedChange={(checked) => set('consentCredit', checked === true)}
              />
              <span className="select-none">{CONSENT_CREDIT_TEXT}</span>
            </div>
            <FieldError message={errors['consents.credit_history_agreement']} />
          </Section>
        </div>

        <div className="flex flex-col gap-3 border-t border-border px-6 py-4">
          {errorSummary.length > 0 && (
            <div className="flex flex-col gap-1 rounded-lg bg-negative/10 px-3 py-2">
              <p className="text-xs font-bold text-negative">Проверьте поля:</p>
              <ul className="max-h-24 list-disc overflow-y-auto pl-4 text-xs text-negative">
                {[...new Set(errorSummary)].map((message) => (
                  <li key={message}>{message}</li>
                ))}
              </ul>
            </div>
          )}
          {submitMutation.isError && (
            <p className="text-xs text-negative">
              {submitMutation.error instanceof Error
                ? submitMutation.error.message
                : 'Не удалось создать заявку'}
            </p>
          )}
          <div className="flex justify-end gap-2">
            <Button variant="ghost" onClick={() => setFormOpen(false)} disabled={isBusy}>
              Отмена
            </Button>
            <Button onClick={handleSubmit} disabled={isBusy}>
              {isBusy ? SUBMIT_STEP_LABELS[step] : 'Отправить заявку'}
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  )
}
