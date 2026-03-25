import { useState } from 'react'
import { ChevronDown, ChevronRight, Zap, CheckCircle } from 'lucide-react'
import type { ChatEvent } from '../hooks/useChat'

const TOOL_LABELS: Record<string, string> = {
  get_project_info: 'Reading project info',
  get_timeline_info: 'Reading timeline',
  switch_page: 'Switching page',
  add_marker: 'Adding marker',
  delete_marker: 'Deleting marker',
  set_playhead: 'Moving playhead',
  split_clip_at: 'Splitting clip',
  delete_clips_in_range: 'Deleting clips',
  set_clip_color: 'Setting clip color',
  add_clip_to_timeline: 'Adding clip to timeline',
  get_media_pool_clips: 'Reading media pool',
  apply_color_wheel: 'Adjusting color wheel',
  set_contrast_saturation: 'Setting contrast & saturation',
  apply_lut: 'Applying LUT',
  add_serial_node: 'Adding color node',
  reset_grade: 'Resetting grade',
  set_audio_track_volume: 'Setting audio volume',
  mute_audio_track: 'Muting audio track',
  set_clip_audio_volume: 'Setting clip volume',
  get_render_presets: 'Reading render presets',
  start_render: 'Starting render',
  open_fusion_for_clip: 'Opening Fusion',
}

const TOOL_ICONS: Record<string, string> = {
  add_marker: '🔖',
  split_clip_at: '✂️',
  delete_clips_in_range: '🗑️',
  apply_color_wheel: '🎨',
  apply_lut: '🎞️',
  add_serial_node: '⬡',
  set_contrast_saturation: '⚡',
  set_audio_track_volume: '🔊',
  mute_audio_track: '🔇',
  start_render: '🚀',
  switch_page: '📄',
  open_fusion_for_clip: '✨',
  set_playhead: '▶',
  get_timeline_info: '📋',
  get_media_pool_clips: '🎬',
}

interface ToolGroupProps {
  toolName: string
  input: Record<string, unknown>
  result?: Record<string, unknown>
}

export function ToolGroup({ toolName, input, result }: ToolGroupProps) {
  const [expanded, setExpanded] = useState(false)
  const label = TOOL_LABELS[toolName] ?? toolName
  const icon = TOOL_ICONS[toolName] ?? '⚙️'
  const success = result && !result.error
  const isRead = toolName.startsWith('get_')

  return (
    <div
      className={`rounded-lg border text-xs font-mono overflow-hidden my-1 ${
        isRead
          ? 'border-resolve-border bg-resolve-panel'
          : success
          ? 'border-resolve-tool-border bg-resolve-tool'
          : 'border-red-900/50 bg-red-950/30'
      }`}
    >
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center gap-2 px-3 py-2 text-left hover:bg-white/5 transition-colors"
      >
        <span className="text-base">{icon}</span>
        <span className={`flex-1 ${isRead ? 'text-gray-400' : 'text-green-300'}`}>
          {label}
        </span>
        {result ? (
          success ? (
            <CheckCircle size={13} className="text-green-400 shrink-0" />
          ) : (
            <span className="text-red-400 text-xs">Error</span>
          )
        ) : (
          <Zap size={13} className="text-yellow-400 shrink-0 animate-pulse" />
        )}
        {expanded ? (
          <ChevronDown size={13} className="text-gray-500 shrink-0" />
        ) : (
          <ChevronRight size={13} className="text-gray-500 shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-resolve-border">
          <div className="px-3 py-2">
            <p className="text-gray-500 text-[10px] uppercase tracking-wider mb-1">Input</p>
            <pre className="text-gray-300 text-[11px] overflow-x-auto whitespace-pre-wrap">
              {JSON.stringify(input, null, 2)}
            </pre>
          </div>
          {result && (
            <div className="px-3 py-2 border-t border-resolve-border">
              <p className="text-gray-500 text-[10px] uppercase tracking-wider mb-1">Result</p>
              <pre
                className={`text-[11px] overflow-x-auto whitespace-pre-wrap ${
                  result.error ? 'text-red-400' : 'text-gray-300'
                }`}
              >
                {JSON.stringify(result, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
