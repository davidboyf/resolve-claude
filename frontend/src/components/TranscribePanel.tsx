import { useState } from 'react'
import { Mic, MicOff, Bookmark, Copy, Check } from 'lucide-react'
import { transcribeVideo } from '../lib/api'

interface Segment {
  start: number
  end: number
  text: string
}

interface TranscriptResult {
  text: string
  language: string
  segments: Segment[]
  duration: number
  formatted: string
}

const MODEL_SIZES = [
  { value: 'tiny', label: 'Tiny', desc: 'Fastest, least accurate' },
  { value: 'base', label: 'Base', desc: 'Good balance' },
  { value: 'small', label: 'Small', desc: 'Better accuracy' },
  { value: 'medium', label: 'Medium', desc: 'High accuracy' },
  { value: 'large', label: 'Large', desc: 'Best accuracy, slow' },
]

const LANGUAGES = [
  { value: 'en', label: 'English' },
  { value: 'es', label: 'Spanish' },
  { value: 'fr', label: 'French' },
  { value: 'de', label: 'German' },
  { value: 'it', label: 'Italian' },
  { value: 'pt', label: 'Portuguese' },
  { value: 'ja', label: 'Japanese' },
  { value: 'zh', label: 'Chinese' },
  { value: 'ko', label: 'Korean' },
  { value: 'ar', label: 'Arabic' },
]

function formatTime(s: number) {
  const m = Math.floor(s / 60)
  const sec = (s % 60).toFixed(1)
  return `${m}:${sec.padStart(4, '0')}`
}

export function TranscribePanel() {
  const [filePath, setFilePath] = useState('')
  const [modelSize, setModelSize] = useState('base')
  const [language, setLanguage] = useState('en')
  const [loading, setLoading] = useState(false)
  const [progress, setProgress] = useState('')
  const [result, setResult] = useState<TranscriptResult | null>(null)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState(false)
  const [applyingMarkers, setApplyingMarkers] = useState(false)
  const [markerMode, setMarkerMode] = useState<'silence' | 'segments'>('silence')

  const handleTranscribe = async () => {
    if (!filePath.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    setProgress('Extracting audio…')

    try {
      const data = await transcribeVideo(filePath.trim(), language, modelSize)
      if (data.detail) {
        setError(data.detail)
      } else {
        setResult(data)
        setProgress('')
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Transcription failed')
      setProgress('')
    }
    setLoading(false)
  }

  const handleCopy = () => {
    if (!result) return
    navigator.clipboard.writeText(result.formatted)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  const handleApplyMarkers = async () => {
    if (!filePath.trim()) return
    setApplyingMarkers(true)
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{
            role: 'user',
            content: `Apply transcript markers to the timeline. File: "${filePath.trim()}", mode: "${markerMode}", language: "${language}", model_size: "${modelSize}". Use the apply_transcript_markers tool.`,
          }],
          model: 'claude-sonnet-4-6',
        }),
      })
      // Drain the stream
      const reader = res.body?.getReader()
      if (reader) {
        while (true) {
          const { done } = await reader.read()
          if (done) break
        }
      }
    } catch {}
    setApplyingMarkers(false)
  }

  const seekTo = async (time: number) => {
    try {
      await fetch('/api/timeline/playhead', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ time_seconds: time }),
      })
    } catch {}
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-resolve-border shrink-0">
        <Mic size={14} className="text-cyan-400" />
        <span className="text-xs font-semibold text-gray-300">Transcribe</span>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* File input */}
        <div>
          <label className="text-[10px] text-gray-500 mb-1 block">Video / Audio File Path</label>
          <input
            value={filePath}
            onChange={(e) => setFilePath(e.target.value)}
            placeholder="/path/to/video.mp4"
            className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-3 py-1.5 text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-resolve-accent/40 font-mono"
          />
        </div>

        {/* Settings */}
        <div className="grid grid-cols-2 gap-2">
          <div>
            <label className="text-[10px] text-gray-500 mb-1 block">Model</label>
            <select
              value={modelSize}
              onChange={(e) => setModelSize(e.target.value)}
              className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-resolve-accent/40"
            >
              {MODEL_SIZES.map((m) => (
                <option key={m.value} value={m.value}>{m.label} — {m.desc}</option>
              ))}
            </select>
          </div>
          <div>
            <label className="text-[10px] text-gray-500 mb-1 block">Language</label>
            <select
              value={language}
              onChange={(e) => setLanguage(e.target.value)}
              className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-resolve-accent/40"
            >
              {LANGUAGES.map((l) => (
                <option key={l.value} value={l.value}>{l.label}</option>
              ))}
            </select>
          </div>
        </div>

        {/* Transcribe button */}
        <button
          onClick={handleTranscribe}
          disabled={loading || !filePath.trim()}
          className="w-full flex items-center justify-center gap-2 py-2.5 rounded-xl bg-cyan-600/20 border border-cyan-600/40 text-xs text-cyan-400 hover:bg-cyan-600/30 transition-colors disabled:opacity-40"
        >
          {loading ? <MicOff size={14} /> : <Mic size={14} />}
          {loading ? (progress || 'Transcribing…') : 'Transcribe'}
        </button>

        {error && (
          <p className="text-xs text-red-400 bg-red-950/30 border border-red-900/50 rounded-lg px-3 py-2">
            {error}
          </p>
        )}

        {/* Apply markers section */}
        <div className="border border-resolve-border rounded-xl p-3 space-y-2">
          <p className="text-xs font-medium text-gray-300">Auto-Apply Markers to Timeline</p>
          <div className="flex gap-2">
            {(['silence', 'segments'] as const).map((m) => (
              <button
                key={m}
                onClick={() => setMarkerMode(m)}
                className={`flex-1 py-1.5 rounded-lg text-xs transition-all ${
                  markerMode === m
                    ? 'bg-resolve-accent/20 border border-resolve-accent/40 text-resolve-accent'
                    : 'bg-resolve-bg border border-resolve-border text-gray-500 hover:text-gray-300'
                }`}
              >
                {m === 'silence' ? '🔴 Silence gaps' : '🔵 Speech starts'}
              </button>
            ))}
          </div>
          <p className="text-[10px] text-gray-600">
            {markerMode === 'silence'
              ? 'Adds Red markers at every silent gap > 0.5s — easy to find dead air to cut.'
              : 'Adds Blue markers at the start of each spoken segment.'}
          </p>
          <button
            onClick={handleApplyMarkers}
            disabled={applyingMarkers || !filePath.trim()}
            className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-resolve-panel border border-resolve-border text-xs text-gray-400 hover:text-gray-200 hover:border-gray-500 transition-colors disabled:opacity-40"
          >
            <Bookmark size={13} />
            {applyingMarkers ? 'Adding markers…' : 'Transcribe & Add Markers'}
          </button>
        </div>

        {/* Transcript result */}
        {result && (
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <p className="text-[10px] text-gray-500 uppercase tracking-wider">
                Transcript — {result.segments.length} segments · {formatTime(result.duration)}
              </p>
              <button
                onClick={handleCopy}
                className="flex items-center gap-1 px-2 py-1 rounded-md text-[10px] text-gray-500 hover:text-gray-300 border border-resolve-border hover:border-gray-500 transition-all"
              >
                {copied ? <Check size={10} className="text-green-400" /> : <Copy size={10} />}
                {copied ? 'Copied' : 'Copy'}
              </button>
            </div>

            <div className="border border-resolve-border rounded-xl overflow-hidden divide-y divide-resolve-border max-h-96 overflow-y-auto">
              {result.segments.map((seg, i) => (
                <button
                  key={i}
                  onClick={() => seekTo(seg.start)}
                  className="w-full flex items-start gap-3 px-3 py-2 hover:bg-white/5 transition-colors text-left"
                  title="Click to seek to this time in Resolve"
                >
                  <span className="text-[10px] font-mono text-resolve-accent shrink-0 mt-0.5 tabular-nums">
                    {formatTime(seg.start)}
                  </span>
                  <span className="text-xs text-gray-300 leading-relaxed">{seg.text}</span>
                  <span className="text-[9px] font-mono text-gray-700 shrink-0 mt-0.5">
                    {formatTime(seg.end)}
                  </span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
