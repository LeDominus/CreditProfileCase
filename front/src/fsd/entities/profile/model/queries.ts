'use client'

import { useQuery } from '@tanstack/react-query'

import { queryKeys } from '@/fsd/shared/api/query-keys'

import { fetchMyProfile } from '../api/profile-api'

/** GET /api/me/profile — null when the user has no profiles yet (404). */
export function useMyProfile() {
  return useQuery({ queryKey: queryKeys.myProfile, queryFn: fetchMyProfile })
}
