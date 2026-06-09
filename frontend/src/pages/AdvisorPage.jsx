import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Sparkles, TrendingUp, CreditCard, PieChart, Lightbulb, Trash2, Clock } from 'lucide-react'
import { advisorApi } from '../services/api'
import api from '../services/api'
import useStore from '../store/useStore'
import toast from 'react-hot-toast'

const SUGGESTIONS = [
  { icon: CreditCard,  text: 'Am I overspending anywhere this month?' },
  { icon: TrendingUp,  text: 'Which of my stocks should I be worried about?' },
  { icon: PieChart,    text: 'What is my savings rate and is it enough?' },
  { icon: Lightbulb,  text: 'Give me 3 specific ways to improve my finances' },
  { icon: TrendingUp,  text: 'Should I rebalance my portfolio right now?' },
  { icon: CreditCard,  text: 'Analyse my bank statement and find money leaks' },
]

function Message({ msg }) {
  const isUser = msg.role === 'user'
  const isThinking = msg.type === 'thinking'

  return (
    <div style={{
      display: 'flex', gap: 10,
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      animation: 'fadeUp 0.25s ease',
    }}>
      {!isUser && (
        <div style={{
          width: 30, height: 30, flexShrink: 0,
          background: 'linear-gradient(135deg, var(--gold-dim), var(--gold))',
          borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: 2,
        }}>
          <Bot size={14} color="#080c14" />
        </div>
      )}

      <div style={{
        maxWidth: '74%',
        padding: '11px 15px',
        borderRadius: isUser ? '14px 14px 3px 14px' : '14px 14px 14px 3px',
        background: isUser ? 'linear-gradient(135deg, var(--gold-dim), var(--gold))' : 'var(--bg-card)',
        border: isUser ? 'none' : '1px solid var(--bg-border)',
        color: isUser ? '#080c14' : 'var(--text-primary)',
        fontSize: '0.875rem', lineHeight: 1.65,
        fontWeight: isUser ? 500 : 400,
      }}>
        {isThinking ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-muted)' }}>
            <div style={{ display: 'flex', gap: 3 }}>
              {[0,1,2].map(i => (
                <div key={i} style={{
                  width: 5, height: 5, borderRadius: '50%', background: 'var(--gold)',
                  animation: 'pulse 1.2s ease infinite', animationDelay: `${i*0.2}s`,
                }} />
              ))}
            </div>
            <span style={{ fontSize: '0.78rem' }}>Analysing your financial data...</span>
          </div>
        ) : (
          <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
        )}
        {msg.created_at && !isThinking && (
          <div style={{ fontSize: '0.65rem', color: isUser ? 'rgba(8,12,20,0.5)' : 'var(--text-muted)', marginTop: 6 }}>
            {msg.created_at ? new Date(msg.created_at + 'Z').toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit', timeZone: 'Asia/Kolkata' }) : ''}
          </div>
        )}
      </div>

      {isUser && (
        <div style={{
          width: 30, height: 30, flexShrink: 0,
          background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
          borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', marginTop: 2,
        }}>
          <User size={13} color="var(--text-secondary)" />
        </div>
      )}
    </div>
  )
}

export default function AdvisorPage() {
  const { user } = useStore()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const [historyLoaded, setHistoryLoaded] = useState(false)
  const bottomRef = useRef()
  const inputRef = useRef()

  // Load conversation history on mount
  useEffect(() => {
    async function loadHistory() {
      try {
        const { data } = await api.get('/advisor/history')
        if (data.length > 0) {
          setMessages(data.map(m => ({ ...m, id: m.id })))
        } else {
          // Welcome message for new users
          setMessages([{
            id: 'welcome',
            role: 'assistant',
            content: `Hello ${user?.full_name?.split(' ')[0] || 'there'}! 👋 I'm your WealthPilot AI advisor.\n\nI have access to your expense history, portfolio holdings, and uploaded bank statements. Ask me anything — I'll give you specific advice based on your actual numbers.\n\nTry asking: "Am I overspending anywhere?" or "Which stock should I be worried about?"`,
          }])
        }
      } catch {
        setMessages([{
          id: 'welcome',
          role: 'assistant',
          content: `Hello! I'm your WealthPilot AI advisor. Ask me anything about your finances.`,
        }])
      } finally {
        setHistoryLoaded(true)
      }
    }
    loadHistory()
  }, [])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function clearHistory() {
    if (!confirm('Clear all conversation history?')) return
    try {
      await api.delete('/advisor/history')
      setMessages([{
        id: 'cleared',
        role: 'assistant',
        content: 'Conversation history cleared. How can I help you today?',
      }])
      toast.success('History cleared')
    } catch { toast.error('Failed to clear history') }
  }

  async function sendMessage(text) {
    const msg = text || input.trim()
    if (!msg || streaming) return
    setInput('')

    const userMsg = { id: Date.now(), role: 'user', content: msg, created_at: new Date().toISOString() }
    setMessages(prev => [...prev, userMsg])
    setStreaming(true)

    const thinkId = Date.now() + 1
    setMessages(prev => [...prev, { id: thinkId, role: 'assistant', type: 'thinking', content: '' }])

    try {
      const response = await advisorApi.chat(msg)
      if (!response.ok) throw new Error('Stream failed')

      const reader = response.body.getReader()
      const decoder = new TextDecoder()

      let assistantContent = ''
      let assistantId = Date.now() + 2
      let thinkingRemoved = false

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        const lines = chunk.split('\n').filter(l => l.startsWith('data: '))

        for (const line of lines) {
          try {
            const data = JSON.parse(line.slice(6))
            if (data.type === 'token') {
              if (!thinkingRemoved) {
                setMessages(prev => prev.filter(m => m.id !== thinkId))
                thinkingRemoved = true
              }
              assistantContent += data.content
              setMessages(prev => {
                const exists = prev.find(m => m.id === assistantId)
                if (exists) return prev.map(m => m.id === assistantId ? { ...m, content: assistantContent } : m)
                return [...prev, { id: assistantId, role: 'assistant', content: assistantContent, created_at: new Date().toISOString() }]
              })
            } else if (data.type === 'error') {
              setMessages(prev => prev.filter(m => m.id !== thinkId))
              setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: `Error: ${data.content}` }])
            }
          } catch {}
        }
      }
    } catch (err) {
      setMessages(prev => prev.filter(m => m.id !== thinkId))
      setMessages(prev => [...prev, {
        id: Date.now() + 3, role: 'assistant',
        content: 'Connection error. Make sure the backend is running with a valid Gemini API key.',
      }])
    } finally {
      setStreaming(false)
      inputRef.current?.focus()
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage() }
  }

  const showSuggestions = messages.length <= 1 && historyLoaded

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 120px)', gap: 0 }}>

      {/* Header */}
      <div className="animate-fadeUp" style={{ marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{
              width: 40, height: 40,
              background: 'linear-gradient(135deg, var(--gold-dim), var(--gold))',
              borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Bot size={20} color="#080c14" />
            </div>
            <div>
              <h1 style={{ fontSize: '1.4rem', marginBottom: 2 }}>AI Financial Advisor</h1>
              <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', display: 'flex', alignItems: 'center', gap: 5 }}>
                <Sparkles size={11} color="var(--gold)" />
                Gemini 2.5 Flash · LangGraph · Knows your actual data
              </p>
            </div>
          </div>
          <button onClick={clearHistory} className="btn btn-ghost" style={{ fontSize: '0.78rem', padding: '7px 12px', gap: 6 }}>
            <Trash2 size={13} /> Clear history
          </button>
        </div>
      </div>

      {/* Chat messages */}
      <div style={{
        flex: 1, overflow: 'auto',
        background: 'var(--bg-surface)',
        border: '1px solid var(--bg-border)',
        borderRadius: showSuggestions ? 'var(--radius-lg) var(--radius-lg) 0 0' : 'var(--radius-lg) var(--radius-lg) 0 0',
        padding: '20px 18px',
        display: 'flex', flexDirection: 'column', gap: 16,
      }}>
        {!historyLoaded ? (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', flex: 1, gap: 10, color: 'var(--text-muted)' }}>
            <div className="spinner" />
            <span style={{ fontSize: '0.85rem' }}>Loading conversation history...</span>
          </div>
        ) : (
          messages.map(msg => <Message key={msg.id} msg={msg} />)
        )}
        <div ref={bottomRef} />
      </div>

      {/* Suggestions */}
      {showSuggestions && (
        <div style={{
          background: 'var(--bg-card)',
          borderLeft: '1px solid var(--bg-border)',
          borderRight: '1px solid var(--bg-border)',
          padding: '10px 14px',
          display: 'flex', gap: 6, flexWrap: 'wrap',
        }}>
          {SUGGESTIONS.map(({ icon: Icon, text }) => (
            <button key={text} onClick={() => sendMessage(text)} style={{
              display: 'flex', alignItems: 'center', gap: 5,
              padding: '5px 10px',
              background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
              borderRadius: 99, color: 'var(--text-secondary)', fontSize: '0.75rem',
              cursor: 'pointer', transition: 'all 0.15s',
            }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold-dim)'; e.currentTarget.style.color = 'var(--gold)' }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--bg-border)'; e.currentTarget.style.color = 'var(--text-secondary)' }}
            >
              <Icon size={11} />{text}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--bg-border)', borderTop: 'none',
        borderRadius: '0 0 var(--radius-lg) var(--radius-lg)',
        padding: '14px',
        display: 'flex', gap: 8, alignItems: 'flex-end',
      }}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your expenses, portfolio, tax savings, or uploaded statement..."
          rows={1}
          style={{
            flex: 1, background: 'var(--bg-elevated)',
            border: '1px solid var(--bg-border)',
            borderRadius: 'var(--radius-md)', padding: '9px 12px',
            color: 'var(--text-primary)', fontFamily: 'var(--font-body)',
            fontSize: '0.875rem', resize: 'none', outline: 'none',
            lineHeight: 1.5, maxHeight: 100, overflowY: 'auto', transition: 'border-color 0.2s',
          }}
          onFocus={e => e.target.style.borderColor = 'var(--gold-dim)'}
          onBlur={e => e.target.style.borderColor = 'var(--bg-border)'}
          disabled={streaming}
        />
        <button onClick={() => sendMessage()} disabled={!input.trim() || streaming} style={{
          width: 38, height: 38, flexShrink: 0,
          background: (!input.trim() || streaming) ? 'var(--bg-elevated)' : 'linear-gradient(135deg, var(--gold), var(--gold-dim))',
          border: '1px solid var(--bg-border)', borderRadius: 'var(--radius-md)',
          color: (!input.trim() || streaming) ? 'var(--text-muted)' : '#080c14',
          cursor: (!input.trim() || streaming) ? 'not-allowed' : 'pointer',
          display: 'flex', alignItems: 'center', justifyContent: 'center', transition: 'all 0.2s',
        }}>
          {streaming ? <div className="spinner" style={{ width: 15, height: 15 }} /> : <Send size={15} />}
        </button>
      </div>

      <div style={{ marginTop: 6, fontSize: '0.68rem', color: 'var(--text-muted)', textAlign: 'center' }}>
        AI advisor uses your real financial data. Not financial advice — consult a SEBI-registered advisor for major decisions.
      </div>
    </div>
  )
}
