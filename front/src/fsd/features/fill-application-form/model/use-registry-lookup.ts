'use client'

import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'

import { fetchRegistryEntry } from '@/fsd/entities/registry/api/registry-api'
import type { RegistryEntry } from '@/fsd/entities/registry/model/schemas'

const INN_PATTERN = /^\d{10}(\d{2})?$/

/**
 * «Заполнить по ИНН»: GET /api/registry/{inn}. 404 → null entry; the caller
 * shows "не найдена в реестре, заполните вручную" (manual fill is allowed).
 */
export function useRegistryLookup() {
  const [notFound, setNotFound] = useState(false)

  const mutation = useMutation({
    mutationFn: async (inn: string): Promise<RegistryEntry | null> => {
      setNotFound(false)
      return fetchRegistryEntry(inn.trim())
    },
    onSuccess: (entry) => {
      setNotFound(entry === null)
    },
  })

  return { ...mutation, notFound, isValidInn: (inn: string) => INN_PATTERN.test(inn.trim()) }
}
