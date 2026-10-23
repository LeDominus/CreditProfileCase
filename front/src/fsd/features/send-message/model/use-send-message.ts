'use client'

import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { createConversation, sendMessage } from '@/fsd/entities/conversation/api/conversation-api'
import { useChatStore } from '@/fsd/entities/conversation/model/chat-store'
import type { ContractExtraction, Message } from '@/fsd/entities/conversation/model/schemas'
import { useRecommendationsStore } from '@/fsd/entities/product/model/recommendations-store'
import type { BusinessProfile } from '@/fsd/entities/profile/model/schemas'
import { queryKeys } from '@/fsd/shared/api/query-keys'

/**
 * Send a chat message to the assistant.
 *
 * Call order (FRONTEND_GUIDE §7): if there is no active dialog yet, the
 * conversation is created first (POST /api/conversations), then the message
 * goes into it (POST /api/conversations/{id}/messages). The user bubble is
 * optimistic (pendingUserMessage in the chat store); the LLM reply, profile
 * updates and recommendations are applied on success.
 */
export function useSendMessage() {
  const queryClient = useQueryClient()
  const setRecommendations = useRecommendationsStore((s) => s.setRecommendations)

  return useMutation({
    mutationFn: async ({ content }: { content: string }) => {
      const { activeConversationId, setActiveConversation } = useChatStore.getState()
      let conversationId = activeConversationId
      if (conversationId == null) {
        conversationId = await createConversation()
        setActiveConversation(conversationId)
        queryClient.setQueryData<Message[]>(queryKeys.messages(conversationId), [])
        useChatStore.getState().setPending(content, conversationId)
      }
      const profile = queryClient.getQueryData<BusinessProfile | null>(queryKeys.myProfile)
      const result = await sendMessage(conversationId, content, profile?.id)
      return { result, content, conversationId }
    },
    onMutate: ({ content }) => {
      const { activeConversationId, setPending } = useChatStore.getState()
      setPending(content, activeConversationId)
    },
    onSuccess: ({ result, content, conversationId }) => {
      applyExtractionToMessages(queryClient, conversationId, result, content)
      applyExtractionToProfile(queryClient, result)
      // The array is empty until the profile is complete; keep the previous
      // non-empty selection rather than wiping the panel.
      if (result.recommendations.length > 0) setRecommendations(result.recommendations)
      queryClient.invalidateQueries({ queryKey: queryKeys.conversations })
      queryClient.invalidateQueries({ queryKey: queryKeys.messages(conversationId) })
    },
    onError: (error) => {
      // The dialog may have been created before the failure — refresh the list.
      queryClient.invalidateQueries({ queryKey: queryKeys.conversations })
      toast.error(error instanceof Error ? error.message : 'Не удалось отправить сообщение')
    },
    onSettled: () => {
      useChatStore.getState().clearPending()
    },
  })
}

type QueryClientLike = ReturnType<typeof useQueryClient>

/** Append the confirmed user message and the assistant reply to the cache. */
function applyExtractionToMessages(
  queryClient: QueryClientLike,
  conversationId: number,
  result: ContractExtraction,
  content: string,
) {
  const now = new Date().toISOString()
  const confirmed: Message[] = [
    { id: result.id, conversationId, role: 'user', content, createdAt: now },
    {
      id: result.assistantMessageId,
      conversationId,
      role: 'assistant',
      content: result.reply,
      createdAt: now,
    },
  ]
  queryClient.setQueryData<Message[]>(queryKeys.messages(conversationId), (old) => [
    ...(old ?? []),
    ...confirmed,
  ])
}

/** Apply `profile` (preferred) or `profile_updates` to the profile cache. */
function applyExtractionToProfile(queryClient: QueryClientLike, result: ContractExtraction) {
  if (result.profile) {
    queryClient.setQueryData<BusinessProfile | null>(queryKeys.myProfile, result.profile)
    return
  }
  const updates = result.profileUpdates
  if (!updates) return
  const defined = Object.fromEntries(Object.entries(updates).filter(([, v]) => v !== undefined))
  if (Object.keys(defined).length === 0) return
  queryClient.setQueryData<BusinessProfile | null>(queryKeys.myProfile, (old) =>
    old ? { ...old, ...defined } : old,
  )
  queryClient.invalidateQueries({ queryKey: queryKeys.myProfile })
}
