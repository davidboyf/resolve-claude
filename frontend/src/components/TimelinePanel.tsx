import { useEffect, useState, useCallback } from 'react'
import { RefreshCw, Clock, Film, Music, Bookmark, Plus, Trash2, Pencil, Check, X } from 'lucide-react'
import { getTimeline, setPlayhead, addMarker } from '../lib/api'

interface Clip {
  name: string
  start: number
  end: number
  duration: number
  clip_color?: string
}

interface Track {
  track: number
  clips: Clip[]
}

interface Marker {
  frame: number
  time: number
  color: string
  name: string
  note: string
}

interface TimelineData {
  name: string
  fps: number
  duration: number
  video_tracks: Track[]
  audio_tracks: Track[]
  markers: Marker[]
}

const MARKER_COLORS: Record<string, string> = {
  Red: '#ef4444',
  Green: '#22c55e',
  Blue: '#3b82f6',
  Cyan: '#06b6d4',
  Magenta: '#d946ef',
  Yellow: '#eab308',
  White: '#e5e7eb',
}

const COLOR_OPTIONS = Object.keys(MARKER_COLORS)

function formatTime(s: number) {
  const m = Math.floor(s / 60)
  const sec = (s % 60).toFixed(1)
  return `${m}:${sec.padStart(4, '0')}`
}

function TimelineTrack({
  track,
  type,
  duration,
  onSeek,
}: {
  track: Track
  type: 'video' | 'audio'
  duration: number
  onSeek: (t: number) => void
}) {
  if (duration === 0) return null
  return (
    <div className="flex items-center gap-2 h-8">
      <span className="text-[10px] text-gray-600 w-14 text-right shrink-0">
        {type === 'video' ? 'V' : 'A'}{track.track}
      </span>
      <div className="flex-1 relative h-full bg-resolve-border/20 rounded overflow-hidden">
        {track.clips.map((clip, i) => {
          const left = (clip.start / duration) * 100
          const width = ((clip.end - clip.start) / duration) * 100
          return (
            <div
              key={i}
              className="absolute top-1 bottom-1 rounded cursor-pointer hover:opacity-80 transition-opacity flex items-center overflow-hidden"
              style={{
                left: `${left}%`,
                width: `${Math.max(width, 0.3)}%`,
                minWidth: 2,
                background: type === 'video' ? '#3d63c9' : '#166534',
                border: `1px solid ${type === 'video' ? '#5b8cf5' : '#22c55e'}`,
              }}
              onClick={() => onSeek(clip.start)}
              title={`${clip.name} — ${formatTime(clip.start)} → ${formatTime(clip.end)}`}
            >
              <span className="px-1 text-[9px] text-white/80 truncate leading-none">
                {clip.name}
              </span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

interface EditingMarker {
  time: number
  name: string
  color: string
  note: string
}

function MarkerRow({
  marker,
  onSeek,
  onDelete,
  onUpdate,
}: {
  marker: Marker
  onSeek: (t: number) => void
  onDelete: (t: number) => void
  onUpdate: (old: Marker, updated: EditingMarker) => void
}) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState<EditingMarker>({
    time: marker.time,
    name: marker.name,
    color: marker.color,
    note: marker.note,
  })

  const save = () => {
    onUpdate(marker, draft)
    setEditing(false)
  }
  const cancel = () => {
    setDraft({ time: marker.time, name: marker.name, color: marker.color, note: marker.note })
    setEditing(false)
  }

  if (editing) {
    return (
      <div className="border border-resolve-accent/40 rounded-xl p-2.5 space-y-2 bg-resolve-panel animate-fade-in">
        <div className="flex gap-2">
          <input
            value={draft.name}
            onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
            placeholder="Marker name"
            className="flex-1 bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1 text-xs text-gray-300 focus:outline-none focus:border-resolve-accent/40"
          />
          <select
            value={draft.color}
            onChange={(e) => setDraft((d) => ({ ...d, color: e.target.value }))}
            className="bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1 text-xs text-gray-300 focus:outline-none"
          >
            {COLOR_OPTIONS.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </div>
        <input
          value={draft.note}
          onChange={(e) => setDraft((d) => ({ ...d, note: e.target.value }))}
          placeholder="Note (optional)"
          className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1 text-xs text-gray-400 focus:outline-none focus:border-resolve-accent/40"
        />
        <div className="flex gap-2">
          <button onClick={save} className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-green-600/20 border border-green-600/40 text-xs text-green-400 hover:bg-green-600/30 transition-colors">
            <Check size={11} /> Save
          </button>
          <button onClick={cancel} className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-resolve-bg border border-resolve-border text-xs text-gray-500 hover:text-gray-300 transition-colors">
            <X size={11} /> Cancel
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg hover:bg-white/5 transition-colors group">
      <button onClick={() => onSeek(marker.time)} className="flex items-center gap-2.5 flex-1 text-left min-w-0">
        <div
          className="w-2.5 h-2.5 rounded-full shrink-0"
          style={{ background: MARKER_COLORS[marker.color] ?? '#3b82f6' }}
        />
        <span className="text-[10px] font-mono text-gray-500 shrink-0 tabular-nums">
          {formatTime(marker.time)}
        </span>
        <span className="text-xs text-gray-300 truncate">{marker.name || 'Marker'}</span>
        {marker.note && (
          <span className="text-[10px] text-gray-600 truncate">{marker.note}</span>
        )}
      </button>
      <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity shrink-0">
        <button
          onClick={() => setEditing(true)}
          className="p-1 rounded text-gray-600 hover:text-gray-300 transition-colors"
          title="Edit marker"
        >
          <Pencil size={11} />
        </button>
        <button
          onClick={() => onDelete(marker.time)}
          className="p-1 rounded text-gray-600 hover:text-red-400 transition-colors"
          title="Delete marker"
        >
          <Trash2 size={11} />
        </button>
      </div>
    </div>
  )
}

function AddMarkerRow({ onAdd }: { onAdd: (m: EditingMarker) => void }) {
  const [open, setOpen] = useState(false)
  const [draft, setDraft] = useState<EditingMarker>({ time: 0, name: '', color: 'Blue', note: '' })

  const save = () => {
    onAdd(draft)
    setDraft({ time: 0, name: '', color: 'Blue', note: '' })
    setOpen(false)
  }

  if (!open) {
    return (
      <button
        onClick={() => setOpen(true)}
        className="w-full flex items-center gap-2 px-2.5 py-1.5 rounded-lg border border-dashed border-resolve-border text-xs text-gray-600 hover:text-gray-400 hover:border-gray-500 transition-all"
      >
        <Plus size={11} /> Add marker
      </button>
    )
  }

  return (
    <div className="border border-resolve-border rounded-xl p-2.5 space-y-2 bg-resolve-panel animate-fade-in">
      <div className="flex gap-2">
        <input
          type="number"
          value={draft.time}
          onChange={(e) => setDraft((d) => ({ ...d, time: parseFloat(e.target.value) || 0 }))}
          placeholder="Time (s)"
          className="w-20 bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1 text-xs text-gray-300 focus:outline-none focus:border-resolve-accent/40 font-mono"
        />
        <input
          value={draft.name}
          onChange={(e) => setDraft((d) => ({ ...d, name: e.target.value }))}
          placeholder="Label"
          className="flex-1 bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1 text-xs text-gray-300 focus:outline-none focus:border-resolve-accent/40"
        />
        <select
          value={draft.color}
          onChange={(e) => setDraft((d) => ({ ...d, color: e.target.value }))}
          className="bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1 text-xs text-gray-300 focus:outline-none"
        >
          {COLOR_OPTIONS.map((c) => (
            <option key={c} value={c}>{c}</option>
          ))}
        </select>
      </div>
      <input
        value={draft.note}
        onChange={(e) => setDraft((d) => ({ ...d, note: e.target.value }))}
        placeholder="Note (optional)"
        className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1 text-xs text-gray-400 focus:outline-none focus:border-resolve-accent/40"
      />
      <div className="flex gap-2">
        <button onClick={save} className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-blue-600/20 border border-blue-600/40 text-xs text-blue-400 hover:bg-blue-600/30 transition-colors">
          <Plus size={11} /> Add
        </button>
        <button onClick={() => setOpen(false)} className="flex items-center gap-1 px-2.5 py-1 rounded-lg bg-resolve-bg border border-resolve-border text-xs text-gray-500 hover:text-gray-300 transition-colors">
          <X size={11} /> Cancel
        </button>
      </div>
    </div>
  )
}

export function TimelinePanel() {
  const [data, setData] = useState<TimelineData | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [seeking, setSeeking] = useState(false)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const d = await getTimeline()
      if (d.detail) setError(d.detail)
      else setData(d)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to load timeline')
    }
    setLoading(false)
  }, [])

  useEffect(() => { load() }, [load])

  const handleSeek = async (t: number) => {
    setSeeking(true)
    try { await setPlayhead(t) } catch {}
    setSeeking(false)
  }

  const handleAddMarker = async (m: EditingMarker) => {
    await addMarker(m.time, m.color, m.name, m.note)
    load()
  }

  const handleDeleteMarker = async (time: number) => {
    try {
      await fetch('/api/timeline/marker/delete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ time_seconds: time }),
      })
    } catch {}
    load()
  }

  const handleUpdateMarker = async (old: Marker, updated: EditingMarker) => {
    // Delete old, add new
    await handleDeleteMarker(old.time)
    await handleAddMarker(updated)
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-resolve-border shrink-0">
        <div className="flex items-center gap-2">
          <Film size={14} className="text-gray-500" />
          <span className="text-xs font-semibold text-gray-300">
            {data?.name ?? 'Timeline'}
          </span>
          {data && (
            <span className="text-[10px] text-gray-600 font-mono">
              {formatTime(data.duration)} · {data.fps}fps
            </span>
          )}
        </div>
        <button onClick={load} disabled={loading} className="p-1.5 rounded-lg text-gray-600 hover:text-gray-400 hover:bg-white/5 transition-colors disabled:opacity-50">
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3">
        {error && (
          <div className="text-xs text-red-400 bg-red-950/30 border border-red-900/50 rounded-lg p-3">
            {error}
          </div>
        )}

        {!data && !error && !loading && (
          <p className="text-xs text-gray-600 text-center py-8">
            Open a project in DaVinci Resolve and click refresh.
          </p>
        )}

        {data && (
          <div className="space-y-4">
            {/* Visual timeline */}
            {(data.video_tracks.length > 0 || data.audio_tracks.length > 0) && (
              <div className="space-y-1">
                {data.video_tracks.map((t) => (
                  <TimelineTrack key={`v${t.track}`} track={t} type="video" duration={data.duration} onSeek={handleSeek} />
                ))}
                {data.audio_tracks.map((t) => (
                  <TimelineTrack key={`a${t.track}`} track={t} type="audio" duration={data.duration} onSeek={handleSeek} />
                ))}
              </div>
            )}

            {/* Markers section */}
            <div>
              <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-2 flex items-center gap-1">
                <Bookmark size={10} /> Markers ({data.markers.length})
              </p>
              <div className="space-y-0.5">
                {data.markers.map((m, i) => (
                  <MarkerRow
                    key={i}
                    marker={m}
                    onSeek={handleSeek}
                    onDelete={handleDeleteMarker}
                    onUpdate={handleUpdateMarker}
                  />
                ))}
                <AddMarkerRow onAdd={handleAddMarker} />
              </div>
            </div>

            {/* Clip list */}
            {data.video_tracks.flatMap((t) => t.clips).length > 0 && (
              <div>
                <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-2 flex items-center gap-1">
                  <Clock size={10} /> Clips ({data.video_tracks.flatMap((t) => t.clips).length})
                </p>
                <div className="space-y-0.5">
                  {data.video_tracks.flatMap((t) =>
                    t.clips.map((clip, i) => (
                      <button
                        key={`${t.track}-${i}`}
                        onClick={() => handleSeek(clip.start)}
                        disabled={seeking}
                        className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg hover:bg-white/5 transition-colors text-left group disabled:opacity-50"
                      >
                        <span className="text-[10px] font-mono text-gray-600 w-10 text-right shrink-0 tabular-nums">
                          {formatTime(clip.start)}
                        </span>
                        <div className="w-1 h-1 rounded-full bg-resolve-accent/50 shrink-0" />
                        <span className="text-xs text-gray-400 group-hover:text-gray-200 truncate transition-colors">
                          {clip.name}
                        </span>
                        <span className="text-[10px] text-gray-600 ml-auto shrink-0">
                          {formatTime(clip.duration)}
                        </span>
                      </button>
                    ))
                  )}
                </div>
              </div>
            )}

            {/* Audio tracks list */}
            {data.audio_tracks.length > 0 && (
              <div>
                <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-2 flex items-center gap-1">
                  <Music size={10} /> Audio ({data.audio_tracks.length} tracks)
                </p>
                {data.audio_tracks.map((t) => (
                  <div key={t.track} className="flex items-center gap-2 px-2.5 py-1 text-xs text-gray-600">
                    <span className="font-mono w-6">A{t.track}</span>
                    <span>{t.clips.length} clips</span>
                  </div>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  )
}
