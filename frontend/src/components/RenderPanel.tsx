import { useState, useEffect, useCallback, useRef } from 'react'
import { RefreshCw, Play, Square, Trash2, CheckCircle, AlertCircle, Clock, Rocket } from 'lucide-react'
import { getRenderPresets, startRender } from '../lib/api'

interface RenderJob {
  job_id: string
  timeline: string
  preset: string
  output: string
  status: string
  completion: number
  error: string
}

interface RenderStatus {
  is_rendering: boolean
  job_count: number
  jobs: RenderJob[]
}

const STATUS_CONFIG: Record<string, { color: string; icon: React.ReactNode; label: string }> = {
  Ready: { color: 'text-blue-400', icon: <Clock size={12} />, label: 'Ready' },
  Rendering: { color: 'text-yellow-400', icon: <RefreshCw size={12} className="animate-spin" />, label: 'Rendering' },
  Complete: { color: 'text-green-400', icon: <CheckCircle size={12} />, label: 'Done' },
  Failed: { color: 'text-red-400', icon: <AlertCircle size={12} />, label: 'Failed' },
  Cancelled: { color: 'text-gray-500', icon: <Square size={12} />, label: 'Cancelled' },
  Unknown: { color: 'text-gray-500', icon: <Clock size={12} />, label: 'Unknown' },
}

export function RenderPanel() {
  const [presets, setPresets] = useState<string[]>([])
  const [selectedPreset, setSelectedPreset] = useState('')
  const [outputPath, setOutputPath] = useState('')
  const [status, setStatus] = useState<RenderStatus | null>(null)
  const [loading, setLoading] = useState(false)
  const [starting, setStarting] = useState(false)
  const [msg, setMsg] = useState('')
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)

  const loadPresets = useCallback(async () => {
    try {
      const data = await getRenderPresets()
      if (Array.isArray(data)) {
        setPresets(data)
        if (data.length > 0 && !selectedPreset) setSelectedPreset(data[0])
      }
    } catch {}
  }, [selectedPreset])

  const loadStatus = useCallback(async () => {
    try {
      const res = await fetch('/api/render/status')
      const data = await res.json()
      if (!data.detail) setStatus(data)
    } catch {}
  }, [])

  useEffect(() => {
    loadPresets()
    loadStatus()
  }, [])

  // Poll while rendering
  useEffect(() => {
    if (status?.is_rendering) {
      pollRef.current = setInterval(loadStatus, 2000)
    } else {
      if (pollRef.current) clearInterval(pollRef.current)
    }
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [status?.is_rendering, loadStatus])

  const handleStartRender = async () => {
    if (!selectedPreset || !outputPath.trim()) {
      setMsg('Select a preset and output path first.')
      return
    }
    setStarting(true)
    setMsg('')
    try {
      const data = await startRender(selectedPreset, outputPath)
      if (data.success) {
        setMsg('Render started!')
        loadStatus()
      } else {
        setMsg(data.detail ?? 'Failed to start render')
      }
    } catch (e) {
      setMsg(e instanceof Error ? e.message : 'Error')
    }
    setStarting(false)
  }

  const handleCancel = async () => {
    try {
      await fetch('/api/render/cancel', { method: 'POST' })
      setMsg('Render cancelled')
      loadStatus()
    } catch {}
  }

  const handleDeleteJob = async (jobId: string) => {
    try {
      await fetch(`/api/render/job/${jobId}`, { method: 'DELETE' })
      loadStatus()
    } catch {}
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-resolve-border shrink-0">
        <div className="flex items-center gap-2">
          <Rocket size={14} className="text-orange-400" />
          <span className="text-xs font-semibold text-gray-300">Render</span>
          {status?.is_rendering && (
            <span className="text-[10px] text-yellow-400 animate-pulse">● Rendering</span>
          )}
        </div>
        <button onClick={() => { loadPresets(); loadStatus() }} disabled={loading} className="p-1.5 rounded-lg text-gray-600 hover:text-gray-400 hover:bg-white/5 transition-colors disabled:opacity-50">
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-4">
        {/* New render */}
        <div className="border border-resolve-border rounded-xl p-3 space-y-3">
          <p className="text-xs font-semibold text-gray-300">New Render Job</p>

          {/* Preset */}
          <div>
            <label className="text-[10px] text-gray-500 mb-1 block">Render Preset</label>
            {presets.length === 0 ? (
              <p className="text-[10px] text-gray-600">No presets found. Open Deliver page first.</p>
            ) : (
              <select
                value={selectedPreset}
                onChange={(e) => setSelectedPreset(e.target.value)}
                className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-3 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-resolve-accent/40"
              >
                {presets.map((p) => (
                  <option key={p} value={p}>{p}</option>
                ))}
              </select>
            )}
          </div>

          {/* Output path */}
          <div>
            <label className="text-[10px] text-gray-500 mb-1 block">Output Directory</label>
            <input
              value={outputPath}
              onChange={(e) => setOutputPath(e.target.value)}
              placeholder="/Users/you/Desktop/exports"
              className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-3 py-1.5 text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-resolve-accent/40 font-mono"
            />
          </div>

          {msg && (
            <p className={`text-[10px] ${msg.includes('started') ? 'text-green-400' : 'text-red-400'}`}>{msg}</p>
          )}

          <div className="flex gap-2">
            <button
              onClick={handleStartRender}
              disabled={starting || !selectedPreset || !outputPath.trim()}
              className="flex-1 flex items-center justify-center gap-2 py-2 rounded-xl bg-orange-600/20 border border-orange-600/40 text-xs text-orange-400 hover:bg-orange-600/30 transition-colors disabled:opacity-40"
            >
              <Play size={13} />
              {starting ? 'Starting…' : 'Start Render'}
            </button>
            {status?.is_rendering && (
              <button
                onClick={handleCancel}
                className="flex items-center justify-center gap-2 px-4 py-2 rounded-xl bg-red-600/20 border border-red-600/40 text-xs text-red-400 hover:bg-red-600/30 transition-colors"
              >
                <Square size={13} />
                Stop
              </button>
            )}
          </div>
        </div>

        {/* Job queue */}
        {status && status.jobs.length > 0 && (
          <div>
            <p className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">
              Queue ({status.job_count} jobs)
            </p>
            <div className="space-y-2">
              {status.jobs.map((job) => {
                const cfg = STATUS_CONFIG[job.status] ?? STATUS_CONFIG.Unknown
                return (
                  <div
                    key={job.job_id}
                    className="border border-resolve-border rounded-xl p-3 space-y-2"
                  >
                    <div className="flex items-center gap-2">
                      <span className={cfg.color}>{cfg.icon}</span>
                      <span className="text-xs font-medium text-gray-300 flex-1 truncate">
                        {job.timeline || job.preset || 'Unnamed'}
                      </span>
                      <span className={`text-[10px] font-mono ${cfg.color}`}>{cfg.label}</span>
                      <button
                        onClick={() => handleDeleteJob(job.job_id)}
                        className="p-1 rounded text-gray-700 hover:text-red-400 transition-colors"
                      >
                        <Trash2 size={11} />
                      </button>
                    </div>

                    {job.status === 'Rendering' && (
                      <div className="space-y-1">
                        <div className="flex justify-between text-[10px] text-gray-500">
                          <span>Progress</span>
                          <span>{job.completion}%</span>
                        </div>
                        <div className="h-1.5 bg-resolve-border rounded-full overflow-hidden">
                          <div
                            className="h-full rounded-full bg-orange-500 transition-all"
                            style={{ width: `${job.completion}%` }}
                          />
                        </div>
                      </div>
                    )}

                    {job.output && (
                      <p className="text-[9px] font-mono text-gray-600 truncate">{job.output}</p>
                    )}

                    {job.error && (
                      <p className="text-[10px] text-red-400">{job.error}</p>
                    )}
                  </div>
                )
              })}
            </div>
          </div>
        )}

        {status && status.jobs.length === 0 && (
          <p className="text-xs text-gray-600 text-center py-4">No render jobs queued.</p>
        )}
      </div>
    </div>
  )
}
