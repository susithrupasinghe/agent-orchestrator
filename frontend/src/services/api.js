const BASE = import.meta.env.VITE_API_URL || ''

export async function sendMessage(message) {
  const res = await fetch(`${BASE}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ message }),
  })
  if (!res.ok) throw new Error(`POST /chat failed: ${res.status}`)
  return res.json()
}

export function openStream(sessionId, onEvent) {
  const es = new EventSource(`${BASE}/stream/${sessionId}`)
  es.onmessage = (e) => {
    try {
      const data = JSON.parse(e.data)
      onEvent(data)
      if (data.type === 'stream_end') es.close()
    } catch (_) {}
  }
  es.onerror = () => es.close()
  return es
}

export async function fetchSessions() {
  const res = await fetch(`${BASE}/sessions`)
  if (!res.ok) return []
  return res.json()
}

export async function fetchHistory(sessionId) {
  const res = await fetch(`${BASE}/history/${sessionId}`)
  if (!res.ok) return []
  return res.json()
}

export async function fetchState(sessionId) {
  const res = await fetch(`${BASE}/state/${sessionId}`)
  if (!res.ok) return null
  return res.json()
}
