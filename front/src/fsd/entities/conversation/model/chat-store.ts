import { create } from 'zustand'

/**
 * Chat UI state (in-memory only). The active conversation id survives tab
 * switches in the right panel; a page reload re-derives it from the
 * conversations query (newest first). `pendingUserMessage` drives the
 * optimistic bubble + typing indicator until the LLM reply arrives.
 */
interface ChatState {
  activeConversationId: number | null
  /** Optimistic bubble + typing indicator while a send is in flight. */
  pendingUserMessage: string | null
  pendingConversationId: number | null
  setActiveConversation: (id: number | null) => void
  setPending: (content: string, conversationId: number | null) => void
  clearPending: () => void
}

export const useChatStore = create<ChatState>()((set) => ({
  activeConversationId: null,
  pendingUserMessage: null,
  pendingConversationId: null,
  setActiveConversation: (id) => set({ activeConversationId: id }),
  setPending: (content, conversationId) =>
    set({ pendingUserMessage: content, pendingConversationId: conversationId }),
  clearPending: () => set({ pendingUserMessage: null, pendingConversationId: null }),
}))
