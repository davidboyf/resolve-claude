import { useState } from 'react'
import {
  MessageSquare, Film, HardDrive, LayoutGrid
} from 'lucide-react'
import { ChatPanel } from './components/ChatPanel'
import { TimelinePanel } from './components/TimelinePanel'
import { MediaPoolPanel } from './components/MediaPoolPanel'
import { StatusBar } from './components/StatusBar'
import clsx from 'clsx'

type RightTab = 'timeline' | 'media'
type Layout = 'chat' | 'split'

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
            Chat only
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

        <div className="text-[10px] text-gray-600 font-mono">
          {/* placeholder for future info */}
        </div>
      </div>

      {/* Main content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Left: Chat */}
        <div
          className={clsx(
            'flex flex-col border-r border-resolve-border overflow-hidden transition-all',
            layout === 'split' ? 'w-[55%]' : 'flex-1'
          )}
        >
          <ChatPanel />
        </div>

        {/* Right: Timeline / Media Pool */}
        {layout === 'split' && (
          <div className="flex-1 flex flex-col overflow-hidden">
            {/* Right tab bar */}
            <div className="flex items-center border-b border-resolve-border bg-resolve-panel shrink-0">
              <button
                onClick={() => setRightTab('timeline')}
                className={clsx(
                  'flex items-center gap-1.5 px-4 py-2.5 text-xs border-b-2 transition-all',
                  rightTab === 'timeline'
                    ? 'border-resolve-accent text-white'
                    : 'border-transparent text-gray-500 hover:text-gray-300'
                )}
              >
                <Film size={12} />
                Timeline
              </button>
              <button
                onClick={() => setRightTab('media')}
                className={clsx(
                  'flex items-center gap-1.5 px-4 py-2.5 text-xs border-b-2 transition-all',
                  rightTab === 'media'
                    ? 'border-resolve-accent text-white'
                    : 'border-transparent text-gray-500 hover:text-gray-300'
                )}
              >
                <HardDrive size={12} />
                Media Pool
              </button>
            </div>

            <div className="flex-1 overflow-hidden">
              {rightTab === 'timeline' ? <TimelinePanel /> : <MediaPoolPanel />}
            </div>
          </div>
        )}
      </div>

      {/* Status bar */}
      <StatusBar />
    </div>
  )
}
