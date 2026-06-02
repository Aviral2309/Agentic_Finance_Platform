import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Wallet, Eye, EyeOff, ArrowRight } from 'lucide-react'
import { authApi } from '../services/api'
import useStore from '../store/useStore'
import toast from 'react-hot-toast'

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
      // Decode JWT payload — no extra API call needed
      const payload = JSON.parse(atob(token.split('.')[1]))
      setAuth(
        { id: payload.sub, email: form.email, full_name: '' },
        token
      )
      navigate('/')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Invalid email or password')
    } finally {
      setLoading(false)
    }
  }
  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      background: 'var(--bg-base)',
      position: 'relative',
      overflow: 'hidden',
    }}>
      {/* Background decoration */}
      <div style={{
        position: 'absolute', inset: 0,
        background: 'radial-gradient(ellipse at 20% 50%, rgba(201,168,76,0.04) 0%, transparent 60%), radial-gradient(ellipse at 80% 20%, rgba(59,130,246,0.03) 0%, transparent 50%)',
        pointerEvents: 'none',
      }} />

      {/* Left panel — branding */}
      <div style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        padding: '60px 80px',
        borderRight: '1px solid var(--bg-border)',
        background: 'var(--bg-surface)',
      }} className="hide-mobile">
        <div style={{ maxWidth: 440 }}>
          <div style={{
            display: 'flex', alignItems: 'center', gap: 12, marginBottom: 48,
          }}>
            <div style={{
              width: 44, height: 44,
              background: 'linear-gradient(135deg, var(--gold), var(--gold-dim))',
              borderRadius: 12,
              display: 'flex', alignItems: 'center', justifyContent: 'center',
            }}>
              <Wallet size={22} color="#080c14" strokeWidth={2.5} />
            </div>
            <div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', fontWeight: 600 }}>WealthPilot</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--gold)', letterSpacing: '0.12em', textTransform: 'uppercase' }}>Personal Finance Platform</div>
            </div>
          </div>

          <h1 style={{ marginBottom: 16, lineHeight: 1.2 }}>
            Your money,<br />
            <span style={{ color: 'var(--gold)' }}>finally explained.</span>
          </h1>

          <p style={{ color: 'var(--text-secondary)', lineHeight: 1.7, marginBottom: 48, fontSize: '1rem' }}>
            95% of Indians have no financial plan. WealthPilot reads your bank statements, tracks your portfolio, and gives you the same advice a ₹25,000/year advisor would — for free.
          </p>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {[
              { icon: '📊', label: 'Smart expense categorization with ML' },
              { icon: '📈', label: 'AI-powered portfolio forecasting' },
              { icon: '🤖', label: 'Agentic financial advisor' },
            ].map(({ icon, label }) => (
              <div key={label} style={{ display: 'flex', alignItems: 'center', gap: 12, color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
                <span style={{ fontSize: '1.1rem' }}>{icon}</span>
                {label}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right panel — login form */}
      <div style={{
        width: 480,
        minWidth: 480,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 40,
      }}>
        <div style={{ width: '100%', maxWidth: 380, animation: 'fadeUp 0.4s ease' }}>
          <h2 style={{ marginBottom: 6 }}>Welcome back</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', marginBottom: 32 }}>
            Sign in to your WealthPilot account
          </p>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 18 }}>
            <div>
              <label className="input-label">Email</label>
              <input
                className="input"
                type="email"
                placeholder="you@example.com"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                required
                autoFocus
              />
            </div>

            <div>
              <label className="input-label">Password</label>
              <div style={{ position: 'relative' }}>
                <input
                  className="input"
                  type={showPass ? 'text' : 'password'}
                  placeholder="••••••••"
                  value={form.password}
                  onChange={e => setForm(f => ({ ...f, password: e.target.value }))}
                  required
                  style={{ paddingRight: 44 }}
                />
                <button
                  type="button"
                  onClick={() => setShowPass(s => !s)}
                  style={{
                    position: 'absolute', right: 12, top: '50%', transform: 'translateY(-50%)',
                    background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)',
                    display: 'flex', alignItems: 'center',
                  }}
                >
                  {showPass ? <EyeOff size={15} /> : <Eye size={15} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn-primary"
              disabled={loading}
              style={{ width: '100%', justifyContent: 'center', padding: '12px 20px', fontSize: '0.9rem' }}
            >
              {loading ? <div className="spinner" style={{ width: 16, height: 16 }} /> : (
                <><span>Sign in</span><ArrowRight size={16} /></>
              )}
            </button>
          </form>

          <div className="divider" />

          <p style={{ textAlign: 'center', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Don't have an account?{' '}
            <Link to="/register" style={{ color: 'var(--gold)', fontWeight: 500 }}>
              Create one free
            </Link>
          </p>

          {/* Demo hint */}
          <div style={{
            marginTop: 24,
            padding: '12px 16px',
            background: 'var(--gold-muted)',
            border: '1px solid rgba(201,168,76,0.2)',
            borderRadius: 'var(--radius-md)',
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--gold)', fontWeight: 500, marginBottom: 4 }}>Demo Account</div>
            <div style={{ fontSize: '0.75rem', color: 'var(--text-secondary)' }}>test@example.com / testpass123@</div>
          </div>
        </div>
      </div>
    </div>
  )
}
