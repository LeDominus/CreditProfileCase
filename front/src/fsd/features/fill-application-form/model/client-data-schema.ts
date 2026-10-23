import { z } from 'zod'

/**
 * Client-side mirror of ClientDataRequest (src/schemas/profile_schema.py) —
 * validates the assembled wire payload before POST /api/applications.
 * Backend models are extra="forbid": only these fields may be sent.
 */

export const TAXATION_SYSTEMS = [
  'ОСНО',
  'УСН доходы',
  'УСН доходы минус расходы',
  'ПСН',
  'ЕСХН',
] as const

export const CREDIT_PRODUCT_TYPES = [
  'оборотный кредит',
  'инвестиционный кредит',
  'овердрафт',
] as const

/** Default credit type per catalog product id (mirrors CREDIT_PRODUCT_BY_ID in app.py). */
export const CREDIT_PRODUCT_BY_ID: Record<number, (typeof CREDIT_PRODUCT_TYPES)[number]> = {
  1: 'оборотный кредит',
  2: 'инвестиционный кредит',
  3: 'инвестиционный кредит',
  4: 'оборотный кредит',
}

const INN_PATTERN = /^\d{10}(\d{2})?$/
const PERSON_INN_PATTERN = /^\d{12}$/
const PHONE_PATTERN = /^\+7\d{10}$/
const EMAIL_PATTERN = /^[^@\s]+@[^@\s]+\.[^@\s]+$/

const required = (label: string) => z.string().min(1, `Заполните: ${label}`)

export const clientDataWireSchema = z.object({
  credit: z.object({
    credit_product: z.enum(CREDIT_PRODUCT_TYPES),
    credit_sum: z.number().positive('Сумма кредита должна быть больше нуля'),
    credit_term_months: z.number().int().positive('Срок кредита должен быть больше нуля'),
    credit_target: required('цель кредита'),
  }),
  company: z.object({
    inn: z.string().regex(INN_PATTERN, 'ИНН — 10 цифр (ООО) или 12 (ИП)'),
    company_name: required('название компании'),
    ogrn: required('ОГРН'),
    registered_address: required('юридический адрес'),
    registration_date: required('дата регистрации'),
    type_of_activity: required('вид деятельности'),
    company_supervisor: required('руководитель компании'),
    company_members: z.array(z.string().min(1)).min(1, 'Укажите участников компании'),
    company_place: required('адрес ведения бизнеса'),
    taxation_system: required('система налогообложения'),
    company_members_count: z.number().int().positive('Число сотрудников — больше нуля'),
    company_phone: z.string().regex(PHONE_PATTERN, 'Телефон в формате +7 и 10 цифр'),
    company_email: z.string().regex(EMAIL_PATTERN, 'Некорректный e-mail'),
  }),
  supervisor: z.object({
    full_name: required('ФИО руководителя'),
    passport: required('паспорт руководителя'),
    passport_issued_by: required('кем и когда выдан паспорт'),
    place_of_birth: required('дата и место рождения'),
    citizenship: z.string(),
    registration_address: required('адрес регистрации'),
    inn_fiz_face: z.string().regex(PERSON_INN_PATTERN, 'ИНН физического лица — 12 цифр'),
    supervisor_phone: z.string().regex(PHONE_PATTERN, 'Телефон в формате +7 и 10 цифр'),
    supervisor_email: z.string().regex(EMAIL_PATTERN, 'Некорректный e-mail'),
    owners_full_name: z.array(z.string().min(1)).nullable(),
    owners_passport: z.array(z.string().min(1)).nullable(),
  }),
  finance: z.object({
    revenue: z.number().nonnegative('Выручка не может быть отрицательной'),
    profit: z.number(),
    current_loans_and_leasing: z.array(z.string().min(1)).nullable(),
    has_debts: z.boolean(),
  }),
  documents: z.object({
    supervisor_passport_scan: z.string(),
    business_type: z.enum(['ip', 'ooo']),
    business_doc: z.array(z.string()),
  }),
  consents: z.object({
    personal_data_agreement: z
      .boolean()
      .refine((value) => value, 'Нужно согласие на обработку персональных данных'),
    credit_history_agreement: z
      .boolean()
      .refine((value) => value, 'Нужно согласие на запрос кредитной истории'),
  }),
})
export type ClientDataWire = z.infer<typeof clientDataWireSchema>

export const CONSENT_PD_TEXT =
  'Даю согласие АО «Альфа-Банк» на обработку моих персональных данных (ФИО, паспортные данные, ' +
  'контакты, сведения о бизнесе) в целях рассмотрения заявки на кредит в соответствии с ' +
  'Федеральным законом № 152-ФЗ «О персональных данных».'

export const CONSENT_CREDIT_TEXT =
  'Даю согласие АО «Альфа-Банк» на запрос и получение информации обо мне из бюро кредитных ' +
  'историй в соответствии с Федеральным законом № 218-ФЗ «О кредитных историях».'
