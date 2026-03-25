import { useState } from 'react'
import { Sparkles, Wand2, Download, Film, Zap, RefreshCw } from 'lucide-react'

const STYLES = [
  'cinematic', 'photorealistic', 'dramatic lighting', 'golden hour',
  'neon noir', 'vintage film', 'minimal clean', 'dark moody',
  'bright airy', 'film burn', 'dream sequence', 'glitch art',
]

const TRANSITION_STYLES = [
  'cinematic blend', 'light leak', 'film burn', 'dream sequence',
  'glitch transition', 'ink wash', 'particle dissolve', 'lens flare',
  'bokeh blur', 'color shift wipe',
]

const PROVIDERS = [
  { value: 'auto', label: 'Auto (best available)', desc: '' },
  { value: 'dalle3', label: 'DALL-E 3', desc: 'Needs OPENAI_API_KEY' },
  { value: 'flux', label: 'Flux Schnell', desc: 'Needs FAL_KEY — very fast' },
]

interface GeneratedImage {
  file_path: string
  image_base64: string
  media_type: string
  revised_prompt?: string
  model?: string
  size?: string
}

export function AIGeneratePanel({ onSendToChat }: { onSendToChat: (msg: string) => void }) {
  const [mode, setMode] = useState<'image' | 'transition'>('image')
  const [prompt, setPrompt] = useState('')
  const [style, setStyle] = useState('cinematic')
  const [provider, setProvider] = useState('auto')
  const [width, setWidth] = useState(1920)
  const [height, setHeight] = useState(1080)
  const [generating, setGenerating] = useState(false)
  const [result, setResult] = useState<GeneratedImage | null>(null)
  const [status, setStatus] = useState('')
  const [dropping, setDropping] = useState(false)
  const [dropDuration, setDropDuration] = useState(3)
  const [dropPosition, setDropPosition] = useState(-1)
  // Transition settings
  const [clipBefore, setClipBefore] = useState(0)
  const [clipAfter, setClipAfter] = useState(1)
  const [transitionStyle, setTransitionStyle] = useState('cinematic blend')
  const [transitionDuration, setTransitionDuration] = useState(2)

  const generateImage = async () => {
    if (!prompt.trim() && mode === 'image') return
    setGenerating(true)
    setResult(null)
    setStatus('Generating…')
    try {
      const body = mode === 'image'
        ? { prompt: prompt.trim(), provider, width, height, style }
        : null

      if (mode === 'image') {
        const res = await fetch('/api/ai/generate', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(body),
        })
        const data = await res.json()
        if (data.error) {
          setStatus(`Error: ${data.error}`)
        } else if (data.success) {
          setResult(data)
          setStatus(`Generated with ${data.model ?? provider}`)
        }
      }
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'Generation failed')
    }
    setGenerating(false)
  }

  const generateTransition = () => {
    onSendToChat(
      `Generate an AI transition between clip ${clipBefore} and clip ${clipAfter} on track 1. ` +
      `Style: "${transitionStyle}". Duration: ${transitionDuration} seconds. ` +
      `Use the generate_ai_transition tool.`
    )
    setStatus('Sent to Claude — watch the chat for progress')
  }

  const dropToTimeline = async () => {
    if (!result?.file_path) return
    setDropping(true)
    setStatus('Dropping to timeline…')
    try {
      const res = await fetch('/api/ai/drop-to-timeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          file_path: result.file_path,
          position_seconds: dropPosition,
          duration_seconds: dropDuration,
        }),
      })
      const data = await res.json()
      if (data.success) {
        setStatus(`Added to timeline at ${dropPosition < 0 ? 'end' : `${dropPosition}s`} for ${dropDuration}s`)
      } else {
        setStatus(`Error: ${data.error ?? 'Failed'}`)
      }
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'Failed')
    }
    setDropping(false)
  }

  const sendGenerateToChat = () => {
    const p = prompt.trim() || `${style} style background for a video production`
    onSendToChat(
      `Generate an AI image with this prompt: "${p}". Style: ${style}. ` +
      `Size: ${width}x${height}. Provider: ${provider}. ` +
      `Use generate_ai_image tool, then drop_ai_image_to_timeline to add it to the timeline for 3 seconds.`
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-resolve-border shrink-0">
        <Sparkles size={14} className="text-yellow-400" />
        <span className="text-xs font-semibold text-gray-300">AI Generate</span>
        <span className="text-[10px] text-gray-600">NanoBanana</span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Mode tabs */}
        <div className="flex gap-2">
          {([
            { id: 'image', label: 'Generate Image', icon: <Sparkles size={11} /> },
            { id: 'transition', label: 'AI Transition', icon: <Film size={11} /> },
          ] as const).map((m) => (
            <button
              key={m.id}
              onClick={() => setMode(m.id)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs border transition-all ${
                mode === m.id
                  ? 'bg-yellow-500/20 border-yellow-500/40 text-yellow-400'
                  : 'bg-resolve-panel border-resolve-border text-gray-500 hover:text-gray-300'
              }`}
            >
              {m.icon} {m.label}
            </button>
          ))}
        </div>

        {mode === 'image' ? (
          <>
            {/* Prompt */}
            <div>
              <label className="text-[10px] text-gray-500 mb-1 block">Prompt</label>
              <textarea
                value={prompt}
                onChange={(e) => setPrompt(e.target.value)}
                placeholder="A sweeping aerial shot of a golden sunset over mountains…"
                rows={3}
                className="w-full bg-resolve-bg border border-resolve-border rounded-xl px-3 py-2 text-xs text-gray-300 placeholder-gray-600 resize-none focus:outline-none focus:border-yellow-500/40 leading-relaxed"
              />
            </div>

            {/* Style chips */}
            <div>
              <label className="text-[10px] text-gray-500 mb-1.5 block">Style</label>
              <div className="flex flex-wrap gap-1.5">
                {STYLES.map((s) => (
                  <button
                    key={s}
                    onClick={() => setStyle(s)}
                    className={`px-2.5 py-1 rounded-full text-[10px] border transition-all ${
                      style === s
                        ? 'bg-yellow-500/20 border-yellow-500/40 text-yellow-400'
                        : 'bg-resolve-panel border-resolve-border text-gray-500 hover:text-gray-300'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            {/* Provider + Size */}
            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] text-gray-500 mb-1 block">Provider</label>
                <select
                  value={provider}
                  onChange={(e) => setProvider(e.target.value)}
                  className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none"
                >
                  {PROVIDERS.map((p) => (
                    <option key={p.value} value={p.value}>
                      {p.label}{p.desc ? ` (${p.desc})` : ''}
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label className="text-[10px] text-gray-500 mb-1 block">Resolution</label>
                <select
                  value={`${width}x${height}`}
                  onChange={(e) => {
                    const [w, h] = e.target.value.split('x').map(Number)
                    setWidth(w); setHeight(h)
                  }}
                  className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none"
                >
                  <option value="1920x1080">1920×1080 (16:9)</option>
                  <option value="1080x1920">1080×1920 (9:16)</option>
                  <option value="1080x1080">1080×1080 (1:1)</option>
                  <option value="2560x1440">2560×1440 (2K)</option>
                  <option value="3840x2160">3840×2160 (4K)</option>
                </select>
              </div>
            </div>

            {/* Generate buttons */}
            <div className="flex gap-2">
              <button
                onClick={generateImage}
                disabled={generating || !prompt.trim()}
                className="flex-1 flex items-center justify-center gap-2 py-2.5 rounded-xl bg-yellow-500/20 border border-yellow-500/40 text-xs text-yellow-400 hover:bg-yellow-500/30 transition-colors disabled:opacity-40"
              >
                <RefreshCw size={13} className={generating ? 'animate-spin' : ''} />
                {generating ? 'Generating…' : 'Generate'}
              </button>
              <button
                onClick={sendGenerateToChat}
                className="flex items-center justify-center gap-2 px-4 py-2.5 rounded-xl bg-resolve-panel border border-resolve-border text-xs text-gray-400 hover:text-gray-200 hover:border-gray-500 transition-colors"
                title="Ask Claude to generate and place on timeline"
              >
                <Wand2 size={13} />
                Auto
              </button>
            </div>

            {status && (
              <p className={`text-[10px] ${status.startsWith('Error') ? 'text-red-400' : 'text-gray-500'}`}>
                {status}
              </p>
            )}

            {/* Preview */}
            {result && (
              <div className="space-y-2">
                <div className="rounded-xl overflow-hidden border border-resolve-border">
                  <img
                    src={`data:${result.media_type};base64,${result.image_base64}`}
                    alt="Generated"
                    className="w-full"
                  />
                </div>

                {result.revised_prompt && (
                  <p className="text-[10px] text-gray-600 italic leading-relaxed">
                    "{result.revised_prompt}"
                  </p>
                )}

                <p className="text-[10px] text-gray-600 font-mono">{result.file_path}</p>

                {/* Drop to timeline */}
                <div className="border border-resolve-border rounded-xl p-3 space-y-2">
                  <p className="text-xs font-medium text-gray-300">Drop to Timeline</p>
                  <div className="flex gap-2">
                    <div className="flex-1">
                      <label className="text-[9px] text-gray-600 block mb-1">Position (s, -1=end)</label>
                      <input
                        type="number"
                        value={dropPosition}
                        onChange={(e) => setDropPosition(parseFloat(e.target.value))}
                        className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1 text-xs text-gray-300 focus:outline-none font-mono"
                      />
                    </div>
                    <div className="flex-1">
                      <label className="text-[9px] text-gray-600 block mb-1">Duration (s)</label>
                      <input
                        type="number"
                        min={0.5}
                        step={0.5}
                        value={dropDuration}
                        onChange={(e) => setDropDuration(parseFloat(e.target.value))}
                        className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1 text-xs text-gray-300 focus:outline-none font-mono"
                      />
                    </div>
                  </div>
                  <button
                    onClick={dropToTimeline}
                    disabled={dropping}
                    className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-resolve-panel border border-resolve-border text-xs text-gray-400 hover:text-white hover:border-yellow-500/50 transition-all disabled:opacity-40"
                  >
                    <Download size={13} />
                    {dropping ? 'Dropping…' : 'Drop to Timeline'}
                  </button>
                </div>
              </div>
            )}
          </>
        ) : (
          /* Transition mode */
          <>
            <div className="rounded-xl border border-yellow-600/20 bg-yellow-600/5 p-3">
              <p className="text-xs font-medium text-yellow-400 mb-1">AI Transition Generator</p>
              <p className="text-[10px] text-gray-500 leading-relaxed">
                Claude grabs the last frame of clip A and first frame of clip B,
                generates a custom transition image using AI, then places it between the clips on your timeline.
              </p>
            </div>

            <div className="grid grid-cols-2 gap-2">
              <div>
                <label className="text-[10px] text-gray-500 mb-1 block">Clip Before (index)</label>
                <input
                  type="number" min={0} value={clipBefore}
                  onChange={(e) => setClipBefore(parseInt(e.target.value) || 0)}
                  className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none font-mono"
                />
              </div>
              <div>
                <label className="text-[10px] text-gray-500 mb-1 block">Clip After (index)</label>
                <input
                  type="number" min={1} value={clipAfter}
                  onChange={(e) => setClipAfter(parseInt(e.target.value) || 1)}
                  className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none font-mono"
                />
              </div>
            </div>

            <div>
              <label className="text-[10px] text-gray-500 mb-1.5 block">Transition Style</label>
              <div className="flex flex-wrap gap-1.5">
                {TRANSITION_STYLES.map((s) => (
                  <button
                    key={s}
                    onClick={() => setTransitionStyle(s)}
                    className={`px-2.5 py-1 rounded-full text-[10px] border transition-all ${
                      transitionStyle === s
                        ? 'bg-yellow-500/20 border-yellow-500/40 text-yellow-400'
                        : 'bg-resolve-panel border-resolve-border text-gray-500 hover:text-gray-300'
                    }`}
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>

            <div>
              <label className="text-[10px] text-gray-500 mb-1 block">Duration (seconds)</label>
              <input
                type="number" min={0.5} step={0.5} value={transitionDuration}
                onChange={(e) => setTransitionDuration(parseFloat(e.target.value))}
                className="w-32 bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none font-mono"
              />
            </div>

            <button
              onClick={generateTransition}
              className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-yellow-500/20 border border-yellow-500/40 text-xs text-yellow-400 hover:bg-yellow-500/30 transition-colors"
            >
              <Zap size={13} />
              Generate AI Transition
            </button>

            {status && (
              <p className="text-[10px] text-gray-500">{status}</p>
            )}
          </>
        )}
      </div>
    </div>
  )
}
