import { useState, useCallback } from 'react'
import { Monitor, RefreshCw, Camera, Eye, Send } from 'lucide-react'

interface CaptureResult {
  image_base64?: string
  has_image?: boolean
  message?: string
  error?: string
}

export function ScreenPanel({ onSendToChat }: { onSendToChat: (msg: string) => void }) {
  const [capturing, setCapturing] = useState(false)
  const [frame, setFrame] = useState<string | null>(null)
  const [status, setStatus] = useState('')
  const [mode, setMode] = useState<'screen' | 'frame'>('screen')
  const [analyzePrompt, setAnalyzePrompt] = useState('Analyze what you see in this Resolve screen. Describe the timeline, current clip, color grade, and anything noteworthy.')

  const capture = useCallback(async () => {
    setCapturing(true)
    setStatus('Capturing…')
    try {
      const endpoint = mode === 'frame' ? '/api/resolve/frame' : '/api/resolve/screen'
      const res = await fetch(endpoint, { method: 'POST' })
      const data: CaptureResult = await res.json()

      if (data.error) {
        setStatus(`Error: ${data.error}`)
        return
      }
      if (data.image_base64) {
        setFrame(`data:image/jpeg;base64,${data.image_base64}`)
        setStatus(data.message ?? 'Captured')
      } else {
        setStatus('No image returned')
      }
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'Capture failed')
    }
    setCapturing(false)
  }, [mode])

  const sendToChat = () => {
    onSendToChat(analyzePrompt + (mode === 'screen' ? ' [use capture_screen tool]' : ' [use grab_resolve_frame tool]'))
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-resolve-border shrink-0">
        <div className="flex items-center gap-2">
          <Monitor size={14} className="text-indigo-400" />
          <span className="text-xs font-semibold text-gray-300">Screen View</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Mode selector */}
        <div className="flex gap-2">
          {([
            { id: 'screen', label: 'Full Screen', icon: <Monitor size={12} /> },
            { id: 'frame', label: 'Resolve Frame', icon: <Camera size={12} /> },
          ] as const).map((m) => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs border transition-all ${
                mode === m.id
                  ? 'bg-resolve-accent/20 border-resolve-accent/40 text-resolve-accent'
                  : 'bg-resolve-panel border-resolve-border text-gray-500 hover:text-gray-300'
              }`}
            >
              {m.icon} {m.label}
            </button>
          ))}
        </div>

        {/* Capture button */}
        <button
          onClick={capture}
          disabled={capturing}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-indigo-600/20 border border-indigo-600/40 text-xs text-indigo-400 hover:bg-indigo-600/30 transition-colors disabled:opacity-40"
        >
          <RefreshCw size={13} className={capturing ? 'animate-spin' : ''} />
          {capturing ? 'Capturing…' : mode === 'screen' ? 'Take Screenshot' : 'Grab Current Frame'}
        </button>

        {status && (
          <p className={`text-[10px] ${status.startsWith('Error') ? 'text-red-400' : 'text-gray-500'}`}>
            {status}
          </p>
        )}

        {/* Preview */}
        {frame && (
          <div className="rounded-xl overflow-hidden border border-resolve-border">
            <img src={frame} alt="Resolve screen" className="w-full" />
          </div>
        )}

        {/* Send to Claude for analysis */}
        <div className="border border-resolve-border rounded-xl p-3 space-y-2">
          <div className="flex items-center gap-2">
            <Eye size={12} className="text-gray-500" />
            <p className="text-xs font-medium text-gray-300">Ask Claude to analyze</p>
          </div>
          <textarea
            value={analyzePrompt}
            onChange={(e) => setAnalyzePrompt(e.target.value)}
            rows={3}
            className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-3 py-2 text-xs text-gray-300 placeholder-gray-600 resize-none focus:outline-none focus:border-resolve-accent/40"
          />
          <button
            onClick={sendToChat}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-resolve-panel border border-resolve-border text-xs text-gray-400 hover:text-gray-200 hover:border-gray-500 transition-colors"
          >
            <Send size={12} />
            Send to Claude
          </button>
        </div>

        {/* Info */}
        <div className="rounded-xl border border-resolve-border p-3 space-y-1.5">
          <p className="text-[10px] font-medium text-gray-400">How it works</p>
          <p className="text-[10px] text-gray-600 leading-relaxed">
            Claude calls <code className="text-purple-400">capture_screen()</code> or{' '}
            <code className="text-purple-400">grab_resolve_frame()</code> as tools.
            The image is passed directly to Claude's vision — it can see color grades,
            UI state, clip names, and anything on screen.
          </p>
          <p className="text-[10px] text-gray-600 leading-relaxed">
            You can also just say <span className="text-gray-400">"what do you see?"</span> or{' '}
            <span className="text-gray-400">"analyze the current frame"</span> in chat.
          </p>
          <p className="text-[10px] text-yellow-600">
            ⚠ macOS: grant Screen Recording permission to Terminal in System Preferences → Privacy & Security.
          </p>
        </div>
      </div>
    </div>
  )
}
