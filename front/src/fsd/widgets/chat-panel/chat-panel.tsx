'use client'

import { motion } from 'framer-motion'
import { BotIcon, PaperclipIcon, SendHorizonalIcon } from 'lucide-react'
import { useEffect, useRef, useState } from 'react'

import { useChatStore } from '@/fsd/entities/conversation/model/chat-store'
import { useConversations, useMessages } from '@/fsd/entities/conversation/model/queries'
import type { Message } from '@/fsd/entities/conversation/model/schemas'
import { useSendMessage } from '@/fsd/features/send-message/model/use-send-message'
import { cn } from '@/fsd/shared/lib/utils'
import { Markdown } from '@/fsd/shared/ui/markdown'
import { Skeleton } from '@/fsd/shared/ui/skeleton'

const SUGGESTIONS = [
  'Нужен кредит 3 000 000 ₽ на 12 месяцев на закупку сырья',
  'Бизнесу 5 лет, выручка 2 млн ₽ в месяц, прибыль 300 тысяч',
  'Расскажите о кредитных продуктах для малого бизнеса',
]

function AssistantAvatar() {
  return (
    <span className="mt-1 inline-flex size-8 shrink-0 items-center justify-center rounded-full bg-accent/10 text-accent">
      <BotIcon className="size-4" />
    </span>
  )
}

function AssistantBubble({ content }: { content: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.25, ease: 'easeOut' }}
      className="flex items-start gap-2.5"
    >
      <AssistantAvatar />
      <div className="max-w-[85%] rounded-2xl rounded-tl-sm bg-bg-secondary px-4 py-3 text-sm">
        <Markdown content={content} />
      </div>
    </motion.div>
  )
}

function UserBubble({ content }: { content: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.2, ease: 'easeOut' }}
      className="flex justify-end"
    >
      <div className="max-w-[85%] rounded-2xl rounded-tr-sm bg-accent px-4 py-3 text-sm whitespace-pre-wrap text-white">
        {content}
      </div>
    </motion.div>
  )
}

function TypingIndicator() {
  return (
    <div className="flex items-start gap-2.5">
      <AssistantAvatar />
      <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm bg-bg-secondary px-4 py-3.5">
        {[0, 1, 2].map((i) => (
          <span
            key={i}
            className="size-1.5 animate-bounce rounded-full bg-text-secondary"
            style={{ animationDelay: `${i * 150}ms` }}
          />
        ))}
        <span className="ml-1.5 text-xs text-text-secondary">Ассистент печатает…</span>
      </div>
    </div>
  )
}

function MessagesSkeleton() {
  return (
    <div className="flex flex-col gap-4">
      <Skeleton className="h-16 w-2/3 rounded-2xl" />
      <Skeleton className="ml-auto h-10 w-1/2 rounded-2xl" />
      <Skeleton className="h-20 w-3/5 rounded-2xl" />
    </div>
  )
}

function WelcomeScreen({ onSuggestion }: { onSuggestion: (text: string) => void }) {
  return (
    <div className="flex h-full flex-col items-center justify-center gap-6 text-center">
      <span className="inline-flex size-16 items-center justify-center rounded-full bg-accent/10 text-accent">
        <BotIcon className="size-8" />
      </span>
      <div className="flex max-w-md flex-col gap-2">
        <h2 className="text-xl font-bold">Здравствуйте! Я — ИИ-ассистент Альфа-Банка</h2>
        <p className="text-sm text-text-secondary">
          Расскажите о вашем бизнесе и цели кредита — я соберу профиль и подберу подходящие
          продукты. Можно начать с примера:
        </p>
      </div>
      <div className="flex max-w-lg flex-col gap-2">
        {SUGGESTIONS.map((text) => (
          <button
            key={text}
            type="button"
            onClick={() => onSuggestion(text)}
            className="cursor-pointer rounded-xl border border-border bg-bg-primary px-4 py-2.5 text-left text-sm transition-colors hover:border-accent hover:bg-accent/5"
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  )
}

/**
 * Center column of the client cabinet: dialog with the LLM assistant.
 * Optimistic user bubble + typing indicator while the (slow) message
 * endpoint is in flight; the composer is locked until the reply arrives.
 */
export function ChatPanel() {
  const activeConversationId = useChatStore((s) => s.activeConversationId)
  const setActiveConversation = useChatStore((s) => s.setActiveConversation)
  const pendingUserMessage = useChatStore((s) => s.pendingUserMessage)
  const pendingConversationId = useChatStore((s) => s.pendingConversationId)

  const conversationsQuery = useConversations()
  // Session restore: with no explicit selection the newest dialog is active.
  useEffect(() => {
    if (activeConversationId == null && conversationsQuery.data?.length) {
      setActiveConversation(conversationsQuery.data[0].id)
    }
  }, [activeConversationId, conversationsQuery.data, setActiveConversation])

  const messagesQuery = useMessages(activeConversationId)
  const { mutate: send, isPending: isSending } = useSendMessage()

  const [value, setValue] = useState('')
  const textareaRef = useRef<HTMLTextAreaElement>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  // Auto-growing composer (capped), driven by the change event.
  const handleChange = (event: React.ChangeEvent<HTMLTextAreaElement>) => {
    setValue(event.target.value)
    const textarea = event.target
    textarea.style.height = 'auto'
    textarea.style.height = `${Math.min(textarea.scrollHeight, 160)}px`
  }

  const showPendingBubble =
    pendingUserMessage != null &&
    (pendingConversationId == null || pendingConversationId === activeConversationId)
  const messagesCount = messagesQuery.data?.length ?? 0

  // biome-ignore lint/correctness/useExhaustiveDependencies: re-scroll whenever the message list, typing state or active dialog changes
  useEffect(() => {
    const container = scrollRef.current
    if (container) container.scrollTop = container.scrollHeight
  }, [messagesCount, showPendingBubble, activeConversationId])

  const submit = (text: string) => {
    const content = text.trim()
    if (!content || isSending) return
    setValue('')
    if (textareaRef.current) textareaRef.current.style.height = 'auto'
    send(
      { content },
      {
        // Give the text back when the send fails, so it is not lost.
        onError: () => setValue(content),
      },
    )
  }

  const handleKeyDown = (event: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === 'Enter' && !event.shiftKey) {
      event.preventDefault()
      submit(value)
    }
  }

  const showWelcome =
    activeConversationId == null && pendingUserMessage == null && !conversationsQuery.isLoading

  return (
    <section className="flex min-w-0 flex-1 flex-col overflow-hidden rounded-xl border border-border bg-bg-primary shadow-card">
      <header className="flex items-center gap-3 border-b border-border px-5 py-3.5">
        <AssistantAvatar />
        <div className="flex flex-col">
          <span className="text-sm font-bold">ИИ-ассистент</span>
          <span className="text-xs text-text-secondary">
            Подбор кредитных продуктов для бизнеса
          </span>
        </div>
      </header>

      <div ref={scrollRef} className="flex-1 overflow-y-auto px-5 py-5">
        {showWelcome ? (
          <WelcomeScreen onSuggestion={submit} />
        ) : (
          <div className="flex flex-col gap-4">
            {activeConversationId != null && messagesQuery.isLoading && <MessagesSkeleton />}
            {messagesQuery.data?.map((message: Message) =>
              message.role === 'assistant' ? (
                <AssistantBubble key={message.id} content={message.content} />
              ) : (
                <UserBubble key={message.id} content={message.content} />
              ),
            )}
            {showPendingBubble && <UserBubble content={pendingUserMessage} />}
            {isSending && <TypingIndicator />}
          </div>
        )}
      </div>

      <footer className="border-t border-border px-4 py-3">
        <div className="flex items-end gap-2">
          <button
            type="button"
            disabled
            title="Прикрепление файлов появится в анкете заявки"
            className="inline-flex size-10 shrink-0 cursor-not-allowed items-center justify-center rounded-full text-text-secondary opacity-50"
          >
            <PaperclipIcon className="size-4.5" />
          </button>
          <textarea
            ref={textareaRef}
            rows={1}
            value={value}
            onChange={handleChange}
            onKeyDown={handleKeyDown}
            disabled={isSending}
            placeholder={isSending ? 'Ассистент отвечает…' : 'Опишите ваш бизнес и цель кредита…'}
            className={cn(
              'max-h-40 min-h-10 flex-1 resize-none rounded-xl border border-border bg-bg-primary px-3.5 py-2.5 text-sm outline-none placeholder:text-text-secondary focus-visible:border-accent focus-visible:ring-3 focus-visible:ring-accent/20 disabled:opacity-60',
            )}
          />
          <button
            type="button"
            onClick={() => submit(value)}
            disabled={!value.trim() || isSending}
            aria-label="Отправить"
            className="inline-flex size-10 shrink-0 cursor-pointer items-center justify-center rounded-full bg-accent text-white transition-colors hover:bg-accent-hover active:bg-accent-press disabled:pointer-events-none disabled:opacity-50"
          >
            <SendHorizonalIcon className="size-4.5" />
          </button>
        </div>
        <p className="mt-1.5 px-1 text-[11px] text-text-secondary">
          Enter — отправить, Shift+Enter — новая строка
        </p>
      </footer>
    </section>
  )
}
