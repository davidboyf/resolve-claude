import { useRef, useEffect, useState, KeyboardEvent } from 'react'
import {
  Send, Square, Trash2, Scissors, Palette, Volume2,
  Film, Zap, ChevronDown
} from 'lucide-react'
import { MessageBubble } from './MessageBubble'
import { useChat } from '../hooks/useChat'

const QUICK_ACTIONS = [
  { icon: <Film size={13} />, label: 'Analyze timeline', prompt: 'Analyze my timeline and give me a summary of all clips, their durations, and any issues you notice.' },
  { icon: <Scissors size={13} />, label: 'Auto-cut silences', prompt: 'Look at my timeline and mark any clips that appear to be just silence, dead air, or very short unusable clips with Red markers labeled "Cut".' },
  { icon: <Palette size={13} />, label: 'Cinematic grade', prompt: 'Apply a cinematic color grade to the first clip on track 1: lift the shadows slightly blue, add warmth to the highlights, boost contrast to 1.1, and reduce saturation slightly to 0.9.' },
  { icon: <Volume2 size={13} />, label: 'Balance audio', prompt: 'Check my audio tracks and set them to appropriate broadcast levels (-12 dB for dialogue, -18 dB for music if present).' },
  { icon: <Zap size={13} />, label: 'Best moments', prompt: 'Review my timeline and add Green markers labeled "Keep" at timestamps you think represent the strongest or most interesting moments based on clip names and lengths.' },
]

const MODELS = [
  { value: 'claude-sonnet-4-6', label: 'Sonnet 4.6', desc: 'Fast · Best for chat' },
  { value: 'claude-opus-4-6', label: 'Opus 4.6', desc: 'Deep analysis · Slower' },
  { value: 'claude-haiku-4-5-20251001', label: 'Haiku 4.5', desc: 'Fastest · Simple tasks' },
]

interface ChatPanelProps {
  externalMessage?: string
  onExternalMessageConsumed?: () => void
}

export function ChatPanel({ externalMessage, onExternalMessageConsumed }: ChatPanelProps) {
  const [model, setModel] = useState('claude-sonnet-4-6')
  const [input, setInput] = useState('')
  const [showModelMenu, setShowModelMenu] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const { messages, isLoading, sendMessage, clearMessages, stopStreaming } = useChat(model)

  // Accept messages injected from other panels (Screen, AI Generate, Color Reference)
  useEffect(() => {
    if (externalMessage) {
      sendMessage(externalMessage)
      onExternalMessageConsumed?.()
    }
  }, [externalMessage])

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSend = () => {
    if (!input.trim()) return
    sendMessage(input)
    setInput('')
    inputRef.current?.focus()
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const selectedModel = MODELS.find((m) => m.value === model)!

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-resolve-border shrink-0">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 rounded-full bg-purple-400 animate-pulse-slow" />
          <span className="text-sm font-semibold text-white">Claude</span>
          <span className="text-xs text-gray-500">× DaVinci Resolve</span>
        </div>

        <div className="flex items-center gap-2">
          {/* Model selector */}
          <div className="relative">
            <button
              onClick={() => setShowModelMenu((v) => !v)}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-resolve-panel border border-resolve-border text-xs text-gray-300 hover:border-gray-500 transition-colors"
            >
              <span className="font-medium">{selectedModel.label}</span>
              <ChevronDown size={12} className="text-gray-500" />
            </button>
            {showModelMenu && (
              <div className="absolute top-full right-0 mt-1 w-52 bg-resolve-panel border border-resolve-border rounded-xl shadow-2xl z-50 overflow-hidden animate-fade-in">
                {MODELS.map((m) => (
                  <button
                    key={m.value}
                    onClick={() => { setModel(m.value); setShowModelMenu(false) }}
                    className={`w-full text-left px-3 py-2.5 hover:bg-white/5 transition-colors ${
                      m.value === model ? 'bg-white/5' : ''
                    }`}
                  >
                    <div className="text-xs font-semibold text-white">{m.label}</div>
                    <div className="text-[10px] text-gray-500">{m.desc}</div>
                  </button>
                ))}
              </div>
            )}
          </div>

          <button
            onClick={clearMessages}
            className="p-1.5 rounded-lg text-gray-600 hover:text-gray-400 hover:bg-white/5 transition-colors"
            title="Clear chat"
          >
            <Trash2 size={14} />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-6 px-8 text-center">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-purple-600 to-indigo-700 flex items-center justify-center shadow-lg shadow-purple-900/30">
              <span className="text-3xl">🎬</span>
            </div>
            <div>
              <h2 className="text-lg font-semibold text-white mb-1">Claude is ready</h2>
              <p className="text-sm text-gray-500 leading-relaxed">
                Ask me to edit your timeline, grade your footage, balance audio, or anything else.
                I have full control over your open DaVinci Resolve project.
              </p>
            </div>
            {/* Quick actions */}
            <div className="flex flex-col gap-2 w-full max-w-xs">
              {QUICK_ACTIONS.map((a) => (
                <button
                  key={a.label}
                  onClick={() => sendMessage(a.prompt)}
                  className="flex items-center gap-2.5 px-3 py-2.5 rounded-xl bg-resolve-panel border border-resolve-border hover:border-resolve-accent/50 hover:bg-resolve-accent/5 transition-all text-left group"
                >
                  <span className="text-gray-500 group-hover:text-resolve-accent transition-colors">{a.icon}</span>
                  <span className="text-xs text-gray-400 group-hover:text-gray-200 transition-colors">{a.label}</span>
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div>
            {messages.map((msg) => (
              <MessageBubble key={msg.id} message={msg} />
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Quick action chips (when messages exist) */}
      {messages.length > 0 && (
        <div className="px-4 py-2 border-t border-resolve-border flex gap-2 overflow-x-auto shrink-0">
          {QUICK_ACTIONS.map((a) => (
            <button
              key={a.label}
              onClick={() => sendMessage(a.prompt)}
              disabled={isLoading}
              className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg bg-resolve-panel border border-resolve-border text-xs text-gray-400 hover:text-gray-200 hover:border-gray-500 whitespace-nowrap shrink-0 transition-all disabled:opacity-40"
            >
              {a.icon}
              {a.label}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div className="px-4 py-3 border-t border-resolve-border shrink-0">
        <div className="flex gap-2 items-end">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Ask Claude to edit, cut, grade, or analyze…"
              rows={1}
              className="w-full bg-resolve-panel border border-resolve-border rounded-xl px-4 py-3 text-sm text-gray-200 placeholder-gray-600 resize-none focus:outline-none focus:border-resolve-accent/60 focus:ring-1 focus:ring-resolve-accent/20 transition-all"
              style={{ maxHeight: '120px', height: 'auto' }}
              onInput={(e) => {
                const t = e.target as HTMLTextAreaElement
                t.style.height = 'auto'
                t.style.height = Math.min(t.scrollHeight, 120) + 'px'
              }}
              disabled={isLoading}
            />
          </div>
          <button
            onClick={isLoading ? stopStreaming : handleSend}
            className={`shrink-0 w-10 h-10 rounded-xl flex items-center justify-center transition-all ${
              isLoading
                ? 'bg-red-600/20 border border-red-600/40 text-red-400 hover:bg-red-600/30'
                : input.trim()
                ? 'bg-resolve-accent text-white hover:bg-resolve-accent-dim shadow-lg shadow-resolve-accent/20'
                : 'bg-resolve-panel border border-resolve-border text-gray-600'
            }`}
            title={isLoading ? 'Stop' : 'Send (Enter)'}
          >
            {isLoading ? <Square size={15} /> : <Send size={15} />}
          </button>
        </div>
        <p className="text-[10px] text-gray-600 mt-1.5 text-center">
          Enter to send · Shift+Enter for newline
        </p>
      </div>
    </div>
  )
}
