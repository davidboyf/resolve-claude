import { useEffect, useState } from 'react'
import { RefreshCw, HardDrive, Film, Music, Image } from 'lucide-react'
import { getMediaPool } from '../lib/api'

interface MediaClip {
  name: string
  duration: string
  fps: string
  resolution: string
  file_path: string
  type: string
}

function getIcon(type: string) {
  if (type.toLowerCase().includes('video') || type.toLowerCase().includes('mov') || type.toLowerCase().includes('mp4')) return <Film size={13} className="text-blue-400" />
  if (type.toLowerCase().includes('audio')) return <Music size={13} className="text-green-400" />
  return <Image size={13} className="text-purple-400" />
}

export function MediaPoolPanel() {
  const [clips, setClips] = useState<MediaClip[]>([])
  const [loading, setLoading] = useState(false)
  const [search, setSearch] = useState('')

  const load = async () => {
    setLoading(true)
    try {
      const data = await getMediaPool()
      if (Array.isArray(data)) setClips(data)
    } catch {}
    setLoading(false)
  }

  useEffect(() => { load() }, [])

  const filtered = clips.filter(
    (c) =>
      c.name.toLowerCase().includes(search.toLowerCase()) ||
      c.file_path.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-resolve-border shrink-0">
        <div className="flex items-center gap-2">
          <HardDrive size={14} className="text-gray-500" />
          <span className="text-xs font-semibold text-gray-300">Media Pool</span>
          {clips.length > 0 && (
            <span className="text-[10px] text-gray-600">({clips.length})</span>
          )}
        </div>
        <button onClick={load} disabled={loading} className="p-1.5 rounded-lg text-gray-600 hover:text-gray-400 hover:bg-white/5 transition-colors disabled:opacity-50">
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="px-3 py-2 border-b border-resolve-border shrink-0">
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search clips…"
          className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-3 py-1.5 text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-resolve-accent/40"
        />
      </div>

      <div className="flex-1 overflow-y-auto p-2">
        {filtered.length === 0 ? (
          <p className="text-xs text-gray-600 text-center py-8">
            {clips.length === 0 ? 'No clips in media pool. Click refresh.' : 'No matches.'}
          </p>
        ) : (
          <div className="space-y-0.5">
            {filtered.map((clip, i) => (
              <div
                key={i}
                className="flex items-start gap-2.5 px-2.5 py-2 rounded-lg hover:bg-white/5 transition-colors group"
              >
                <div className="mt-0.5 shrink-0">{getIcon(clip.type)}</div>
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-300 truncate">{clip.name}</p>
                  <div className="flex gap-2 mt-0.5">
                    {clip.duration && (
                      <span className="text-[10px] text-gray-600">{clip.duration}</span>
                    )}
                    {clip.resolution && clip.resolution !== '?x?' && (
                      <span className="text-[10px] text-gray-600">{clip.resolution}</span>
                    )}
                    {clip.fps && (
                      <span className="text-[10px] text-gray-600">{clip.fps}fps</span>
                    )}
                  </div>
                  {clip.file_path && (
                    <p className="text-[9px] text-gray-700 truncate mt-0.5 font-mono">
                      {clip.file_path.split('/').slice(-2).join('/')}
                    </p>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
