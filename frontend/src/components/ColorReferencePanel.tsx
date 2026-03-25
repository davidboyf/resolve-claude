import { useState, useRef } from 'react'
import { ImageIcon, Link, Upload, Wand2, Send } from 'lucide-react'

export function ColorReferencePanel({ onSendToChat }: { onSendToChat: (msg: string) => void }) {
  const [source, setSource] = useState<'url' | 'path'>('url')
  const [input, setInput] = useState('')
  const [preview, setPreview] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [status, setStatus] = useState('')
  const [clipTrack, setClipTrack] = useState(1)
  const [clipIndex, setClipIndex] = useState(0)
  const [analysisPrompt, setAnalysisPrompt] = useState(
    'Analyze this reference image: describe the color grade characteristics (shadows, mids, highlights color temperature, saturation level, contrast, skin tone treatment, overall mood). Then apply a matching color grade to clip at track={TRACK} clip_index={INDEX} using apply_color_wheel, set_contrast_saturation, and any other needed tools.'
  )

  const loadImage = async () => {
    if (!input.trim()) return
    setLoading(true)
    setStatus('Loading image…')
    try {
      const res = await fetch('/api/reference-image/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path_or_url: input.trim() }),
      })
      const data = await res.json()
      if (data.error) {
        setStatus(`Error: ${data.error}`)
      } else if (data.image_base64) {
        setPreview(`data:${data.media_type};base64,${data.image_base64}`)
        setStatus('Image loaded')
      }
    } catch (e) {
      setStatus(e instanceof Error ? e.message : 'Failed')
    }
    setLoading(false)
  }

  const matchGrade = () => {
    const prompt = analysisPrompt
      .replace('{TRACK}', String(clipTrack))
      .replace('{INDEX}', String(clipIndex))
    const fullPrompt = `Load the reference image at "${input.trim()}" using load_reference_image tool, then ${prompt}`
    onSendToChat(fullPrompt)
    setStatus('Sent to Claude for analysis and grade matching')
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-resolve-border shrink-0">
        <ImageIcon size={14} className="text-rose-400" />
        <span className="text-xs font-semibold text-gray-300">Color Reference</span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Source type */}
        <div className="flex gap-2">
          {([
            { id: 'url', label: 'URL / Link', icon: <Link size={11} /> },
            { id: 'path', label: 'File Path', icon: <Upload size={11} /> },
          ] as const).map((s) => (
            <button
              key={s.id}
              onClick={() => setSource(s.id)}
              className={`flex-1 flex items-center justify-center gap-1.5 py-2 rounded-xl text-xs border transition-all ${
                source === s.id
                  ? 'bg-rose-600/20 border-rose-600/40 text-rose-400'
                  : 'bg-resolve-panel border-resolve-border text-gray-500 hover:text-gray-300'
              }`}
            >
              {s.icon} {s.label}
            </button>
          ))}
        </div>

        {/* Input */}
        <div className="flex gap-2">
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && loadImage()}
            placeholder={source === 'url' ? 'https://…' : '/path/to/reference.jpg'}
            className="flex-1 bg-resolve-bg border border-resolve-border rounded-lg px-3 py-1.5 text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-rose-500/40 font-mono"
          />
          <button
            onClick={loadImage}
            disabled={loading || !input.trim()}
            className="px-3 py-1.5 rounded-lg bg-rose-600/20 border border-rose-600/40 text-xs text-rose-400 hover:bg-rose-600/30 transition-colors disabled:opacity-40"
          >
            {loading ? '…' : 'Load'}
          </button>
        </div>

        {status && (
          <p className={`text-[10px] ${status.startsWith('Error') ? 'text-red-400' : 'text-gray-500'}`}>
            {status}
          </p>
        )}

        {/* Preview */}
        {preview && (
          <div className="rounded-xl overflow-hidden border border-resolve-border">
            <img src={preview} alt="Reference" className="w-full" />
          </div>
        )}

        {/* Target clip */}
        <div>
          <p className="text-[10px] text-gray-500 mb-2">Apply grade to clip:</p>
          <div className="flex gap-2">
            <div className="flex-1">
              <label className="text-[9px] text-gray-600 mb-1 block">Track</label>
              <input
                type="number" min={1} value={clipTrack}
                onChange={(e) => setClipTrack(parseInt(e.target.value) || 1)}
                className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-rose-500/40"
              />
            </div>
            <div className="flex-1">
              <label className="text-[9px] text-gray-600 mb-1 block">Clip Index</label>
              <input
                type="number" min={0} value={clipIndex}
                onChange={(e) => setClipIndex(parseInt(e.target.value) || 0)}
                className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-rose-500/40"
              />
            </div>
          </div>
        </div>

        {/* Analysis prompt */}
        <div>
          <label className="text-[10px] text-gray-500 mb-1 block">Analysis instructions</label>
          <textarea
            value={analysisPrompt}
            onChange={(e) => setAnalysisPrompt(e.target.value)}
            rows={4}
            className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-3 py-2 text-xs text-gray-300 resize-none focus:outline-none focus:border-rose-500/40 leading-relaxed"
          />
        </div>

        {/* Match button */}
        <button
          onClick={matchGrade}
          disabled={!input.trim()}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-rose-600/20 border border-rose-600/40 text-xs text-rose-400 hover:bg-rose-600/30 transition-colors disabled:opacity-40"
        >
          <Wand2 size={13} />
          Match Color Grade
        </button>

        {/* Info */}
        <div className="rounded-xl border border-resolve-border p-3 space-y-1.5">
          <p className="text-[10px] font-medium text-gray-400">How it works</p>
          <p className="text-[10px] text-gray-600 leading-relaxed">
            Claude calls <code className="text-purple-400">load_reference_image()</code>, sees the image via vision, analyzes the color characteristics, and then calls the color grading tools to match that look on your clip.
          </p>
          <p className="text-[10px] text-gray-600 leading-relaxed">
            Works with any reference: a film still, Instagram photo, director's reference, or even a screenshot of another clip's grade.
          </p>
        </div>
      </div>
    </div>
  )
}
