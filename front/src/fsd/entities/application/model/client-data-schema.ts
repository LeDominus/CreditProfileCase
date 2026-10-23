import { z } from 'zod'

/**
 * client_data (ClientDataRequest) attached to an application — read-only
 * display in the bank АРМ. Loose sections (registry-sourced fields vary by
 * business type), normalized to camelCase at the boundary.
 */

const creditApiSchema = z.looseObject({
  credit_product: z.string(),
  credit_sum: z.number(),
  credit_term_months: z.number(),
  credit_target: z.string(),
})

const companyApiSchema = z.looseObject({
  inn: z.string(),
  company_name: z.string(),
  ogrn: z.string().nullish(),
  registered_address: z.string().nullish(),
  registration_date: z.string().nullish(),
  type_of_activity: z.string().nullish(),
  company_supervisor: z.string().nullish(),
  company_members: z.array(z.string()).nullish(),
  company_place: z.string().nullish(),
  taxation_system: z.string().nullish(),
  company_members_count: z.number().nullish(),
  company_phone: z.string().nullish(),
  company_email: z.string().nullish(),
})

const supervisorApiSchema = z.looseObject({
  full_name: z.string(),
  passport: z.string().nullish(),
  passport_issued_by: z.string().nullish(),
  place_of_birth: z.string().nullish(),
  citizenship: z.string().nullish(),
  registration_address: z.string().nullish(),
  inn_fiz_face: z.string().nullish(),
  supervisor_phone: z.string().nullish(),
  supervisor_email: z.string().nullish(),
  owners_full_name: z.array(z.string()).nullish(),
  owners_passport: z.array(z.string()).nullish(),
})

const financeApiSchema = z.looseObject({
  revenue: z.number().nullish(),
  profit: z.number().nullish(),
  current_loans_and_leasing: z.array(z.string()).nullish(),
  has_debts: z.boolean().nullish(),
})

const documentsApiSchema = z.looseObject({
  supervisor_passport_scan: z.string().nullish(),
  business_type: z.string().nullish(),
  business_doc: z.array(z.string()).nullish(),
})

const consentsApiSchema = z.looseObject({
  personal_data_agreement: z.boolean(),
  credit_history_agreement: z.boolean(),
})

export const clientDataSchema = z
  .looseObject({
    credit: creditApiSchema,
    company: companyApiSchema,
    supervisor: supervisorApiSchema,
    finance: financeApiSchema,
    documents: documentsApiSchema,
    consents: consentsApiSchema,
  })
  .transform((raw) => ({
    credit: {
      creditProduct: raw.credit.credit_product,
      creditSum: raw.credit.credit_sum,
      creditTermMonths: raw.credit.credit_term_months,
      creditTarget: raw.credit.credit_target,
    },
    company: {
      inn: raw.company.inn,
      companyName: raw.company.company_name,
      ogrn: raw.company.ogrn ?? null,
      registeredAddress: raw.company.registered_address ?? null,
      registrationDate: raw.company.registration_date ?? null,
      typeOfActivity: raw.company.type_of_activity ?? null,
      companySupervisor: raw.company.company_supervisor ?? null,
      companyMembers: raw.company.company_members ?? null,
      companyPlace: raw.company.company_place ?? null,
      taxationSystem: raw.company.taxation_system ?? null,
      companyMembersCount: raw.company.company_members_count ?? null,
      companyPhone: raw.company.company_phone ?? null,
      companyEmail: raw.company.company_email ?? null,
    },
    supervisor: {
      fullName: raw.supervisor.full_name,
      passport: raw.supervisor.passport ?? null,
      passportIssuedBy: raw.supervisor.passport_issued_by ?? null,
      placeOfBirth: raw.supervisor.place_of_birth ?? null,
      citizenship: raw.supervisor.citizenship ?? null,
      registrationAddress: raw.supervisor.registration_address ?? null,
      innFizFace: raw.supervisor.inn_fiz_face ?? null,
      supervisorPhone: raw.supervisor.supervisor_phone ?? null,
      supervisorEmail: raw.supervisor.supervisor_email ?? null,
      ownersFullName: raw.supervisor.owners_full_name ?? null,
      ownersPassport: raw.supervisor.owners_passport ?? null,
    },
    finance: {
      revenue: raw.finance.revenue ?? null,
      profit: raw.finance.profit ?? null,
      currentLoansAndLeasing: raw.finance.current_loans_and_leasing ?? null,
      hasDebts: raw.finance.has_debts ?? null,
    },
    documents: {
      supervisorPassportScan: raw.documents.supervisor_passport_scan ?? null,
      businessType: raw.documents.business_type ?? null,
      businessDoc: raw.documents.business_doc ?? null,
    },
    consents: {
      personalDataAgreement: raw.consents.personal_data_agreement,
      creditHistoryAgreement: raw.consents.credit_history_agreement,
    },
  }))
export type ClientData = z.infer<typeof clientDataSchema>
