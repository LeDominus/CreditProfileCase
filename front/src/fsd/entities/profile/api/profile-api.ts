import { HTTPError } from 'ky'

import { api } from '@/fsd/shared/api/http'

import {
  type BusinessProfile,
  businessProfileSchema,
  type ProfileCreatePayload,
  type ProfilePatchPayload,
} from '../model/schemas'

/**
 * GET /api/me/profile — the user's latest profile. 404 means "no profiles
 * yet" (one is created by the first chat message) — mapped to null.
 */
export async function fetchMyProfile(): Promise<BusinessProfile | null> {
  try {
    const data = await api.get('me/profile').json()
    return businessProfileSchema.parse(data)
  } catch (error) {
    if (error instanceof HTTPError && error.response.status === 404) return null
    throw error
  }
}

/** POST /api/profile — manual creation (industry + funding_purpose required). */
export async function createProfile(payload: ProfileCreatePayload): Promise<BusinessProfile> {
  const data = await api.post('profile', { json: payload }).json()
  return businessProfileSchema.parse(data)
}

/** PATCH /api/profile/{id} — partial update; empty object is a no-op. */
export async function updateProfile(
  profileId: number,
  payload: ProfilePatchPayload,
): Promise<BusinessProfile> {
  const data = await api.patch(`profile/${profileId}`, { json: payload }).json()
  return businessProfileSchema.parse(data)
}
