import { useState, useEffect, useCallback } from 'react'
import { RefreshCw, RotateCcw, Palette, ChevronDown } from 'lucide-react'

interface WheelValues { red: number; green: number; blue: number; luma: number }
interface GradeState {
  lift: WheelValues
  gamma: WheelValues
  gain: WheelValues
  offset: WheelValues
  contrast: number
  saturation: number
}

const DEFAULT_WHEEL: WheelValues = { red: 0, green: 0, blue: 0, luma: 0 }
const DEFAULT_GRADE: GradeState = {
  lift: { ...DEFAULT_WHEEL },
  gamma: { ...DEFAULT_WHEEL },
  gain: { ...DEFAULT_WHEEL },
  offset: { ...DEFAULT_WHEEL },
  contrast: 1.0,
  saturation: 1.0,
}

const WHEEL_LABELS: Record<string, string> = {
  lift: 'Lift (Shadows)',
  gamma: 'Gamma (Mids)',
  gain: 'Gain (Highlights)',
  offset: 'Offset (All)',
}
const WHEEL_COLORS: Record<string, string> = {
  lift: '#6366f1',
  gamma: '#8b5cf6',
  gain: '#a78bfa',
  offset: '#c4b5fd',
}

function Slider({
  label,
  value,
  min,
  max,
  step = 0.01,
  color = '#5b8cf5',
  onChange,
}: {
  label: string
  value: number
  min: number
  max: number
  step?: number
  color?: string
  onChange: (v: number) => void
}) {
  const pct = ((value - min) / (max - min)) * 100
  return (
    <div className="flex items-center gap-2">
      <span className="text-[10px] text-gray-500 w-8 shrink-0 text-right">{label}</span>
      <div className="flex-1 relative h-1.5 bg-resolve-border rounded-full">
        <div
          className="absolute top-0 left-0 h-full rounded-full"
          style={{ width: `${pct}%`, background: color }}
        />
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={value}
          onChange={(e) => onChange(parseFloat(e.target.value))}
          className="absolute inset-0 w-full h-full opacity-0 cursor-pointer"
          style={{ zIndex: 2 }}
        />
        <div
          className="absolute top-1/2 -translate-y-1/2 w-3 h-3 rounded-full border-2 border-white shadow"
          style={{ left: `calc(${pct}% - 6px)`, background: color }}
        />
      </div>
      <span className="text-[10px] font-mono text-gray-400 w-10 text-right shrink-0">
        {value.toFixed(2)}
      </span>
    </div>
  )
}

function WheelSection({
  wheel,
  values,
  onChange,
}: {
  wheel: string
  values: WheelValues
  onChange: (wheel: string, channel: string, val: number) => void
}) {
  const [open, setOpen] = useState(wheel === 'gain')
  const color = WHEEL_COLORS[wheel]

  return (
    <div className="border border-resolve-border rounded-xl overflow-hidden">
      <button
        onClick={() => setOpen((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 hover:bg-white/5 transition-colors"
      >
        <div className="w-2 h-2 rounded-full shrink-0" style={{ background: color }} />
        <span className="text-xs font-medium text-gray-300 flex-1 text-left">
          {WHEEL_LABELS[wheel]}
        </span>
        <span className="text-[10px] font-mono text-gray-600">
          R{values.red >= 0 ? '+' : ''}{values.red.toFixed(2)} G{values.green >= 0 ? '+' : ''}{values.green.toFixed(2)} B{values.blue >= 0 ? '+' : ''}{values.blue.toFixed(2)}
        </span>
        <ChevronDown
          size={12}
          className={`text-gray-600 transition-transform ${open ? 'rotate-180' : ''}`}
        />
      </button>

      {open && (
        <div className="px-3 pb-3 space-y-2 border-t border-resolve-border pt-2">
          {(['red', 'green', 'blue', 'luma'] as const).map((ch) => (
            <Slider
              key={ch}
              label={ch === 'luma' ? 'Luma' : ch.charAt(0).toUpperCase()}
              value={values[ch]}
              min={-1}
              max={1}
              color={ch === 'red' ? '#ef4444' : ch === 'green' ? '#22c55e' : ch === 'blue' ? '#3b82f6' : color}
              onChange={(v) => onChange(wheel, ch, v)}
            />
          ))}
        </div>
      )}
    </div>
  )
}

export function ColorGradePanel() {
  const [track, setTrack] = useState(1)
  const [clipIndex, setClipIndex] = useState(0)
  const [grade, setGrade] = useState<GradeState>(DEFAULT_GRADE)
  const [loading, setLoading] = useState(false)
  const [applying, setApplying] = useState<string | null>(null)
  const [lutPath, setLutPath] = useState('')
  const [status, setStatus] = useState('')

  const loadGrade = useCallback(async () => {
    setLoading(true)
    setStatus('')
    try {
      const res = await fetch('/api/color/grade', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ track, clip_index: clipIndex }),
      })
      const data = await res.json()
      if (data.error) { setStatus(data.error); return }

      const parse = (v: unknown): WheelValues => {
        if (!v || typeof v !== 'object') return { ...DEFAULT_WHEEL }
        const o = v as Record<string, number>
        return { red: o.Red ?? 0, green: o.Green ?? 0, blue: o.Blue ?? 0, luma: o.Luma ?? 0 }
      }

      setGrade({
        lift: parse(data.lift),
        gamma: parse(data.gamma),
        gain: parse(data.gain),
        offset: parse(data.offset),
        contrast: data.contrast ?? 1.0,
        saturation: data.saturation ?? 1.0,
      })
      setStatus(`Loaded: ${data.clip}`)
    } catch (e) {
      setStatus('Failed to load grade')
    }
    setLoading(false)
  }, [track, clipIndex])

  const applyWheel = async (wheel: string, vals: WheelValues) => {
    setApplying(wheel)
    try {
      await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{
            role: 'user',
            content: `Apply color wheel: wheel=${wheel} red=${vals.red} green=${vals.green} blue=${vals.blue} luma=${vals.luma} track=${track} clip_index=${clipIndex}`,
          }],
          model: 'claude-sonnet-4-6',
        }),
      })
      setStatus(`Applied ${wheel}`)
    } catch {}
    setApplying(null)
  }

  const applyContrastSat = async () => {
    setApplying('cs')
    try {
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{
            role: 'user',
            content: `Set contrast=${grade.contrast} saturation=${grade.saturation} track=${track} clip_index=${clipIndex}`,
          }],
          model: 'claude-sonnet-4-6',
        }),
      })
      setStatus('Applied contrast & saturation')
    } catch {}
    setApplying(null)
  }

  const applyLUT = async () => {
    if (!lutPath.trim()) return
    setApplying('lut')
    setStatus('Applying LUT…')
    try {
      await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: `Apply LUT at path "${lutPath}" to clip at track=${track} clip_index=${clipIndex}` }],
          model: 'claude-sonnet-4-6',
        }),
      })
      setStatus('LUT applied')
    } catch {}
    setApplying(null)
  }

  const resetGrade = async () => {
    setApplying('reset')
    try {
      await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: [{ role: 'user', content: `Reset all grades on clip at track=${track} clip_index=${clipIndex}` }],
          model: 'claude-sonnet-4-6',
        }),
      })
      setGrade(DEFAULT_GRADE)
      setStatus('Grade reset')
    } catch {}
    setApplying(null)
  }

  const handleWheelChange = (wheel: string, channel: string, val: number) => {
    setGrade((prev) => ({
      ...prev,
      [wheel]: { ...(prev as Record<string, WheelValues>)[wheel], [channel]: val },
    }))
  }

  return (
    <div className="flex flex-col h-full">
      <div className="flex items-center justify-between px-4 py-2.5 border-b border-resolve-border shrink-0">
        <div className="flex items-center gap-2">
          <Palette size={14} className="text-purple-400" />
          <span className="text-xs font-semibold text-gray-300">Color Grade</span>
        </div>
        <button
          onClick={loadGrade}
          disabled={loading}
          className="p-1.5 rounded-lg text-gray-600 hover:text-gray-400 hover:bg-white/5 transition-colors disabled:opacity-50"
        >
          <RefreshCw size={13} className={loading ? 'animate-spin' : ''} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-3 space-y-3">
        {/* Clip selector */}
        <div className="flex gap-2">
          <div className="flex-1">
            <label className="text-[10px] text-gray-600 mb-1 block">Track</label>
            <input
              type="number"
              min={1}
              value={track}
              onChange={(e) => setTrack(parseInt(e.target.value) || 1)}
              className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-resolve-accent/40"
            />
          </div>
          <div className="flex-1">
            <label className="text-[10px] text-gray-600 mb-1 block">Clip Index</label>
            <input
              type="number"
              min={0}
              value={clipIndex}
              onChange={(e) => setClipIndex(parseInt(e.target.value) || 0)}
              className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-2 py-1.5 text-xs text-gray-300 focus:outline-none focus:border-resolve-accent/40"
            />
          </div>
          <div className="flex items-end">
            <button
              onClick={loadGrade}
              disabled={loading}
              className="px-3 py-1.5 rounded-lg bg-resolve-accent/20 border border-resolve-accent/30 text-xs text-resolve-accent hover:bg-resolve-accent/30 transition-colors disabled:opacity-50"
            >
              Load
            </button>
          </div>
        </div>

        {status && (
          <p className="text-[10px] text-gray-500 bg-resolve-panel border border-resolve-border rounded-lg px-3 py-1.5">
            {status}
          </p>
        )}

        {/* Color Wheels */}
        {(['lift', 'gamma', 'gain', 'offset'] as const).map((wheel) => (
          <div key={wheel}>
            <WheelSection
              wheel={wheel}
              values={grade[wheel]}
              onChange={handleWheelChange}
            />
            <button
              onClick={() => applyWheel(wheel, grade[wheel])}
              disabled={applying === wheel}
              className="w-full mt-1 py-1 rounded-lg bg-resolve-panel border border-resolve-border text-[10px] text-gray-500 hover:text-gray-300 hover:border-gray-500 transition-colors disabled:opacity-50"
            >
              {applying === wheel ? 'Applying…' : `Apply ${WHEEL_LABELS[wheel]}`}
            </button>
          </div>
        ))}

        {/* Contrast & Saturation */}
        <div className="border border-resolve-border rounded-xl p-3 space-y-3">
          <p className="text-xs font-medium text-gray-300">Contrast & Saturation</p>
          <Slider
            label="Con"
            value={grade.contrast}
            min={0}
            max={2}
            color="#f59e0b"
            onChange={(v) => setGrade((g) => ({ ...g, contrast: v }))}
          />
          <Slider
            label="Sat"
            value={grade.saturation}
            min={0}
            max={2}
            color="#ec4899"
            onChange={(v) => setGrade((g) => ({ ...g, saturation: v }))}
          />
          <button
            onClick={applyContrastSat}
            disabled={applying === 'cs'}
            className="w-full py-1.5 rounded-lg bg-resolve-panel border border-resolve-border text-[10px] text-gray-500 hover:text-gray-300 hover:border-gray-500 transition-colors disabled:opacity-50"
          >
            {applying === 'cs' ? 'Applying…' : 'Apply Contrast & Saturation'}
          </button>
        </div>

        {/* LUT */}
        <div className="border border-resolve-border rounded-xl p-3 space-y-2">
          <p className="text-xs font-medium text-gray-300">Apply LUT</p>
          <input
            value={lutPath}
            onChange={(e) => setLutPath(e.target.value)}
            placeholder="/path/to/look.cube"
            className="w-full bg-resolve-bg border border-resolve-border rounded-lg px-3 py-1.5 text-xs text-gray-300 placeholder-gray-600 focus:outline-none focus:border-resolve-accent/40 font-mono"
          />
          <button
            onClick={applyLUT}
            disabled={!lutPath.trim() || applying === 'lut'}
            className="w-full py-1.5 rounded-lg bg-resolve-panel border border-resolve-border text-[10px] text-gray-500 hover:text-gray-300 hover:border-gray-500 transition-colors disabled:opacity-50"
          >
            {applying === 'lut' ? 'Applying…' : 'Apply LUT'}
          </button>
        </div>

        {/* Reset */}
        <button
          onClick={resetGrade}
          disabled={applying === 'reset'}
          className="w-full flex items-center justify-center gap-2 py-2 rounded-xl bg-red-950/30 border border-red-900/40 text-xs text-red-400 hover:bg-red-950/50 transition-colors disabled:opacity-50"
        >
          <RotateCcw size={12} />
          {applying === 'reset' ? 'Resetting…' : 'Reset All Grades'}
        </button>
      </div>
    </div>
  )
}
