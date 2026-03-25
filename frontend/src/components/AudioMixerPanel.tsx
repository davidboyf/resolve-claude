import { useState, useEffect, useCallback } from 'react'
import { RefreshCw, Volume2, VolumeX, Music } from 'lucide-react'
import { getTimeline } from '../lib/api'

interface AudioTrack {
  track: number
  clips: { name: string; start: number; end: number }[]
}

interface TrackState {
  track: number
  volume_db: number
  muted: boolean
  clipCount: number
}

const DB_MIN = -60
const DB_MAX = 12
const DB_UNITY = 0

function dbToPercent(db: number) {
  return ((db - DB_MIN) / (DB_MAX - DB_MIN)) * 100
}

function VUMeter({ db, muted }: { db: number; muted: boolean }) {
  const pct = dbToPercent(db)
  const color =
    db > 0 ? '#ef4444' : db > -6 ? '#f59e0b' : '#22c55e'

  return (
    <div className="relative w-2 h-16 bg-resolve-border rounded-full overflow-hidden">
      {!muted && (
        <div
          className="absolute bottom-0 left-0 right-0 rounded-full transition-all duration-100"
          style={{ height: `${Math.max(2, pct)}%`, background: color }}
        />
      )}
    </div>
  )
}

function TrackStrip({
  state,
  onVolumeChange,
  onMuteToggle,
  onApply,
  applying,
}: {
  state: TrackState
  onVolumeChange: (track: number, db: number) => void
  onMuteToggle: (track: number) => void
  onApply: (track: number) => void
  applying: boolean
}) {
  return (
    <div
      className={`flex flex-col items-center gap-2 px-3 py-3 rounded-xl border transition-all ${
        state.muted
          ? 'border-resolve-border bg-resolve-panel opacity-60'
          : 'border-resolve-border bg-resolve-panel hover:border-gray-600'
      }`}
      style={{ minWidth: 64 }}
    >
      <span className="text-[10px] text-gray-500 font-mono">A{state.track}</span>
      <span className="text-[9px] text-gray-600">{state.clipCount} clips</span>

      <VUMeter db={state.volume_db} muted={state.muted} />

      {/* Volume slider (vertical) */}
      <div className="relative h-20 flex items-center justify-center" style={{ writingMode: 'vertical-lr' }}>
        <input
          type="range"
          min={DB_MIN}
          max={DB_MAX}
          step={0.5}
          value={state.volume_db}
          onChange={(e) => onVolumeChange(state.track, parseFloat(e.target.value))}
          className="appearance-none cursor-pointer"
          style={{
            writingMode: 'vertical-lr',
            direction: 'rtl',
            width: 4,
            height: 80,
            background: `linear-gradient(to top, #5b8cf5 ${dbToPercent(state.volume_db)}%, #2a2a30 ${dbToPercent(state.volume_db)}%)`,
            borderRadius: 4,
            outline: 'none',
            WebkitAppearance: 'slider-vertical',
          }}
        />
      </div>

      <span
        className={`text-[10px] font-mono ${
          state.volume_db > 0 ? 'text-red-400' : state.volume_db === 0 ? 'text-green-400' : 'text-gray-400'
        }`}
      >
        {state.volume_db >= 0 ? '+' : ''}{state.volume_db.toFixed(1)}
      </span>

      {/* Mute */}
      <button
        onClick={() => onMuteToggle(state.track)}
        className={`w-8 h-6 rounded-md flex items-center justify-center text-xs transition-all ${
          state.muted
            ? 'bg-red-600/30 border border-red-600/50 text-red-400'
            : 'bg-resolve-bg border border-resolve-border text-gray-400 hover:border-gray-500'
        }`}
        title={state.muted ? 'Unmute' : 'Mute'}
      >
        {state.muted ? <VolumeX size={11} /> : <Volume2 size={11} />}
      </button>

      {/* Apply */}
      <button
        onClick={() => onApply(state.track)}
        disabled={applying}
        className="px-2 py-0.5 rounded-md bg-resolve-accent/20 border border-resolve-accent/30 text-[9px] text-resolve-accent hover:bg-resolve-accent/30 transition-colors disabled:opacity-50"
      >
        {applying ? '…' : 'Set'}
      </button>
    </div>
  )
}

export function AudioMixerPanel() {
  const [tracks, setTracks] = useState<TrackState[]>([])
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState<number | null>(null)
  const [status, setStatus] = useState('')

  const load = useCallback(async () => {
    setLoading(true)
    try {
      const data = await getTimeline()
      if (data.audio_tracks) {
        const t: TrackState[] = (data.audio_tracks as AudioTrack[]).map((at) => ({
          track: at.track,
          volume_db: DB_UNITY,
          muted: false,
          clipCount: at.clips.length,
        }))
        setTracks(t)
      }
    } catch {}
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const handleVolumeChange = (track: number, db: number) => {
    setTracks((prev) => prev.map((t) => (t.track === track ? { ...t, volume_db: db } : t)))
  }

  const handleMuteToggle = (track: number) => {
    setTracks((prev) => prev.map((t) => (t.track === track ? { ...t, muted: !t.muted } : t)))
  }

  const handleApply = async (track: number) => {
    const t = tracks.find((x) => x.track === track)
    if (!t) return
    setApplying(track)
    try {
      if (t.muted) {
        await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            messages: [{ role: 'user', content: `Mute audio track ${track}` }],
            model: 'claude-sonnet-4-6',
          }),
        })
      } else {
        await fetch('/api/chat', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            messages: [{ role: 'user', content: `Set audio track ${track} volume to ${t.volume_db} dB` }],
            model: 'claude-sonnet-4-6',
          }),
        })
      }
      setStatus(`Track ${track}: ${t.muted ? 'muted' : `${t.volume_db}dB`}`)
    } catch {}
    setApplying(null)
  }

  const applyAll = async () => {
    for (const t of tracks) {
      await handleApply(t.track)
    }
    setStatus('All tracks updated')
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-resolve-border shrink-0">
        <div className="flex items-center gap-2">
          <Music size={14} className="text-green-400" />
          <span className="text-xs font-semibold text-gray-300">Audio Mixer</span>
          {tracks.length > 0 && (
            <span className="text-[10px] text-gray-600">({tracks.length} tracks)</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          {tracks.length > 0 && (
            <button
              onClick={applyAll}
              className="px-2.5 py-1 rounded-lg bg-resolve-accent/20 border border-resolve-accent/30 text-[10px] text-resolve-accent hover:bg-resolve-accent/30 transition-colors"
            >
              Apply All
            </button>
          )}
          <button onClick={load} disabled={loading} className="p-1.5 rounded-lg text-gray-600 hover:text-gray-400 hover:bg-white/5 transition-colors disabled:opacity-50">
            <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
          </button>
        </div>
      </div>

      {status && (
        <div className="px-4 py-1.5 border-b border-resolve-border">
          <p className="text-[10px] text-gray-500">{status}</p>
        </div>
      )}

      <div className="flex-1 overflow-x-auto overflow-y-hidden">
        {tracks.length === 0 ? (
          <div className="flex items-center justify-center h-full">
            <p className="text-xs text-gray-600">No audio tracks found. Click refresh.</p>
          </div>
        ) : (
          <div className="flex gap-3 p-4 h-full items-start">
            {/* dB scale */}
            <div className="flex flex-col justify-between h-full pt-12 pb-8 shrink-0">
              {[DB_MAX, 6, 0, -6, -12, -24, -48, DB_MIN].map((db) => (
                <span key={db} className="text-[9px] font-mono text-gray-700 text-right w-6">
                  {db}
                </span>
              ))}
            </div>

            {tracks.map((t) => (
              <TrackStrip
                key={t.track}
                state={t}
                onVolumeChange={handleVolumeChange}
                onMuteToggle={handleMuteToggle}
                onApply={handleApply}
                applying={applying === t.track}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
