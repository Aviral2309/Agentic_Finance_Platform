import { useState, useRef, useEffect } from 'react'
import { Send, Bot, User, Sparkles, TrendingUp, CreditCard, PieChart, Lightbulb } from 'lucide-react'
import { advisorApi } from '../services/api'
import useStore from '../store/useStore'

const SUGGESTIONS = [
  { icon: CreditCard,  text: 'Am I spending too much on food this month?' },
  { icon: TrendingUp,  text: 'Should I rebalance my portfolio?' },
  { icon: PieChart,    text: 'What is my savings rate this month?' },
  { icon: Lightbulb,   text: 'How can I reduce my tax burden?' },
]

function Message({ msg }) {
  const isUser = msg.role === 'user'
  const isThinking = msg.type === 'thinking'

  return (
    <div style={{
      display: 'flex',
      gap: 12,
      justifyContent: isUser ? 'flex-end' : 'flex-start',
      animation: 'fadeUp 0.3s ease',
    }}>
      {!isUser && (
        <div style={{
          width: 32, height: 32, flexShrink: 0,
          background: 'linear-gradient(135deg, var(--gold-dim), var(--gold))',
          borderRadius: '50%',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginTop: 2,
        }}>
          <Bot size={16} color="#080c14" />
        </div>
      )}

      <div style={{
        maxWidth: '72%',
        padding: isThinking ? '10px 16px' : '12px 16px',
        borderRadius: isUser ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
        background: isUser
          ? 'linear-gradient(135deg, var(--gold-dim), var(--gold))'
          : 'var(--bg-card)',
        border: isUser ? 'none' : '1px solid var(--bg-border)',
        color: isUser ? '#080c14' : 'var(--text-primary)',
        fontSize: '0.875rem',
        lineHeight: 1.65,
        fontWeight: isUser ? 500 : 400,
      }}>
        {isThinking ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--text-muted)' }}>
            <div style={{ display: 'flex', gap: 4 }}>
              {[0, 1, 2].map(i => (
                <div key={i} style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: 'var(--gold)',
                  animation: 'pulse 1.2s ease infinite',
                  animationDelay: `${i * 0.2}s`,
                }} />
              ))}
            </div>
            <span style={{ fontSize: '0.8rem' }}>Analyzing your financial data...</span>
          </div>
        ) : (
          <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
        )}
      </div>

      {isUser && (
        <div style={{
          width: 32, height: 32, flexShrink: 0,
          background: 'var(--bg-elevated)',
          border: '1px solid var(--bg-border)',
          borderRadius: '50%',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          marginTop: 2,
        }}>
          <User size={15} color="var(--text-secondary)" />
        </div>
      )}
    </div>
  )
}

export default function AdvisorPage() {
  const { user } = useStore()
  const [messages, setMessages] = useState([
    {
      id: 'welcome',
      role: 'assistant',
      content: `Hello ${user?.full_name?.split(' ')[0] || 'there'}! 👋 I'm your WealthPilot financial advisor.\n\nI have access to your expense history, portfolio holdings, and financial knowledge base. Ask me anything about your money — I'll give you specific, data-driven advice based on your actual numbers.\n\nWhat would you like to know?`,
    }
  ])
  const [input, setInput] = useState('')
  const [streaming, setStreaming] = useState(false)
  const bottomRef = useRef()
  const inputRef = useRef()

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  async function sendMessage(text) {
    const msg = text || input.trim()
    if (!msg || streaming) return
    setInput('')

    // Add user message
    const userMsg = { id: Date.now(), role: 'user', content: msg }
    setMessages(prev => [...prev, userMsg])
    setStreaming(true)

    // Add thinking indicator
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

            if (data.type === 'thinking' && !thinkingRemoved) {
              // Keep thinking indicator
            } else if (data.type === 'token') {
              if (!thinkingRemoved) {
                // Replace thinking with first token
                setMessages(prev => prev.filter(m => m.id !== thinkId))
                thinkingRemoved = true
              }
              assistantContent += data.content
              setMessages(prev => {
                const exists = prev.find(m => m.id === assistantId)
                if (exists) {
                  return prev.map(m => m.id === assistantId ? { ...m, content: assistantContent } : m)
                }
                return [...prev, { id: assistantId, role: 'assistant', content: assistantContent }]
              })
            } else if (data.type === 'done') {
              break
            } else if (data.type === 'error') {
              setMessages(prev => prev.filter(m => m.id !== thinkId))
              setMessages(prev => [...prev, { id: assistantId, role: 'assistant', content: `Sorry, I encountered an error: ${data.content}` }])
            }
          } catch {}
        }
      }
    } catch (err) {
      setMessages(prev => prev.filter(m => m.id !== thinkId))
      setMessages(prev => [...prev, {
        id: Date.now() + 3,
        role: 'assistant',
        content: 'Sorry, I had trouble connecting. Make sure your backend is running and Gemini API key is set.',
      }])
    } finally {
      setStreaming(false)
      inputRef.current?.focus()
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage()
    }
  }

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: 'calc(100vh - 64px - 56px)',
      maxHeight: 800,
      gap: 0,
    }}>

      {/* Header */}
      <div className="animate-fadeUp" style={{ marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <div style={{
            width: 44, height: 44,
            background: 'linear-gradient(135deg, var(--gold-dim), var(--gold))',
            borderRadius: 12,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Bot size={22} color="#080c14" />
          </div>
          <div>
            <h1 style={{ fontSize: '1.5rem', marginBottom: 2 }}>AI Financial Advisor</h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', display: 'flex', alignItems: 'center', gap: 6 }}>
              <Sparkles size={12} color="var(--gold)" />
              Powered by LangGraph + Gemini · Knows your actual financial data
            </p>
          </div>
        </div>
      </div>

      {/* Chat area */}
      <div style={{
        flex: 1, overflow: 'auto',
        background: 'var(--bg-surface)',
        border: '1px solid var(--bg-border)',
        borderRadius: 'var(--radius-lg) var(--radius-lg) 0 0',
        padding: '24px 20px',
        display: 'flex', flexDirection: 'column', gap: 20,
      }}>
        {messages.map(msg => <Message key={msg.id} msg={msg} />)}
        <div ref={bottomRef} />
      </div>

      {/* Suggestions */}
      {messages.length <= 1 && (
        <div style={{
          background: 'var(--bg-card)',
          borderLeft: '1px solid var(--bg-border)',
          borderRight: '1px solid var(--bg-border)',
          padding: '12px 16px',
          display: 'flex', gap: 8, flexWrap: 'wrap',
        }}>
          {SUGGESTIONS.map(({ icon: Icon, text }) => (
            <button
              key={text}
              onClick={() => sendMessage(text)}
              style={{
                display: 'flex', alignItems: 'center', gap: 6,
                padding: '6px 12px',
                background: 'var(--bg-elevated)',
                border: '1px solid var(--bg-border)',
                borderRadius: 99,
                color: 'var(--text-secondary)',
                fontSize: '0.78rem', cursor: 'pointer',
                transition: 'all 0.15s',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor='var(--gold-dim)'; e.currentTarget.style.color='var(--gold)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor='var(--bg-border)'; e.currentTarget.style.color='var(--text-secondary)'; }}
            >
              <Icon size={12} />
              {text}
            </button>
          ))}
        </div>
      )}

      {/* Input */}
      <div style={{
        background: 'var(--bg-card)',
        border: '1px solid var(--bg-border)',
        borderTop: 'none',
        borderRadius: '0 0 var(--radius-lg) var(--radius-lg)',
        padding: '16px 16px',
        display: 'flex', gap: 10, alignItems: 'flex-end',
      }}>
        <textarea
          ref={inputRef}
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Ask about your expenses, portfolio, tax savings, or financial goals..."
          rows={1}
          style={{
            flex: 1,
            background: 'var(--bg-elevated)',
            border: '1px solid var(--bg-border)',
            borderRadius: 'var(--radius-md)',
            padding: '10px 14px',
            color: 'var(--text-primary)',
            fontFamily: 'var(--font-body)',
            fontSize: '0.875rem',
            resize: 'none',
            outline: 'none',
            lineHeight: 1.5,
            maxHeight: 120,
            overflowY: 'auto',
            transition: 'border-color 0.2s',
          }}
          onFocus={e => e.target.style.borderColor='var(--gold-dim)'}
          onBlur={e => e.target.style.borderColor='var(--bg-border)'}
          disabled={streaming}
        />
        <button
          onClick={() => sendMessage()}
          disabled={!input.trim() || streaming}
          style={{
            width: 40, height: 40, flexShrink: 0,
            background: (!input.trim() || streaming) ? 'var(--bg-elevated)' : 'linear-gradient(135deg, var(--gold), var(--gold-dim))',
            border: '1px solid var(--bg-border)',
            borderRadius: 'var(--radius-md)',
            color: (!input.trim() || streaming) ? 'var(--text-muted)' : '#080c14',
            cursor: (!input.trim() || streaming) ? 'not-allowed' : 'pointer',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            transition: 'all 0.2s',
          }}
        >
          {streaming ? <div className="spinner" style={{ width: 16, height: 16 }} /> : <Send size={16} />}
        </button>
      </div>

      <div style={{ marginTop: 8, fontSize: '0.7rem', color: 'var(--text-muted)', textAlign: 'center' }}>
        WealthPilot AI uses your actual financial data. Not financial advice — always verify with a certified advisor.
      </div>
    </div>
  )
}
