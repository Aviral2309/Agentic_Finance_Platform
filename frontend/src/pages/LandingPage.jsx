import { useEffect, useRef } from 'react'
import { Link } from 'react-router-dom'

const STOCKS = [
  { s: 'NIFTY 50', p: '24,520.35', c: '+1.2%', up: true },
  { s: 'SENSEX', p: '80,740.25', c: '+1.1%', up: true },
  { s: 'TCS.NS', p: '₹2,151.00', c: '-0.8%', up: false },
  { s: 'HDFCBANK.NS', p: '₹1,738.35', c: '+0.4%', up: true },
  { s: 'RELIANCE.NS', p: '₹2,890.00', c: '+2.1%', up: true },
  { s: 'INFY.NS', p: '₹1,580.50', c: '-1.2%', up: false },
  { s: 'WIPRO.NS', p: '₹459.80', c: '+0.6%', up: true },
  { s: 'GOLD', p: '₹71,240', c: '+0.3%', up: true },
  { s: 'USD/INR', p: '83.42', c: '-0.1%', up: false },
  { s: 'ICICIBANK.NS', p: '₹1,240.60', c: '+1.8%', up: true },
]

const FEATURES = [
  { icon: '🧠', title: '4-Layer ML Categorizer', desc: 'Merchant rules handle 99.1% instantly. Random Forest catches the rest. Gemini AI for edge cases.', tag: '99.1% accuracy', tagColor: '#c9a84c' },
  { icon: '🤖', title: '5-Agent AI Advisor', desc: 'LangGraph routes your question to expense, portfolio, or RAG agents — then synthesizes with Gemini 2.5 Flash.', tag: 'Streaming SSE', tagColor: '#3b82f6' },
  { icon: '📈', title: 'Technical Analysis', desc: 'RSI, MACD, Bollinger Bands computed in under 2 seconds per ticker. Gemini interprets signals in plain English.', tag: '<2s per stock', tagColor: '#22c55e' },
  { icon: '🎯', title: 'FIRE Calculator', desc: '4% safe withdrawal rule, inflation-adjusted corpus, month-by-month SIP roadmap using your actual expenses.', tag: 'Real data input', tagColor: '#8b5cf6' },
  { icon: '🛡️', title: 'Tax Optimizer', desc: 'Old vs new regime compared for FY 2024-25. Finds missing 80C, 80D, NPS deductions automatically.', tag: 'FY 2024-25', tagColor: '#ef4444' },
  { icon: '🔔', title: 'Anomaly Detection', desc: 'Compares this month vs 3-month rolling average per category. Flags spending spikes before you notice them.', tag: 'Auto alerts', tagColor: '#f59e0b' },
]

function Ticker() {
  const items = [...STOCKS, ...STOCKS]
  return (
    <div style={{ background: '#0c0e1a', borderBottom: '1px solid #1e2235', overflow: 'hidden', height: 38, display: 'flex', alignItems: 'center' }}>
      <div style={{ display: 'flex', animation: 'ticker 40s linear infinite', whiteSpace: 'nowrap' }}>
        {items.map((s, i) => (
          <div key={i} style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '0 28px', fontFamily: 'var(--font-mono)', fontSize: 12, borderRight: '1px solid #1e2235' }}>
            <span style={{ fontWeight: 500, color: '#e8eaf0' }}>{s.s}</span>
            <span style={{ color: '#8892a4' }}>{s.p}</span>
            <span style={{ color: s.up ? '#22c55e' : '#ef4444' }}>{s.c}</span>
          </div>
        ))}
      </div>
    </div>
  )
}

export default function LandingPage() {
  return (
    <div style={{ background: '#07080f', color: '#e8eaf0', fontFamily: 'var(--font-body)', minHeight: '100vh' }}>
      <style>{`
        @keyframes ticker { 0% { transform: translateX(0) } 100% { transform: translateX(-50%) } }
        @keyframes pulse-dot { 0%,100% { opacity:1 } 50% { opacity:0.3 } }
        .land-feature:hover { background: #0c0e1a !important; }
        .land-nav-btn:hover { color: #e8eaf0 !important; }
        .land-cta-primary:hover { background: #e2c068 !important; box-shadow: 0 0 24px rgba(200,168,75,0.3); transform: translateY(-1px); }
        .land-outline:hover { border-color: #8a6e28 !important; color: #e8eaf0 !important; }
      `}</style>

      <Ticker />

      {/* Nav */}
      <nav style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '20px 64px', borderBottom: '1px solid #1e2235', position: 'sticky', top: 0, background: 'rgba(7,8,15,0.92)', backdropFilter: 'blur(16px)', zIndex: 100 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 32, height: 32, background: 'linear-gradient(135deg,#c8a84b,#8a6e28)', borderRadius: 8, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, color: '#07080f', fontSize: 14 }}>W</div>
          <span style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', fontStyle: 'italic' }}>WealthPilot</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 32, fontSize: 14, color: '#8892a4' }}>
          <a href="#features" className="land-nav-btn" style={{ color: '#8892a4', textDecoration: 'none', transition: 'color 0.18s' }}>Features</a>
          <a href="#how" className="land-nav-btn" style={{ color: '#8892a4', textDecoration: 'none', transition: 'color 0.18s' }}>How it works</a>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Link to="/login" style={{ padding: '9px 20px', borderRadius: 10, fontSize: 14, fontWeight: 500, color: '#8892a4', textDecoration: 'none', border: '1px solid transparent', transition: 'all 0.18s' }}
            onMouseEnter={e => { e.currentTarget.style.color = '#e8eaf0'; e.currentTarget.style.borderColor = '#262b40' }}
            onMouseLeave={e => { e.currentTarget.style.color = '#8892a4'; e.currentTarget.style.borderColor = 'transparent' }}>
            Sign in
          </Link>
          <Link to="/register" className="land-cta-primary" style={{ padding: '9px 20px', borderRadius: 10, fontSize: 14, fontWeight: 600, background: '#c8a84b', color: '#07080f', textDecoration: 'none', transition: 'all 0.18s', display: 'inline-flex', alignItems: 'center', gap: 6 }}>
            Start free →
          </Link>
        </div>
      </nav>

      {/* Hero */}
      <section style={{ padding: '100px 64px 80px', maxWidth: 1280, margin: '0 auto' }}>
        <div style={{ display: 'inline-flex', alignItems: 'center', gap: 8, padding: '6px 14px', background: 'rgba(200,168,75,0.08)', border: '1px solid rgba(200,168,75,0.2)', borderRadius: 99, fontSize: 12, color: '#c8a84b', fontWeight: 500, letterSpacing: '0.06em', textTransform: 'uppercase', marginBottom: 28 }}>
          <span style={{ width: 6, height: 6, borderRadius: '50%', background: '#c8a84b', animation: 'pulse-dot 2s ease infinite', display: 'inline-block' }} />
          Powered by LangGraph + Gemini 2.5 Flash
        </div>

        <h1 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(3rem,6vw,5.5rem)', lineHeight: 1.05, letterSpacing: '-0.02em', color: '#e8eaf0', maxWidth: 820, marginBottom: 24 }}>
          Your money,<br /><em style={{ fontStyle: 'italic', color: '#c8a84b' }}>finally understood.</em>
        </h1>

        <p style={{ fontSize: 18, color: '#8892a4', maxWidth: 560, lineHeight: 1.7, marginBottom: 44 }}>
          Upload your bank statement. Our 5-agent AI reads every transaction, finds patterns you miss, and tells you exactly where your money went — and where it should go.
        </p>

        <div style={{ display: 'flex', alignItems: 'center', gap: 14, marginBottom: 64 }}>
          <Link to="/register" className="land-cta-primary" style={{ padding: '13px 28px', borderRadius: 10, fontSize: 15, fontWeight: 600, background: '#c8a84b', color: '#07080f', textDecoration: 'none', transition: 'all 0.18s', display: 'inline-flex', alignItems: 'center', gap: 8 }}>
            Analyse my finances free →
          </Link>
          <Link to="/login" className="land-outline" style={{ padding: '12px 20px', borderRadius: 10, fontSize: 14, fontWeight: 500, border: '1px solid #262b40', color: '#8892a4', textDecoration: 'none', transition: 'all 0.18s' }}>
            Sign in
          </Link>
        </div>

        {/* Stats */}
        <div style={{ display: 'flex', borderTop: '1px solid #1e2235', borderBottom: '1px solid #1e2235' }}>
          {[
            { num: '99', suffix: '.1%', label: 'Auto-categorization accuracy' },
            { num: '<2', suffix: 's', label: 'Technical analysis per stock' },
            { num: '5', suffix: '', label: 'AI agents working in parallel' },
            { num: '₹0', suffix: '', label: 'Cost to get started' },
          ].map((s, i) => (
            <div key={i} style={{ flex: 1, padding: '24px 32px', borderRight: i < 3 ? '1px solid #1e2235' : 'none' }}>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '2.2rem', color: '#e8eaf0', letterSpacing: '-0.02em', lineHeight: 1, marginBottom: 4 }}>
                {s.num}<span style={{ color: '#c8a84b' }}>{s.suffix}</span>
              </div>
              <div style={{ fontSize: 13, color: '#4a5568' }}>{s.label}</div>
            </div>
          ))}
        </div>
      </section>

      {/* Features */}
      <section id="features" style={{ padding: '80px 64px', maxWidth: 1280, margin: '0 auto' }}>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 40, marginBottom: 56, alignItems: 'end' }}>
          <div>
            <div style={{ fontSize: 11, color: '#c8a84b', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 12, fontWeight: 500 }}>What WealthPilot does</div>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(2rem,4vw,3rem)', lineHeight: 1.1, letterSpacing: '-0.02em' }}>
              Every layer of your<br /><em style={{ fontStyle: 'italic', color: '#c8a84b' }}>financial life, covered</em>
            </h2>
          </div>
          <p style={{ color: '#8892a4', fontSize: 15, lineHeight: 1.7, maxWidth: 420, alignSelf: 'end' }}>
            We built the tool we wished existed — one that reads your actual numbers, not guesses. Every feature is grounded in your real bank data.
          </p>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3,1fr)', gap: 1, background: '#1e2235', border: '1px solid #1e2235', borderRadius: 16, overflow: 'hidden' }}>
          {FEATURES.map((f, i) => (
            <div key={i} className="land-feature" style={{ background: '#111422', padding: 32, transition: 'background 0.2s', cursor: 'default' }}>
              <div style={{ width: 40, height: 40, borderRadius: 10, background: `${f.tagColor}18`, display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 20, fontSize: 18 }}>{f.icon}</div>
              <h3 style={{ fontSize: 15, fontWeight: 600, color: '#e8eaf0', marginBottom: 8 }}>{f.title}</h3>
              <p style={{ fontSize: 13, color: '#8892a4', lineHeight: 1.6, marginBottom: 14 }}>{f.desc}</p>
              <span style={{ display: 'inline-block', padding: '3px 8px', borderRadius: 4, fontSize: 11, fontFamily: 'var(--font-mono)', fontWeight: 500, background: `${f.tagColor}15`, color: f.tagColor }}>{f.tag}</span>
            </div>
          ))}
        </div>
      </section>

      {/* How it works */}
      <section id="how" style={{ padding: '80px 64px', maxWidth: 1280, margin: '0 auto' }}>
        <div style={{ textAlign: 'center', marginBottom: 56 }}>
          <div style={{ fontSize: 11, color: '#c8a84b', letterSpacing: '0.12em', textTransform: 'uppercase', marginBottom: 12, fontWeight: 500 }}>How it works</div>
          <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(2rem,4vw,3rem)', lineHeight: 1.1, letterSpacing: '-0.02em' }}>
            From statement to insight<br /><em style={{ fontStyle: 'italic', color: '#c8a84b' }}>in under a minute</em>
          </h2>
        </div>

        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4,1fr)', gap: 0, position: 'relative' }}>
          <div style={{ position: 'absolute', top: 28, left: '10%', right: '10%', height: 1, background: 'linear-gradient(90deg,transparent,#1e2235,#8a6e28,#1e2235,transparent)' }} />
          {[
            { n: '01', title: 'Upload statement', desc: 'PDF or CSV from any Indian bank — SBI, HDFC, ICICI, Axis, Kotak' },
            { n: '02', title: 'AI categorizes', desc: '4-layer pipeline labels every transaction automatically in seconds' },
            { n: '03', title: 'See the patterns', desc: 'Category breakdown, anomalies, budget gaps — all surfaced automatically' },
            { n: '04', title: 'Ask anything', desc: 'The AI advisor answers using your actual numbers, not generic advice' },
          ].map((s, i) => (
            <div key={i} style={{ padding: '0 24px', textAlign: 'center', position: 'relative' }}>
              <div style={{ width: 56, height: 56, borderRadius: '50%', background: '#111422', border: '1px solid #1e2235', display: 'flex', alignItems: 'center', justifyContent: 'center', margin: '0 auto 20px', fontFamily: 'var(--font-mono)', fontSize: 13, color: '#c8a84b', position: 'relative', zIndex: 1 }}>{s.n}</div>
              <h4 style={{ fontSize: 14, fontWeight: 600, color: '#e8eaf0', marginBottom: 6 }}>{s.title}</h4>
              <p style={{ fontSize: 13, color: '#8892a4', lineHeight: 1.5 }}>{s.desc}</p>
            </div>
          ))}
        </div>
      </section>

      {/* CTA */}
      <section style={{ padding: '80px 64px', maxWidth: 1280, margin: '0 auto' }}>
        <div style={{ background: 'linear-gradient(135deg,#111422 0%,rgba(200,168,75,0.06) 100%)', border: '1px solid rgba(200,168,75,0.2)', borderRadius: 24, padding: '72px 80px', display: 'grid', gridTemplateColumns: '1fr auto', alignItems: 'center', gap: 40, position: 'relative', overflow: 'hidden' }}>
          <div style={{ position: 'absolute', top: -80, right: -80, width: 300, height: 300, borderRadius: '50%', background: 'radial-gradient(circle,rgba(200,168,75,0.1) 0%,transparent 70%)', pointerEvents: 'none' }} />
          <div>
            <h2 style={{ fontFamily: 'var(--font-display)', fontSize: 'clamp(2rem,4vw,3rem)', letterSpacing: '-0.02em', lineHeight: 1.1, marginBottom: 14 }}>
              Stop guessing.<br /><em style={{ fontStyle: 'italic', color: '#c8a84b' }}>Start knowing.</em>
            </h2>
            <p style={{ color: '#8892a4', fontSize: 15, maxWidth: 480 }}>Upload your first bank statement in 60 seconds. No credit card. No setup. Your data never leaves without your permission.</p>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, alignItems: 'flex-end', flexShrink: 0 }}>
            <Link to="/register" className="land-cta-primary" style={{ padding: '14px 32px', borderRadius: 10, fontSize: 15, fontWeight: 600, background: '#c8a84b', color: '#07080f', textDecoration: 'none', transition: 'all 0.18s', whiteSpace: 'nowrap' }}>
              Create free account →
            </Link>
            <Link to="/login" style={{ fontSize: 14, color: '#8892a4', textDecoration: 'none' }}>Sign in instead</Link>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer style={{ borderTop: '1px solid #1e2235', padding: '40px 64px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 28, height: 28, background: 'linear-gradient(135deg,#c8a84b,#8a6e28)', borderRadius: 7, display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 700, color: '#07080f', fontSize: 12 }}>W</div>
          <span style={{ fontFamily: 'var(--font-display)', fontSize: '1rem', fontStyle: 'italic' }}>WealthPilot</span>
        </div>
        <p style={{ fontSize: 13, color: '#4a5568' }}>Built by Aviral Jain · SGSITS Indore · 2026</p>
        <div style={{ display: 'flex', gap: 24, fontSize: 13, color: '#4a5568' }}>
          <a href="https://github.com/Aviral2309/Agentic_Finance_Platform" target="_blank" rel="noopener noreferrer" style={{ color: '#4a5568', textDecoration: 'none' }}>GitHub</a>
          <a href="/docs" style={{ color: '#4a5568', textDecoration: 'none' }}>API Docs</a>
        </div>
      </footer>
    </div>
  )
}