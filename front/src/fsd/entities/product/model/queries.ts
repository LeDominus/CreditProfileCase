'use client'

import { useQuery } from '@tanstack/react-query'

import { queryKeys } from '@/fsd/shared/api/query-keys'

import { fetchProducts } from '../api/product-api'

/** GET /api/products — full catalog (comparison modal). */
export function useProducts() {
  return useQuery({ queryKey: queryKeys.products, queryFn: fetchProducts, staleTime: 300_000 })
}
