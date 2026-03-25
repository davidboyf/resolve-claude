import { useState } from 'react'
import {
  MessageSquare, Film, HardDrive, Palette,
  Music, Rocket, Mic, LayoutGrid
} from 'lucide-react'
import { ChatPanel } from './components/ChatPanel'
import { TimelinePanel } from './components/TimelinePanel'
import { MediaPoolPanel } from './components/MediaPoolPanel'
import { ColorGradePanel } from './components/ColorGradePanel'
import { AudioMixerPanel } from './components/AudioMixerPanel'
import { RenderPanel } from './components/RenderPanel'
import { TranscribePanel } from './components/TranscribePanel'
import { StatusBar } from './components/StatusBar'
import clsx from 'clsx'

type RightTab = 'timeline' | 'media' | 'color' | 'audio' | 'render' | 'transcribe'
type Layout = 'chat' | 'split'

const RIGHT_TABS: { id: RightTab; label: string; icon: React.ReactNode; color: string }[] = [
  { id: 'timeline', label: 'Timeline', icon: <Film size={12} />, color: 'text-blue-400' },
  { id: 'media', label: 'Media', icon: <HardDrive size={12} />, color: 'text-gray-400' },
  { id: 'color', label: 'Color', icon: <Palette size={12} />, color: 'text-purple-400' },
  { id: 'audio', label: 'Audio', icon: <Music size={12} />, color: 'text-green-400' },
  { id: 'render', label: 'Render', icon: <Rocket size={12} />, color: 'text-orange-400' },
  { id: 'transcribe', label: 'Transcribe', icon: <Mic size={12} />, color: 'text-cyan-400' },
]

const LOGO = (
  <div className="flex items-center gap-2">
    <div className="w-6 h-6 rounded-md bg-gradient-to-br from-purple-600 to-indigo-700 flex items-center justify-center shadow">
      <span className="text-xs font-bold text-white">C</span>
    </div>
    <span className="text-sm font-semibold text-white tracking-tight">
      Claude <span className="text-gray-600 font-normal">× Resolve</span>
    </span>
  </div>
)

function RightPanel({ tab }: { tab: RightTab }) {
  switch (tab) {
    case 'timeline': return <TimelinePanel />
    case 'media': return <MediaPoolPanel />
    case 'color': return <ColorGradePanel />
    case 'audio': return <AudioMixerPanel />
    case 'render': return <RenderPanel />
    case 'transcribe': return <TranscribePanel />
  }
}

export default function App() {
  const [layout, setLayout] = useState<Layout>('split')
  const [rightTab, setRightTab] = useState<RightTab>('timeline')

  return (
    <div className="flex flex-col h-screen bg-resolve-bg overflow-hidden">
      {/* Top bar */}
      <div className="flex items-center justify-between px-4 h-11 border-b border-resolve-border shrink-0 bg-resolve-panel">
        {LOGO}

        <div className="flex items-center gap-1 bg-resolve-bg rounded-lg p-0.5">
          <button
            onClick={() => setLayout('chat')}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-all',
              layout === 'chat'
                ? 'bg-resolve-panel text-white shadow'
                : 'text-gray-500 hover:text-gray-300'
            )}
          >
            <MessageSquare size={12} />
            Chat
          </button>
          <button
            onClick={() => setLayout('split')}
            className={clsx(
              'flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs transition-all',
              layout === 'split'
                ? 'bg-resolve-panel text-white shadow'
                : 'text-gray-500 hover:text-gray-300'
            )}
          >
            <LayoutGrid size={12} />
            Split
          </button>
        </div>

        <div className="w-28" />
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Chat */}
        <div
          className={clsx(
            'flex flex-col border-r border-resolve-border overflow-hidden',
            layout === 'split' ? 'w-[52%]' : 'flex-1'
          )}
        >
          <ChatPanel />
        </div>

        {/* Right: Tool panels */}
        {layout === 'split' && (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Tab bar */}
            <div className="flex items-center border-b border-resolve-border bg-resolve-panel shrink-0 overflow-x-auto">
              {RIGHT_TABS.map((tab) => (
                <button
                  key={tab.id}
                  onClick={() => setRightTab(tab.id)}
                  className={clsx(
                    'flex items-center gap-1.5 px-3.5 py-2.5 text-xs border-b-2 whitespace-nowrap transition-all shrink-0',
                    rightTab === tab.id
                      ? `border-resolve-accent ${tab.color}`
                      : 'border-transparent text-gray-600 hover:text-gray-400'
                  )}
                >
                  {tab.icon}
                  {tab.label}
                </button>
              ))}
            </div>

            <div className="flex-1 overflow-hidden">
              <RightPanel tab={rightTab} />
            </div>
          </div>
        )}
      </div>

      {/* Status bar */}
      <StatusBar />
    </div>
  )
}
