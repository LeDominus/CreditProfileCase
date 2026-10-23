'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { HTTPError } from 'ky'
import { toast } from 'sonner'

import {
  type ApplicationPatchPayload,
  createApplication,
  explainApplication,
  rescoreApplication,
  respondToOffer,
  signApplication,
  submitApplication,
  updateApplication,
} from '@/fsd/entities/application/api/application-api'
import type { AlternativeProduct } from '@/fsd/entities/application/model/decision-details-schema'
import { queryKeys } from '@/fsd/shared/api/query-keys'

function errorMessage(error: unknown, fallback: string): string {
  if (error instanceof HTTPError && error.response.status === 409) {
    return error.message || 'Действие недоступно для текущего статуса заявки'
  }
  return error instanceof Error ? error.message : fallback
}

function useInvalidateApplications() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: queryKeys.myApplications })
}

/** draft → submit (pipeline). */
export function useSubmitDraft(applicationId: number) {
  const invalidate = useInvalidateApplications()
  return useMutation({
    mutationFn: () => submitApplication(applicationId),
    onSuccess: () => {
      invalidate()
      toast.success('Заявка отправлена на обработку')
    },
    onError: (error) => toast.error(errorMessage(error, 'Не удалось отправить заявку')),
  })
}

/** draft: PATCH requested_amount / term_months. */
export function useUpdateDraft(applicationId: number) {
  const invalidate = useInvalidateApplications()
  return useMutation({
    mutationFn: (payload: ApplicationPatchPayload) => updateApplication(applicationId, payload),
    onSuccess: () => {
      invalidate()
      toast.success('Изменения сохранены')
    },
    onError: (error) => toast.error(errorMessage(error, 'Не удалось сохранить изменения')),
  })
}

/** needs_info → POST /scoring (reprocess after profile completion). */
export function useRescore(applicationId: number) {
  const invalidate = useInvalidateApplications()
  return useMutation({
    mutationFn: () => rescoreApplication(applicationId),
    onSuccess: () => {
      invalidate()
      toast.success('Заявка отправлена на повторную обработку')
    },
    onError: (error) => toast.error(errorMessage(error, 'Не удалось обработать заявку повторно')),
  })
}

/** offer_ready → accept / decline (decline carries a required reason). */
export function useOfferResponse(applicationId: number) {
  const invalidate = useInvalidateApplications()
  return useMutation({
    mutationFn: ({ accept, declineReason }: { accept: boolean; declineReason?: string }) =>
      respondToOffer(applicationId, accept, declineReason),
    onSuccess: (_data, { accept }) => {
      invalidate()
      toast.success(accept ? 'Условия приняты' : 'Предложение отклонено')
    },
    onError: (error) => toast.error(errorMessage(error, 'Не удалось отправить отклик')),
  })
}

/** accepted → sign (ЭП моделируется кнопкой; issued follows automatically). */
export function useSign(applicationId: number) {
  const invalidate = useInvalidateApplications()
  return useMutation({
    mutationFn: () => signApplication(applicationId),
    onSuccess: () => {
      invalidate()
      toast.success('Договор подписан. Выдача смоделирована')
    },
    onError: (error) => toast.error(errorMessage(error, 'Не удалось подписать договор')),
  })
}

/** rejected → create a new draft on an alternative product. */
export function useCreateAlternative(profileId: number | null) {
  const invalidate = useInvalidateApplications()
  return useMutation({
    mutationFn: (alternative: AlternativeProduct) => {
      if (profileId == null) throw new Error('Профиль не найден')
      return createApplication({
        profile_id: profileId,
        product_id: alternative.id,
        requested_amount: alternative.amount,
        term_months: alternative.termMonths,
      })
    },
    onSuccess: () => {
      invalidate()
      toast.success('Черновик заявки на альтернативный продукт создан')
    },
    onError: (error) => toast.error(errorMessage(error, 'Не удалось создать заявку')),
  })
}

/**
 * «Объяснить решение (ИИ)» — SLOW LLM endpoint: the button shows a spinner
 * and stays locked while pending. 409 → no decision yet (button should not
 * be rendered then, the toast is a safety net).
 */
export function useExplain(applicationId: number) {
  return useMutation({
    mutationFn: () => explainApplication(applicationId, 'client'),
    onError: (error) => {
      if (error instanceof HTTPError && error.response.status === 409) {
        toast.info('Решение по заявке ещё не принято')
        return
      }
      toast.error(errorMessage(error, 'ИИ-объяснение недоступно'))
    },
  })
}
