'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'

import { createConversation } from '@/fsd/entities/conversation/api/conversation-api'
import { useChatStore } from '@/fsd/entities/conversation/model/chat-store'
import type { Message } from '@/fsd/entities/conversation/model/schemas'
import { queryKeys } from '@/fsd/shared/api/query-keys'

/** «Новая заявка»: create an empty dialog and make it active. */
export function useCreateConversation() {
  const queryClient = useQueryClient()
  const setActiveConversation = useChatStore((s) => s.setActiveConversation)

  return useMutation({
    mutationFn: () => createConversation(),
    onSuccess: (conversationId) => {
      queryClient.setQueryData<Message[]>(queryKeys.messages(conversationId), [])
      setActiveConversation(conversationId)
      queryClient.invalidateQueries({ queryKey: queryKeys.conversations })
    },
    onError: (error) => {
      toast.error(error instanceof Error ? error.message : 'Не удалось создать диалог')
    },
  })
}
