import { useEffect, useState, useCallback } from 'react'
import { RefreshCw, Clock, Film, Music, Bookmark } from 'lucide-react'
import { getTimeline, setPlayhead } from '../lib/api'

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
  White: '#ffffff',
}

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
                width: `${width}%`,
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
    try {
      await setPlayhead(t)
    } catch {}
    setSeeking(false)
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
        <button
          onClick={load}
          disabled={loading}
          className="p-1.5 rounded-lg text-gray-600 hover:text-gray-400 hover:bg-white/5 transition-colors disabled:opacity-50"
        >
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
          <div className="space-y-3">
            {/* Video Tracks */}
            {data.video_tracks.length > 0 && (
              <div>
                <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-2 flex items-center gap-1">
                  <Film size={10} /> Video Tracks
                </p>
                <div className="space-y-1">
                  {data.video_tracks.map((t) => (
                    <TimelineTrack
                      key={t.track}
                      track={t}
                      type="video"
                      duration={data.duration}
                      onSeek={handleSeek}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Audio Tracks */}
            {data.audio_tracks.length > 0 && (
              <div>
                <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-2 flex items-center gap-1">
                  <Music size={10} /> Audio Tracks
                </p>
                <div className="space-y-1">
                  {data.audio_tracks.map((t) => (
                    <TimelineTrack
                      key={t.track}
                      track={t}
                      type="audio"
                      duration={data.duration}
                      onSeek={handleSeek}
                    />
                  ))}
                </div>
              </div>
            )}

            {/* Markers */}
            {data.markers.length > 0 && (
              <div>
                <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-2 flex items-center gap-1">
                  <Bookmark size={10} /> Markers ({data.markers.length})
                </p>
                <div className="space-y-1">
                  {data.markers.map((m, i) => (
                    <button
                      key={i}
                      onClick={() => handleSeek(m.time)}
                      disabled={seeking}
                      className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg bg-resolve-panel border border-resolve-border hover:border-gray-500 transition-colors text-left disabled:opacity-50"
                    >
                      <div
                        className="w-2.5 h-2.5 rounded-full shrink-0"
                        style={{ background: MARKER_COLORS[m.color] ?? '#3b82f6' }}
                      />
                      <span className="text-[10px] font-mono text-gray-500 shrink-0">
                        {formatTime(m.time)}
                      </span>
                      <span className="text-xs text-gray-300 truncate">{m.name || 'Marker'}</span>
                      {m.note && (
                        <span className="text-[10px] text-gray-600 truncate ml-auto">{m.note}</span>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Clip list */}
            {data.video_tracks.flatMap((t) => t.clips).length > 0 && (
              <div>
                <p className="text-[10px] text-gray-600 uppercase tracking-wider mb-2 flex items-center gap-1">
                  <Clock size={10} /> Clips
                </p>
                <div className="space-y-0.5">
                  {data.video_tracks.flatMap((t) =>
                    t.clips.map((clip, i) => (
                      <button
                        key={`${t.track}-${i}`}
                        onClick={() => handleSeek(clip.start)}
                        className="w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg hover:bg-white/5 transition-colors text-left group"
                      >
                        <span className="text-[10px] font-mono text-gray-600 w-10 text-right shrink-0">
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
          </div>
        )}
      </div>
    </div>
  )
}
