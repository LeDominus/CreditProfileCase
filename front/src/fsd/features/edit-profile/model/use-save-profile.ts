'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { createProfile, updateProfile } from '@/fsd/entities/profile/api/profile-api'
import type {
  BusinessProfile,
  ProfileCreatePayload,
  ProfilePatchPayload,
} from '@/fsd/entities/profile/model/schemas'
import { queryKeys } from '@/fsd/shared/api/query-keys'

function saveErrorMessage(error: unknown): string {
  return error instanceof Error ? error.message : 'Не удалось сохранить профиль'
}

/** PATCH /api/profile/{id} — partial update of the business profile. */
export function useUpdateProfile(profileId: number) {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: ProfilePatchPayload) => updateProfile(profileId, payload),
    onSuccess: (profile) => {
      queryClient.setQueryData<BusinessProfile | null>(queryKeys.myProfile, profile)
      queryClient.invalidateQueries({ queryKey: queryKeys.myProfile })
      toast.success('Профиль сохранён')
    },
    onError: (error) => toast.error(saveErrorMessage(error)),
  })
}

/** POST /api/profile — manual creation (industry + funding_purpose required). */
export function useCreateProfile() {
  const queryClient = useQueryClient()

  return useMutation({
    mutationFn: (payload: ProfileCreatePayload) => createProfile(payload),
    onSuccess: (profile) => {
      queryClient.setQueryData<BusinessProfile | null>(queryKeys.myProfile, profile)
      queryClient.invalidateQueries({ queryKey: queryKeys.myProfile })
      toast.success('Профиль создан')
    },
    onError: (error) => toast.error(saveErrorMessage(error)),
  })
}
