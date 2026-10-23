import { z } from 'zod'
import { recommendationSchema } from '@/fsd/entities/product/model/schemas'
import { businessProfileSchema, profileUpdatesSchema } from '@/fsd/entities/profile/model/schemas'

/**
 * API contract for conversations (backend: src/schemas/conversation_schema.py,
 * FRONTEND_GUIDE §4.7–4.8). snake_case → camelCase at the boundary.
 */

const messageApiSchema = z.object({
  id: z.number(),
  conversation_id: z.number().optional(),
  role: z.enum(['user', 'assistant']),
  content: z.string(),
  created_at: z.string(),
})

export const messageSchema = messageApiSchema.transform((raw) => ({
  id: raw.id,
  conversationId: raw.conversation_id,
  role: raw.role,
  content: raw.content,
  createdAt: raw.created_at,
}))
export type Message = z.infer<typeof messageSchema>

const conversationApiSchema = z.object({
  id: z.number(),
  state: z.string(),
  created_at: z.string(),
  updated_at: z.string(),
})

export const conversationSchema = conversationApiSchema.transform((raw) => ({
  id: raw.id,
  state: raw.state,
  createdAt: raw.created_at,
  updatedAt: raw.updated_at,
}))
export type Conversation = z.infer<typeof conversationSchema>

/** GET /api/conversations */
export const conversationListResponseSchema = z.object({
  status: z.string(),
  conversations: z.array(conversationSchema),
})

/** POST /api/conversations → 201 */
export const conversationCreatedResponseSchema = z.object({
  status: z.string(),
  id: z.number(),
})

/** GET /api/conversations/{id}/messages */
export const messageListResponseSchema = z.object({
  status: z.string(),
  conversation_id: z.number(),
  messages: z.array(messageSchema),
})

/**
 * POST /api/conversations/{id}/messages → 201 ContractExtraction (§4.7).
 * `recommendations` stays EMPTY until the profile has all five gating fields;
 * `profile` is null when no profile_id was passed and none was created.
 */
export const contractExtractionSchema = z
  .object({
    status: z.string(),
    id: z.number(),
    assistant_message_id: z.number(),
    conversation_id: z.number(),
    reply: z.string(),
    profile_updates: profileUpdatesSchema.nullable(),
    profile: businessProfileSchema.nullable(),
    recommendations: z.array(recommendationSchema),
  })
  .transform((raw) => ({
    status: raw.status,
    id: raw.id,
    assistantMessageId: raw.assistant_message_id,
    conversationId: raw.conversation_id,
    reply: raw.reply,
    profileUpdates: raw.profile_updates,
    profile: raw.profile,
    recommendations: raw.recommendations,
  }))
export type ContractExtraction = z.infer<typeof contractExtractionSchema>
