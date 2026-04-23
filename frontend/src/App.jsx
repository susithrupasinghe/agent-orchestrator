import React, { useState, useCallback, useRef, useEffect } from 'react'
import Chat from './components/Chat.jsx'
import FlowGraph from './components/FlowGraph.jsx'
import RunsPanel from './components/RunsPanel.jsx'
import { sendMessage, openStream, fetchSessions, fetchHistory } from './services/api.js'

export default function App() {
  const [messages, setMessages]             = useState([])
  const [isLoading, setIsLoading]           = useState(false)
  const [activeAgent, setActiveAgent]       = useState(null)
  const [doneAgents, setDoneAgents]         = useState([])
  const [currentSessionId, setCurrentSid]  = useState(null)

  // Runs panel state
  const [sessions, setSessions]             = useState([])
  const [selectedSession, setSelectedSess] = useState(null)
  const [selectedStages, setSelectedStages] = useState([])

  const esRef = useRef(null)

  // Poll sessions list
  const refreshSessions = useCallback(async () => {
    const list = await fetchSessions()
    setSessions(list)
  }, [])

  useEffect(() => {
    refreshSessions()
  }, [])

  const handleSelectSession = useCallback(async (session) => {
    if (!session) {
      setSelectedSess(null)
      setSelectedStages([])
      return
    }
    setSelectedSess(session)
    const stages = await fetchHistory(session.session_id)
    setSelectedStages(stages)
  }, [])

  const handleSend = useCallback(async (text) => {
    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setIsLoading(true)
    setActiveAgent(null)
    setDoneAgents([])
    if (esRef.current) esRef.current.close()

    try {
      const { session_id } = await sendMessage(text)
      setCurrentSid(session_id)
      await refreshSessions()

      const es = openStream(session_id, async (event) => {
        if (event.type === 'agent_start') {
          setActiveAgent(event.agent)
        }

        if (event.type === 'agent_end') {
          setDoneAgents((prev) =>
            prev.includes(event.agent) ? prev : [...prev, event.agent]
          )
          await refreshSessions()
          // If user is viewing this session in the runs panel, refresh its stages too
          if (selectedSession?.session_id === session_id) {
            const stages = await fetchHistory(session_id)
            setSelectedStages(stages)
          }
        }

        if (event.type === 'done') {
          setActiveAgent(null)
          setIsLoading(false)
          setMessages((prev) => [
            ...prev,
            { role: 'assistant', content: event.final_response || 'Analysis complete.' },
          ])
          await refreshSessions()
          es.close()
        }

        if (event.type === 'stream_end') {
          setIsLoading(false)
          setActiveAgent(null)
        }
      })

      esRef.current = es
    } catch (err) {
      setIsLoading(false)
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: `Error: ${err.message}` },
      ])
    }
  }, [selectedSession, refreshSessions])

  return (
    <div className="app-layout">
      <header className="app-header">
        <span className="app-logo">⚡ MAS</span>
        <span className="app-title">Multi-Agent Bug &amp; Security Analysis System</span>
        {currentSessionId && (
          <span className="app-session">Session: {currentSessionId.slice(0, 8)}…</span>
        )}
      </header>

      <div className="main-content">
        <Chat onSend={handleSend} messages={messages} isLoading={isLoading} />
        <FlowGraph activeAgent={activeAgent} doneAgents={doneAgents} />
      </div>

      <div className="bottom-panel">
        <RunsPanel
          sessions={sessions}
          currentSessionId={currentSessionId}
          onSelectSession={handleSelectSession}
          selectedSession={selectedSession}
          stages={selectedStages}
        />
      </div>
    </div>
  )
}
