import type { UserRole } from './schemas'

export const ROLE_LABELS: Record<UserRole, string> = {
  client: 'Клиент / предприниматель',
  bank_manager: 'Менеджер банка',
  bank_analyst: 'Аналитик банка',
}
