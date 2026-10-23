import { z } from 'zod'

/**
 * Mock registry entry (GET /api/registry/{inn}, FRONTEND_GUIDE §4.10,
 * backend src/config/registry.py). Fills the application form's company,
 * supervisor and finance sections. snake_case → camelCase at the boundary.
 */

const registryCompanyApiSchema = z.object({
  company_name: z.string(),
  ogrn: z.string(),
  registered_address: z.string(),
  registration_date: z.string(),
  type_of_activity: z.string(),
  company_supervisor: z.string(),
  company_members: z.array(z.string()),
  company_place: z.string(),
  taxation_system: z.string(),
  company_members_count: z.number(),
  company_phone: z.string(),
  company_email: z.string(),
})

const registrySupervisorApiSchema = z.object({
  full_name: z.string(),
  passport: z.string(),
  passport_issued_by: z.string(),
  place_of_birth: z.string(),
  citizenship: z.string(),
  registration_address: z.string(),
  inn_fiz_face: z.string(),
  supervisor_phone: z.string(),
  supervisor_email: z.string(),
  owners_full_name: z.array(z.string()).nullable().optional(),
  owners_passport: z.array(z.string()).nullable().optional(),
})

const registryFinanceApiSchema = z.object({
  revenue: z.number(),
  profit: z.number(),
  current_loans_and_leasing: z.array(z.string()).nullable().optional(),
  has_debts: z.boolean(),
})

export const registryEntrySchema = z
  .object({
    status: z.string(),
    inn: z.string(),
    company: registryCompanyApiSchema,
    supervisor: registrySupervisorApiSchema,
    finance: registryFinanceApiSchema,
  })
  .transform((raw) => ({
    inn: raw.inn,
    company: {
      companyName: raw.company.company_name,
      ogrn: raw.company.ogrn,
      registeredAddress: raw.company.registered_address,
      registrationDate: raw.company.registration_date,
      typeOfActivity: raw.company.type_of_activity,
      companySupervisor: raw.company.company_supervisor,
      companyMembers: raw.company.company_members,
      companyPlace: raw.company.company_place,
      taxationSystem: raw.company.taxation_system,
      companyMembersCount: raw.company.company_members_count,
      companyPhone: raw.company.company_phone,
      companyEmail: raw.company.company_email,
    },
    supervisor: {
      fullName: raw.supervisor.full_name,
      passport: raw.supervisor.passport,
      passportIssuedBy: raw.supervisor.passport_issued_by,
      placeOfBirth: raw.supervisor.place_of_birth,
      citizenship: raw.supervisor.citizenship,
      registrationAddress: raw.supervisor.registration_address,
      innFizFace: raw.supervisor.inn_fiz_face,
      supervisorPhone: raw.supervisor.supervisor_phone,
      supervisorEmail: raw.supervisor.supervisor_email,
      ownersFullName: raw.supervisor.owners_full_name ?? null,
      ownersPassport: raw.supervisor.owners_passport ?? null,
    },
    finance: {
      revenue: raw.finance.revenue,
      profit: raw.finance.profit,
      currentLoansAndLeasing: raw.finance.current_loans_and_leasing ?? null,
      hasDebts: raw.finance.has_debts,
    },
  }))
export type RegistryEntry = z.infer<typeof registryEntrySchema>
