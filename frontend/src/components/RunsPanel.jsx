import React, { useState } from 'react'

const AGENT_COLORS = {
  Orchestrator: '#6366f1',
  FrontDesk:    '#06b6d4',
  GitHub:       '#8b5cf6',
  Security:     '#ef4444',
  ClickUp:      '#10b981',
}

function agentBadge(agent) {
  const color = AGENT_COLORS[agent] || '#94a3b8'
  return (
    <span style={{
      background: color + '22',
      color,
      border: `1px solid ${color}55`,
      borderRadius: 4,
      padding: '1px 7px',
      fontSize: 11,
      fontWeight: 700,
    }}>
      {agent}
    </span>
  )
}

function JsonView({ data }) {
  if (data === null || data === undefined) return <span style={{ color: '#64748b' }}>—</span>
  if (typeof data === 'string') return <span style={{ color: '#86efac' }}>{data}</span>
  return (
    <pre style={{
      margin: 0,
      whiteSpace: 'pre-wrap',
      wordBreak: 'break-word',
      fontSize: 11,
      color: '#cbd5e1',
      lineHeight: 1.5,
    }}>
      {JSON.stringify(data, null, 2)}
    </pre>
  )
}

function StageRow({ stage, index }) {
  const [open, setOpen] = useState(false)
  const toolCall = stage.tool_calls?.[0]

  return (
    <div className="stage-row" style={{ borderLeft: `3px solid ${AGENT_COLORS[stage.agent] || '#334155'}` }}>
      <div className="stage-header" onClick={() => setOpen(o => !o)} style={{ cursor: 'pointer' }}>
        <span className="stage-index">#{index + 1}</span>
        {agentBadge(stage.agent)}
        {toolCall && (
          <span className="stage-tool">⚙ {toolCall.tool}</span>
        )}
        <span className="stage-ts">{new Date(stage.timestamp).toLocaleTimeString()}</span>
        <span className="stage-chevron">{open ? '▲' : '▼'}</span>
      </div>

      {open && (
        <div className="stage-body">
          <div className="stage-section">
            <div className="stage-label">INPUT</div>
            <div className="stage-content"><JsonView data={stage.input} /></div>
          </div>

          {toolCall && (
            <div className="stage-section">
              <div className="stage-label">TOOL · {toolCall.tool}</div>
              <div className="stage-content"><JsonView data={toolCall.output} /></div>
            </div>
          )}

          <div className="stage-section">
            <div className="stage-label">OUTPUT</div>
            <div className="stage-content"><JsonView data={stage.output} /></div>
          </div>
        </div>
      )}
    </div>
  )
}

function RunDetail({ run, stages, onBack }) {
  return (
    <div className="run-detail">
      <div className="run-detail-header">
        <button className="back-btn" onClick={onBack}>← All Runs</button>
        <div className="run-detail-meta">
          <span className="run-msg-preview">{run.user_message?.slice(0, 80)}{run.user_message?.length > 80 ? '…' : ''}</span>
          <span className="run-agent-count">{stages.length} stages</span>
        </div>
      </div>
      <div className="run-stages">
        {stages.length === 0
          ? <div className="empty-msg">No stages recorded yet.</div>
          : stages.map((s, i) => <StageRow key={i} stage={s} index={i} />)
        }
      </div>
    </div>
  )
}

export default function RunsPanel({ sessions, onSelectSession, selectedSession, stages, currentSessionId }) {
  if (selectedSession) {
    return (
      <RunDetail
        run={selectedSession}
        stages={stages}
        onBack={() => onSelectSession(null)}
      />
    )
  }

  return (
    <div className="runs-list-panel">
      <div className="runs-list-header">
        <h3>All Runs</h3>
        <span className="runs-count">{sessions.length} sessions</span>
      </div>
      <div className="runs-list">
        {sessions.length === 0 ? (
          <div className="empty-msg">No runs yet.</div>
        ) : (
          sessions.map((s) => (
            <div
              key={s.session_id}
              className={`run-item ${s.session_id === currentSessionId ? 'run-item-active' : ''}`}
              onClick={() => onSelectSession(s)}
            >
              <div className="run-item-top">
                <span className="run-item-time">{new Date(s.timestamp).toLocaleTimeString()}</span>
                <span className="run-item-date">{new Date(s.timestamp).toLocaleDateString()}</span>
                <span className="run-item-stages">{s.agent_count} stages</span>
              </div>
              <div className="run-item-msg">
                {s.user_message?.slice(0, 90)}{s.user_message?.length > 90 ? '…' : ''}
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  )
}
