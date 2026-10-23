import { api } from '@/fsd/shared/api/http'

import {
  type ContractExtraction,
  type Conversation,
  contractExtractionSchema,
  conversationCreatedResponseSchema,
  conversationListResponseSchema,
  type Message,
  messageListResponseSchema,
} from '../model/schemas'

/** GET /api/conversations — user's dialogs, newest first. */
export async function fetchConversations(): Promise<Conversation[]> {
  const data = await api.get('conversations').json()
  return conversationListResponseSchema.parse(data).conversations
}

/** POST /api/conversations {state:"new"} → new dialog id. */
export async function createConversation(): Promise<number> {
  const data = await api.post('conversations', { json: { state: 'new' } }).json()
  return conversationCreatedResponseSchema.parse(data).id
}

/** GET /api/conversations/{id}/messages — chronological history. */
export async function fetchMessages(conversationId: number): Promise<Message[]> {
  const data = await api.get(`conversations/${conversationId}/messages`).json()
  return messageListResponseSchema.parse(data).messages
}

/**
 * POST /api/conversations/{id}/messages — the main chat endpoint.
 * SLOW (LLM, tens of seconds): the shared ky timeout is 120 s; callers must
 * show a typing indicator and block resubmission.
 */
export async function sendMessage(
  conversationId: number,
  content: string,
  profileId?: number | null,
): Promise<ContractExtraction> {
  const json: { role: 'user'; content: string; profile_id?: number } = {
    role: 'user',
    content,
  }
  if (profileId != null) json.profile_id = profileId
  const data = await api.post(`conversations/${conversationId}/messages`, { json }).json()
  return contractExtractionSchema.parse(data)
}
