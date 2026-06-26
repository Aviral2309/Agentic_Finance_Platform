import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  Eye, EyeOff, ArrowRight, TrendingUp, Shield,
  Brain, BarChart2, Target, Bell, FileText, Zap
} from 'lucide-react'
import { authApi } from '../services/api'
import useStore from '../store/useStore'
import toast from 'react-hot-toast'

const FEATURES = [
  { icon: Brain, title: 'AI Financial Advisor', desc: '5-agent LangGraph system that knows your actual numbers', color: '#c9a84c' },
  { icon: FileText, title: 'Smart Expense Tracking', desc: '4-layer ML categorizes 99.1% of transactions automatically', color: '#3b82f6' },
  { icon: TrendingUp, title: 'Portfolio Intelligence', desc: 'RSI, MACD, Bollinger Bands + Gemini AI interpretation', color: '#22c55e' },
  { icon: Target, title: 'FIRE Calculator', desc: 'Retirement corpus planning with inflation-adjusted SIP roadmap', color: '#8b5cf6' },
  { icon: Shield, title: 'Tax Optimizer', desc: 'Old vs new regime comparison with missing deduction alerts', color: '#ef4444' },
  { icon: Bell, title: 'Anomaly Detection', desc: 'Alerts when spending spikes beyond normal patterns', color: '#f59e0b' },
  { icon: BarChart2, title: 'Money Health Score', desc: '6-dimension financial wellness radar with personalized tips', color: '#06b6d4' },
  { icon: Zap, title: 'News Impact Analysis', desc: 'FinBERT NLP links market news to your actual holdings', color: '#ec4899' },
]

function GoogleButton({ loading, onClick }) {
  return (
    <button
      onClick={onClick}
      disabled={loading}
      style={{
        width: '100%',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 10,
        padding: '11px 20px',
        background: 'var(--bg-elevated)',
        border: '1px solid var(--bg-border)',
        borderRadius: 'var(--radius-md)',
        color: 'var(--text-primary)',
        fontSize: '0.9rem',
        fontWeight: 500,
        cursor: 'pointer',
        transition: 'all 0.2s',
        fontFamily: 'var(--font-body)',
      }}
      onMouseEnter={e => { e.currentTarget.style.borderColor = 'var(--gold-dim)'; e.currentTarget.style.background = 'var(--bg-hover)' }}
      onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--bg-border)'; e.currentTarget.style.background = 'var(--bg-elevated)' }}
    >
      <svg width="18" height="18" viewBox="0 0 24 24">
        <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
        <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
        <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
        <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
      </svg>
      Continue with Google
    </button>
  )
}

export default function LoginPage() {
  const [form, setForm] = useState({ email: '', password: '' })
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)
  const { setAuth } = useStore()
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      const { data } = await authApi.login(form)
      const token = data.access_token
      localStorage.setItem('wp_token', token)
      const { data: user } = await authApi.me()
      setAuth(user, token)
      toast.success(`Welcome back, ${user.full_name?.split(' ')[0] || 'there'}!`)
      navigate('/')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Invalid credentials')
    } finally {
      setLoading(false)
    }
  }

  function handleGoogleLogin() {
    toast('Google OAuth coming soon — use email login for now', { icon: '⚡' })
  }

  return (
    <div style={{ minHeight: '100vh', display: 'flex', background: 'var(--bg-base)', overflow: 'hidden', position: 'relative' }}>

      {/* Background glow */}
      <div style={{ position: 'absolute', inset: 0, background: 'radial-gradient(ellipse at 15% 50%, rgba(201,168,76,0.06) 0%, transparent 55%), radial-gradient(ellipse at 85% 20%, rgba(59,130,246,0.04) 0%, transparent 50%)', pointerEvents: 'none' }} />

      {/* Left — Feature Showcase */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', justifyContent: 'center', padding: '60px 64px', borderRight: '1px solid var(--bg-border)', background: 'var(--bg-surface)', position: 'relative' }} className="hide-mobile">

        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 52 }}>
          <div style={{ width: 40, height: 40, background: 'linear-gradient(135deg, var(--gold), var(--gold-dim))', borderRadius: 12, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <TrendingUp size={20} color="#080c14" strokeWidth={2.5} />
          </div>
          <div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.2rem', fontWeight: 600, color: 'var(--text-primary)' }}>WealthPilot</div>
            <div style={{ fontSize: '0.65rem', color: 'var(--gold)', letterSpacing: '0.12em', textTransform: 'uppercase' }}>Personal Finance Platform</div>
          </div>
        </div>

        {/* Headline */}
        <h1 style={{ fontSize: '2rem', marginBottom: 12, lineHeight: 1.2 }}>
          Your money,<br />
          <span style={{ color: 'var(--gold)' }}>finally understood.</span>
        </h1>
        <p style={{ color: 'var(--text-secondary)', fontSize: '0.95rem', marginBottom: 44, lineHeight: 1.7, maxWidth: 420 }}>
          The same financial intelligence a ₹25,000/year advisor gives — powered by AI, built for every Indian.
        </p>

        {/* Feature grid */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {FEATURES.map(({ icon: Icon, title, desc, color }) => (
            <div key={title} style={{
              display: 'flex', alignItems: 'flex-start', gap: 10,
              padding: '12px 14px',
              background: 'var(--bg-card)',
              border: '1px solid var(--bg-border)',
              borderRadius: 'var(--radius-md)',
              transition: 'border-color 0.2s',
            }}
              onMouseEnter={e => e.currentTarget.style.borderColor = `${color}40`}
              onMouseLeave={e => e.currentTarget.style.borderColor = 'var(--bg-border)'}
            >
              <div style={{ width: 30, height: 30, borderRadius: 8, background: `${color}15`, border: `1px solid ${color}25`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Icon size={14} color={color} />
              </div>
              <div>
                <div style={{ fontSize: '0.78rem', fontWeight: 600, color: 'var(--text-primary)', marginBottom: 2 }}>{title}</div>
                <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', lineHeight: 1.4 }}>{desc}</div>
              </div>
            </div>
          ))}
        </div>

        {/* Trust indicators */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 20, marginTop: 32 }}>
          {[
            { label: '99.1%', desc: 'auto-categorization' },
            { label: '5-agent', desc: 'AI advisor' },
            { label: 'NSE live', desc: 'portfolio data' },
          ].map(s => (
            <div key={s.label} style={{ textAlign: 'center' }}>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', fontWeight: 600, color: 'var(--gold)' }}>{s.label}</div>
              <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>{s.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Right — Login Form */}
      <div style={{ width: 460, minWidth: 460, display: 'flex', alignItems: 'center', justifyContent: 'center', padding: '40px 48px' }}>
        <div style={{ width: '100%', animation: 'fadeUp 0.4s ease' }}>

          {/* Mobile logo */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 32 }} className="show-mobile">
            <div style={{ width: 34, height: 34, background: 'linear-gradient(135deg, var(--gold), var(--gold-dim))', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
              <TrendingUp size={16} color="#080c14" />
            </div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '1rem', fontWeight: 600 }}>WealthPilot</div>
          </div>

          <h2 style={{ marginBottom: 4, fontSize: '1.5rem' }}>Welcome back</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: 28 }}>Sign in to your account</p>

          {/* Google OAuth */}
          <GoogleButton loading={loading} onClick={handleGoogleLogin} />

          <div style={{ display: 'flex', alignItems: 'center', gap: 12, margin: '20px 0' }}>
            <div style={{ flex: 1, height: 1, background: 'var(--bg-border)' }} />
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>or continue with email</span>
            <div style={{ flex: 1, height: 1, background: 'var(--bg-border)' }} />
          </div>

          {/* Email form */}
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label className="input-label">Email</label>
              <input className="input" type="email" placeholder="you@example.com"
                value={form.email} onChange={e => setForm(f => ({ ...f, email: e.target.value }))} required autoFocus />
            </div>
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                <label className="input-label" style={{ margin: 0 }}>Password</label>
                <Link to="/forgot-password" style={{ fontSize: '0.75rem', color: 'var(--gold)' }}>Forgot password?</Link>
              </div>
              <div style={{ position: 'relative' }}>
                <input className="input" type={showPass ? 'text' : 'password'} placeholder="••••••••"
                  value={form.password} onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  required style={{ paddingRight: 44 }} />
                <button type="button" onClick={() => setShowPass(s => !s)} style={{ position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)', background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', display: 'flex', alignItems: 'center' }}>
                  {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <button type="submit" disabled={loading} className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', padding: '12px', fontSize: '0.9rem' }}>
              {loading ? <div className="spinner" style={{ width: 16, height: 16 }} /> : <><span>Sign in</span><ArrowRight size={16} /></>}
            </button>
          </form>

          <div className="divider" />

          <p style={{ textAlign: 'center', fontSize: '0.875rem', color: 'var(--text-muted)' }}>
            No account?{' '}
            <Link to="/register" style={{ color: 'var(--gold)', fontWeight: 500 }}>Create one free</Link>
          </p>

          {/* Demo hint */}
          <div style={{ marginTop: 20, padding: '10px 14px', background: 'var(--gold-muted)', border: '1px solid rgba(201,168,76,0.2)', borderRadius: 'var(--radius-md)' }}>
            <div style={{ fontSize: '0.72rem', color: 'var(--gold)', fontWeight: 600, marginBottom: 3 }}>Demo account</div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', fontFamily: 'var(--font-mono)' }}>aviraltest0@gmail.com / your-password</div>
          </div>
        </div>
      </div>
    </div>
  )
}