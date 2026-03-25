const BASE = '/api'

export async function getStatus() {
  const res = await fetch(`${BASE}/status`)
  return res.json()
}

export async function getTimeline() {
  const res = await fetch(`${BASE}/timeline`)
  return res.json()
}

export async function getMediaPool() {
  const res = await fetch(`${BASE}/media-pool`)
  return res.json()
}

export async function addMarker(time_seconds: number, color = 'Blue', name = '', note = '') {
  const res = await fetch(`${BASE}/timeline/marker`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ time_seconds, color, name, note }),
  })
  return res.json()
}

export async function setPlayhead(time_seconds: number) {
  const res = await fetch(`${BASE}/timeline/playhead`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ time_seconds }),
  })
  return res.json()
}

export async function transcribeVideo(video_path: string, language = 'en', model_size = 'base') {
  const res = await fetch(`${BASE}/transcribe`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ video_path, language, model_size }),
  })
  return res.json()
}

export async function getRenderPresets() {
  const res = await fetch(`${BASE}/render/presets`)
  return res.json()
}

export async function startRender(preset_name: string, output_path: string) {
  const res = await fetch(`${BASE}/render/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ preset_name, output_path }),
  })
  return res.json()
}

/** Stream chat messages. Returns an EventSource-compatible async generator. */
export async function* streamChat(messages: Message[], model: string) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ messages, model }),
  })

  if (!res.body) throw new Error('No response body')

  const reader = res.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''

  while (true) {
    const { done, value } = await reader.read()
    if (done) break

    buffer += decoder.decode(value, { stream: true })
    const lines = buffer.split('\n')
    buffer = lines.pop() ?? ''

    for (const line of lines) {
      if (line.startsWith('data: ')) {
        try {
          const data = JSON.parse(line.slice(6))
          yield data
        } catch {
          // ignore parse errors
        }
      }
    }
  }
}

export interface Message {
  role: 'user' | 'assistant'
  content: string | ContentBlock[]
}

export interface ContentBlock {
  type: 'text' | 'tool_use' | 'tool_result'
  text?: string
  id?: string
  name?: string
  input?: Record<string, unknown>
  tool_use_id?: string
  content?: string
}
