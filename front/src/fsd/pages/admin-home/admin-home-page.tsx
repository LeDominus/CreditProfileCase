import { AdminApplicationDetails } from '@/fsd/widgets/admin-application-details/admin-application-details'
import { AdminQueue } from '@/fsd/widgets/admin-queue/admin-queue'

/**
 * АРМ (bank workspace): application queue on the left, selected application
 * details on the right — a separate interface from the client cabinet.
 */
export function AdminHomePage() {
  return (
    <div className="flex h-[calc(100dvh-8rem)] gap-5">
      <AdminQueue />
      <AdminApplicationDetails />
    </div>
  )
}
