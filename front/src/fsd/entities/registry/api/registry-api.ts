import { HTTPError } from 'ky'

import { api } from '@/fsd/shared/api/http'

import { type RegistryEntry, registryEntrySchema } from '../model/schemas'

/** GET /api/registry/{inn} — public mock registry; 404 → null (unknown INN). */
export async function fetchRegistryEntry(inn: string): Promise<RegistryEntry | null> {
  try {
    const data = await api.get(`registry/${inn}`).json()
    return registryEntrySchema.parse(data)
  } catch (error) {
    if (error instanceof HTTPError && error.response.status === 404) return null
    throw error
  }
}
