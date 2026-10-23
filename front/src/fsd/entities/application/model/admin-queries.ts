'use client'

import { useQuery } from '@tanstack/react-query'

import { queryKeys } from '@/fsd/shared/api/query-keys'

import { fetchAdminApplications } from '../api/application-api'

/**
 * GET /api/admin/applications — bank queue with polling (15 s, like the
 * Streamlit fragment): new client applications surface without a reload.
 */
export function useAdminQueue(status: string | null) {
  return useQuery({
    queryKey: queryKeys.adminQueue(status),
    queryFn: () => fetchAdminApplications(status),
    refetchInterval: 15_000,
  })
}
