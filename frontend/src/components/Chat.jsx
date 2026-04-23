import React, { useState, useRef, useEffect } from 'react'

export default function Chat({ onSend, messages, isLoading }) {
  const [input, setInput] = useState('')
  const bottomRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = (e) => {
    e.preventDefault()
    const trimmed = input.trim()
    if (!trimmed || isLoading) return
    onSend(trimmed)
    setInput('')
  }

  return (
    <div className="chat-panel">
      <div className="chat-header">
        <h2>Bug / Security Reporter</h2>
        <p className="chat-subtitle">Describe your issue or paste a GitHub URL</p>
      </div>

      <div className="chat-messages">
        {messages.length === 0 && (
          <div className="chat-empty">
            Start by describing a bug or security concern. Optionally include a GitHub repo URL and file path.
          </div>
        )}
        {messages.map((msg, i) => (
          <div key={i} className={`chat-bubble ${msg.role}`}>
            <div className="bubble-role">{msg.role === 'user' ? 'You' : 'MAS'}</div>
            <div className="bubble-content" style={{ whiteSpace: 'pre-wrap' }}>
              {msg.content}
            </div>
          </div>
        ))}
        {isLoading && (
          <div className="chat-bubble assistant loading">
            <div className="bubble-role">MAS</div>
            <div className="bubble-content">
              <span className="dot-pulse">Analysing</span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      <form className="chat-form" onSubmit={handleSubmit}>
        <textarea
          className="chat-input"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Describe the issue… e.g. 'SQL injection in https://github.com/owner/repo at app/db.py'"
          rows={3}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault()
              handleSubmit(e)
            }
          }}
          disabled={isLoading}
        />
        <button
          type="submit"
          className="chat-send-btn"
          disabled={isLoading || !input.trim()}
        >
          {isLoading ? 'Running…' : 'Send'}
        </button>
      </form>
    </div>
  )
}
