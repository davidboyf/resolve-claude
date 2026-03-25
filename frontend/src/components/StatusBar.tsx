import { useEffect, useState } from 'react'
import { Wifi, WifiOff, Circle } from 'lucide-react'
import { getStatus } from '../lib/api'

interface Status {
  connected: boolean
  project?: string
  timeline?: string
  fps?: number
  resolve_version?: string
  error?: string
}

export function StatusBar() {
  const [status, setStatus] = useState<Status | null>(null)

  useEffect(() => {
    const check = async () => {
      try {
        const s = await getStatus()
        setStatus(s)
      } catch {
        setStatus({ connected: false, error: 'Backend not running' })
      }
    }
    check()
    const interval = setInterval(check, 5000)
    return () => clearInterval(interval)
  }, [])

  const ok = status?.connected && status?.project

  return (
    <div className="flex items-center gap-3 px-4 py-1.5 border-t border-resolve-border bg-resolve-bg text-[10px] font-mono shrink-0">
      {/* Backend status */}
      <div className="flex items-center gap-1.5">
        {status === null ? (
          <Circle size={7} className="text-gray-600 animate-pulse" />
        ) : status.connected ? (
          <Wifi size={11} className="text-green-500" />
        ) : (
          <WifiOff size={11} className="text-red-500" />
        )}
        <span className={status?.connected ? 'text-green-500' : 'text-red-400'}>
          {status === null ? 'connecting…' : status.connected ? 'backend ok' : 'backend offline'}
        </span>
      </div>

      {status?.connected && (
        <>
          <span className="text-gray-700">|</span>
          <div className="flex items-center gap-1.5">
            <div
              className={`w-1.5 h-1.5 rounded-full ${
                ok ? 'bg-green-500' : 'bg-yellow-500'
              }`}
            />
            <span className={ok ? 'text-gray-300' : 'text-yellow-500'}>
              {ok
                ? `${status.project}`
                : 'No project open'}
            </span>
          </div>

          {status.timeline && (
            <>
              <span className="text-gray-700">|</span>
              <span className="text-gray-500">
                ⏱ {status.timeline}
                {status.fps ? ` · ${status.fps}fps` : ''}
              </span>
            </>
          )}

          {status.resolve_version && (
            <>
              <span className="text-gray-700">|</span>
              <span className="text-gray-600">
                DaVinci Resolve {status.resolve_version}
              </span>
            </>
          )}
        </>
      )}

      {status?.error && (
        <>
          <span className="text-gray-700">|</span>
          <span className="text-red-400">{status.error}</span>
        </>
      )}

      <div className="ml-auto text-gray-700">claude × resolve</div>
    </div>
  )
}
