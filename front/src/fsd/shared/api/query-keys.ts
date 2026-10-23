/** Shared react-query keys. */
export const queryKeys = {
  conversations: ['conversations'] as const,
  messages: (conversationId: number) => ['messages', conversationId] as const,
  myProfile: ['profile', 'me'] as const,
  myApplications: ['applications', 'me'] as const,
  products: ['products'] as const,
  payment: (profileId: number, amount: number, term: number) =>
    ['payment', profileId, amount, term] as const,
  adminQueue: (status: string | null) => ['admin', 'applications', status ?? 'all'] as const,
  adminQueuesAll: ['admin', 'applications'] as const,
}
