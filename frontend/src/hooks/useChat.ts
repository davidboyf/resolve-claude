import { useState, useRef, useCallback } from 'react'
import { streamChat } from '../lib/api'

export type EventType = 'text' | 'tool_call' | 'tool_result' | 'error' | 'done'

export interface ChatEvent {
  type: EventType
  content?: string
  tool_name?: string
  tool_input?: Record<string, unknown>
  result?: Record<string, unknown>
}

export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  text: string
  events: ChatEvent[]
  isStreaming?: boolean
  timestamp: Date
}

let msgId = 0
const nextId = () => String(++msgId)

export function useChat(model: string) {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const abortRef = useRef<boolean>(false)

  // History for the Claude API (only text content)
  const historyRef = useRef<{ role: 'user' | 'assistant'; content: string }[]>([])

  const sendMessage = useCallback(
    async (text: string) => {
      if (!text.trim() || isLoading) return

      // Add user message
      const userMsg: ChatMessage = {
        id: nextId(),
        role: 'user',
        text,
        events: [],
        timestamp: new Date(),
      }

      setMessages((prev) => [...prev, userMsg])
      historyRef.current.push({ role: 'user', content: text })

      // Add streaming assistant message
      const assistantId = nextId()
      const assistantMsg: ChatMessage = {
        id: assistantId,
        role: 'assistant',
        text: '',
        events: [],
        isStreaming: true,
        timestamp: new Date(),
      }
      setMessages((prev) => [...prev, assistantMsg])
      setIsLoading(true)
      abortRef.current = false

      let fullText = ''

      try {
        for await (const event of streamChat(historyRef.current, model)) {
          if (abortRef.current) break

          if (event.type === 'text') {
            fullText += event.content ?? ''
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, text: fullText, events: [...m.events, event] }
                  : m
              )
            )
          } else if (event.type === 'tool_call' || event.type === 'tool_result') {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? { ...m, events: [...m.events, event] }
                  : m
              )
            )
          } else if (event.type === 'error') {
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      text: fullText + `\n\n⚠️ Error: ${event.content}`,
                      events: [...m.events, event],
                      isStreaming: false,
                    }
                  : m
              )
            )
            break
          } else if (event.type === 'done') {
            break
          }
        }
      } catch (e) {
        const errText = e instanceof Error ? e.message : String(e)
        setMessages((prev) =>
          prev.map((m) =>
            m.id === assistantId
              ? { ...m, text: `⚠️ ${errText}`, isStreaming: false }
              : m
          )
        )
      }

      // Finalize
      setMessages((prev) =>
        prev.map((m) =>
          m.id === assistantId ? { ...m, isStreaming: false } : m
        )
      )

      if (fullText) {
        historyRef.current.push({ role: 'assistant', content: fullText })
      }

      setIsLoading(false)
    },
    [isLoading, model]
  )

  const clearMessages = useCallback(() => {
    setMessages([])
    historyRef.current = []
  }, [])

  const stopStreaming = useCallback(() => {
    abortRef.current = true
    setIsLoading(false)
  }, [])

  return { messages, isLoading, sendMessage, clearMessages, stopStreaming }
}
