'use client'

import { useQuery } from '@tanstack/react-query'

import { queryKeys } from '@/fsd/shared/api/query-keys'

import { fetchConversations, fetchMessages } from '../api/conversation-api'

/** GET /api/conversations — user's dialogs, newest first. */
export function useConversations() {
  return useQuery({ queryKey: queryKeys.conversations, queryFn: fetchConversations })
}

/** GET /api/conversations/{id}/messages — enabled only with an active dialog. */
export function useMessages(conversationId: number | null) {
  return useQuery({
    queryKey: queryKeys.messages(conversationId ?? -1),
    queryFn: () => fetchMessages(conversationId as number),
    enabled: conversationId != null,
  })
}
