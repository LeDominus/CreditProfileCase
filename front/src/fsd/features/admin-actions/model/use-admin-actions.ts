'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { HTTPError } from 'ky'
import { toast } from 'sonner'

import {
  type AnalystDecisionValue,
  adminAssignAnalyst,
  adminDecision,
  adminRequestInfo,
  explainApplication,
} from '@/fsd/entities/application/api/application-api'
import { queryKeys } from '@/fsd/shared/api/query-keys'

function adminErrorMessage(error: unknown, fallback: string): string {
  if (error instanceof HTTPError) {
    if (error.response.status === 403) {
      return `Недостаточно прав: действие доступно другой роли (${error.message})`
    }
    if (error.response.status === 409) {
      return error.message || 'Действие недоступно для текущего статуса заявки'
    }
  }
  return error instanceof Error ? error.message : fallback
}

function useInvalidateQueue() {
  const queryClient = useQueryClient()
  return () => queryClient.invalidateQueries({ queryKey: queryKeys.adminQueuesAll })
}

/** bank_manager: request clarifications from the client (→ needs_info). */
export function useRequestInfo(applicationId: number) {
  const invalidate = useInvalidateQueue()
  return useMutation({
    mutationFn: (message: string) => adminRequestInfo(applicationId, message),
    onSuccess: () => {
      invalidate()
      toast.success('Запрос отправлен — заявка ожидает уточнений от клиента')
    },
    onError: (error) => toast.error(adminErrorMessage(error, 'Не удалось отправить запрос')),
  })
}

/** bank_manager: hand the application to the analyst (→ manual_review). */
export function useAssignAnalyst(applicationId: number) {
  const invalidate = useInvalidateQueue()
  return useMutation({
    mutationFn: () => adminAssignAnalyst(applicationId),
    onSuccess: () => {
      invalidate()
      toast.success('Заявка передана кредитному аналитику')
    },
    onError: (error) => toast.error(adminErrorMessage(error, 'Не удалось передать заявку')),
  })
}

/** bank_analyst: decision with a mandatory reason (manual_review → …). */
export function useDecision(applicationId: number) {
  const invalidate = useInvalidateQueue()
  return useMutation({
    mutationFn: ({ decision, reason }: { decision: AnalystDecisionValue; reason: string }) =>
      adminDecision(applicationId, decision, reason),
    onSuccess: () => {
      invalidate()
      toast.success('Решение зафиксировано')
    },
    onError: (error) => toast.error(adminErrorMessage(error, 'Не удалось зафиксировать решение')),
  })
}

/** «Объяснить решение (ИИ)» for the bank — audience=analyst. SLOW endpoint. */
export function useExplainAnalyst(applicationId: number) {
  return useMutation({
    mutationFn: () => explainApplication(applicationId, 'analyst'),
    onError: (error) => {
      if (error instanceof HTTPError) {
        if (error.response.status === 409) {
          toast.info('Решение по заявке ещё не принято')
          return
        }
        // Backend quirk: /explain is owner-only, so bank roles get 404 on
        // client applications (verified against live backend).
        if (error.response.status === 404) {
          toast.info('ИИ-объяснение доступно только владельцу заявки (ограничение бэкенда)')
          return
        }
      }
      toast.error(adminErrorMessage(error, 'ИИ-объяснение недоступно'))
    },
  })
}
