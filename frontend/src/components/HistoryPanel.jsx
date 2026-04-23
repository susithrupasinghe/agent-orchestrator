import React from 'react'

function severityBadge(severity) {
  const map = { HIGH: '#ef4444', MEDIUM: '#f59e0b', LOW: '#3b82f6' }
  return (
    <span
      style={{
        background: map[severity] || '#6b7280',
        color: '#fff',
        borderRadius: 4,
        padding: '1px 6px',
        fontSize: 11,
        fontWeight: 700,
      }}
    >
      {severity}
    </span>
  )
}

function HistoryEntry({ entry, index }) {
  const toolCall = entry.tool_calls?.[0]
  const output   = entry.output || {}

  return (
    <div className="history-entry">
      <div className="history-entry-header">
        <span className="history-index">#{index + 1}</span>
        <span className="history-agent">{entry.agent}</span>
        <span className="history-ts">{new Date(entry.timestamp).toLocaleTimeString()}</span>
      </div>

      {toolCall && (
        <div className="history-tool">
          <span className="history-tool-name">⚙ {toolCall.tool}</span>
          {toolCall.output?.findings && Array.isArray(toolCall.output.findings) && (
            <div className="history-findings">
              {toolCall.output.findings.slice(0, 3).map((f, i) => (
                <div key={i} className="history-finding">
                  {severityBadge(f.severity)} {f.description} — line {f.line_number}
                </div>
              ))}
              {toolCall.output.findings.length > 3 && (
                <div className="history-finding muted">…{toolCall.output.findings.length - 3} more</div>
              )}
            </div>
          )}
          {toolCall.output?.id && (
            <div className="history-ticket">
              🎫 Ticket: <a href={toolCall.output.url} target="_blank" rel="noreferrer">{toolCall.output.id}</a>
            </div>
          )}
        </div>
      )}

      {output.next_agent && (
        <div className="history-next">→ next: {output.next_agent}</div>
      )}
    </div>
  )
}

export default function HistoryPanel({ history }) {
  return (
    <div className="history-panel">
      <div className="history-header">
        <h3>Agent Run History</h3>
        <span className="history-count">{history.length} steps</span>
      </div>
      <div className="history-list">
        {history.length === 0 ? (
          <div className="history-empty">No runs yet. Send a message to start.</div>
        ) : (
          history.map((entry, i) => (
            <HistoryEntry key={i} entry={entry} index={i} />
          ))
        )}
      </div>
    </div>
  )
}
