import { Bot, User } from 'lucide-react'
import type { ChatMessage, ChatEvent } from '../hooks/useChat'
import { ToolGroup } from './ToolCallCard'

interface Props {
  message: ChatMessage
}

function formatTime(d: Date) {
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// Pair tool_call events with their tool_result
function groupToolEvents(events: ChatEvent[]) {
  const groups: { call: ChatEvent; result?: ChatEvent }[] = []
  const pending: Record<string, number> = {}

  for (const e of events) {
    if (e.type === 'tool_call') {
      const idx = groups.length
      groups.push({ call: e })
      pending[e.tool_name ?? ''] = idx
    } else if (e.type === 'tool_result') {
      const idx = pending[e.tool_name ?? '']
      if (idx !== undefined) {
        groups[idx].result = e
        delete pending[e.tool_name ?? '']
      } else {
        groups.push({ call: { type: 'tool_call', tool_name: e.tool_name }, result: e })
      }
    }
  }
  return groups
}

export function MessageBubble({ message }: Props) {
  const isUser = message.role === 'user'
  const toolGroups = groupToolEvents(message.events)

  return (
    <div className={`flex gap-3 py-4 px-4 ${isUser ? 'flex-row-reverse' : 'flex-row'} animate-slide-up`}>
      {/* Avatar */}
      <div
        className={`shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-xs font-semibold mt-0.5 ${
          isUser
            ? 'bg-resolve-accent text-white'
            : 'bg-gradient-to-br from-purple-600 to-indigo-700 text-white'
        }`}
      >
        {isUser ? <User size={16} /> : <Bot size={16} />}
      </div>

      {/* Content */}
      <div className={`flex-1 max-w-[85%] ${isUser ? 'items-end' : 'items-start'} flex flex-col gap-1`}>
        <div className="flex items-center gap-2">
          <span className={`text-xs font-semibold ${isUser ? 'text-resolve-accent' : 'text-purple-400'}`}>
            {isUser ? 'You' : 'Claude'}
          </span>
          <span className="text-[10px] text-gray-600">{formatTime(message.timestamp)}</span>
        </div>

        {/* Tool calls */}
        {toolGroups.length > 0 && (
          <div className="w-full">
            {toolGroups.map((g, i) => (
              <ToolGroup
                key={i}
                toolName={g.call.tool_name ?? ''}
                input={g.call.tool_input ?? {}}
                result={g.result?.result}
              />
            ))}
          </div>
        )}

        {/* Text content */}
        {(message.text || message.isStreaming) && (
          <div
            className={`rounded-2xl px-4 py-3 text-sm leading-relaxed chat-text ${
              isUser
                ? 'bg-resolve-accent/20 border border-resolve-accent/30 text-resolve-user rounded-tr-sm'
                : 'bg-resolve-panel border border-resolve-border text-resolve-user rounded-tl-sm'
            }`}
          >
            {message.text || (message.isStreaming ? '' : '…')}
            {message.isStreaming && !message.text && toolGroups.length === 0 && (
              <span className="inline-flex gap-1 items-center text-gray-500">
                <span className="text-xs">thinking</span>
                <span className="cursor-blink" />
              </span>
            )}
            {message.isStreaming && message.text && <span className="cursor-blink" />}
          </div>
        )}
      </div>
    </div>
  )
}
