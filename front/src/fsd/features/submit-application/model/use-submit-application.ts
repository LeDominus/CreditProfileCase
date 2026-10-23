'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useState } from 'react'
import { toast } from 'sonner'

import {
  createApplication,
  submitApplication,
} from '@/fsd/entities/application/api/application-api'
import type {
  Application,
  ApplicationCreatePayload,
} from '@/fsd/entities/application/model/schemas'
import { queryKeys } from '@/fsd/shared/api/query-keys'

import { useApplicationDraft } from './draft-store'

export type SubmitStep = 'idle' | 'creating' | 'submitting'

export const SUBMIT_STEP_LABELS: Record<Exclude<SubmitStep, 'idle'>, string> = {
  creating: 'Создаём черновик…',
  submitting: 'Отправляем на проверку…',
}

export interface SubmitResult {
  application: Application
  /** false when the draft was created but submit failed (stays a draft). */
  submitted: boolean
}

/**
 * One-click application flow: POST /api/applications (draft) → immediately
 * POST /api/applications/{id}/submit (pipeline). A failed submit keeps the
 * draft — the user can resend it from the applications tab (stage 5).
 */
export function useSubmitApplication() {
  const queryClient = useQueryClient()
  const setAccepted = useApplicationDraft((s) => s.setAccepted)
  const setFormOpen = useApplicationDraft((s) => s.setFormOpen)
  const [step, setStep] = useState<SubmitStep>('idle')

  const mutation = useMutation({
    mutationFn: async (payload: ApplicationCreatePayload): Promise<SubmitResult> => {
      setStep('creating')
      const draft = await createApplication(payload)
      setStep('submitting')
      try {
        const result = await submitApplication(draft.id)
        return { application: result.application, submitted: true }
      } catch {
        return { application: draft, submitted: false }
      }
    },
    onSuccess: ({ application, submitted }) => {
      queryClient.invalidateQueries({ queryKey: queryKeys.myApplications })
      setFormOpen(false)
      setAccepted({ application, submitted })
      if (!submitted) {
        toast.info('Заявка сохранена как черновик — отправьте её из вкладки «Заявки»')
      }
    },
    onSettled: () => setStep('idle'),
  })

  return { mutation, step }
}
