'use client'

import { useQuery } from '@tanstack/react-query'

import { queryKeys } from '@/fsd/shared/api/query-keys'

import { fetchApplicationHistory, fetchMyApplications } from '../api/application-api'

/**
 * GET /api/me/applications with polling: bank decisions (manual review,
 * offers) must surface without any client action (PRD §5.2).
 */
export function useMyApplications() {
  return useQuery({
    queryKey: queryKeys.myApplications,
    queryFn: fetchMyApplications,
    refetchInterval: 12_000,
  })
}

/** GET /api/applications/{id}/history — lazy, only when the block is open. */
export function useApplicationHistory(applicationId: number, enabled: boolean) {
  return useQuery({
    queryKey: ['applications', applicationId, 'history'],
    queryFn: () => fetchApplicationHistory(applicationId),
    enabled,
    staleTime: 30_000,
  })
}
