import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Wallet, Eye, EyeOff, ArrowRight } from 'lucide-react'
import { authApi } from '../services/api'
import useStore from '../store/useStore'
import toast from 'react-hot-toast'

export default function RegisterPage() {
  const [form, setForm] = useState({ email: '', password: '', full_name: '' })
  const [showPass, setShowPass] = useState(false)
  const [loading, setLoading] = useState(false)
  const { setAuth } = useStore()
  const navigate = useNavigate()

  async function handleSubmit(e) {
    e.preventDefault()
    if (form.password.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }
    setLoading(true)
    try {
      await authApi.register(form)
      const { data } = await authApi.login({ email: form.email, password: form.password })
      const token = data.access_token
      localStorage.setItem('wp_token', token)
      const { data: user } = await authApi.me()
      setAuth(user, token)
      toast.success('Account created! Welcome to WealthPilot.')
      navigate('/')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      background: 'var(--bg-base)',
      padding: 20,
      position: 'relative',
    }}>
      <div style={{
        position: 'absolute', inset: 0,
        background: 'radial-gradient(ellipse at 50% 0%, rgba(201,168,76,0.05) 0%, transparent 60%)',
        pointerEvents: 'none',
      }} />

      <div style={{ width: '100%', maxWidth: 420, animation: 'fadeUp 0.4s ease' }}>
        {/* Logo */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 36, justifyContent: 'center' }}>
          <div style={{
            width: 36, height: 36,
            background: 'linear-gradient(135deg, var(--gold), var(--gold-dim))',
            borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Wallet size={18} color="#080c14" strokeWidth={2.5} />
          </div>
          <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', fontWeight: 600 }}>WealthPilot</div>
        </div>

        <div className="card" style={{ padding: 36 }}>
          <h2 style={{ marginBottom: 6, textAlign: 'center' }}>Create account</h2>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.85rem', marginBottom: 28, textAlign: 'center' }}>
            Start your financial journey for free
          </p>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div>
              <label className="input-label">Full Name</label>
              <input
                className="input"
                type="text"
                placeholder="Aviral Jain"
                value={form.full_name}
                onChange={e => setForm(f => ({ ...f, full_name: e.target.value }))}
                autoFocus
              />
            </div>

            <div>
              <label className="input-label">Email</label>
              <input
                className="input"
                type="email"
                placeholder="you@example.com"
                value={form.email}
                onChange={e => setForm(f => ({ ...f, email: e.target.value }))}
                required
              />
            </div>

            <div>
              <label className="input-label">Password</label>
              <div style={{ position: 'relative' }}>
                <input
                  className="input"
                  type={showPass ? 'text' : 'password'}
                  placeholder="Min 8 characters"
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
              style={{ width: '100%', justifyContent: 'center', padding: '12px 20px', marginTop: 4, fontSize: '0.9rem' }}
            >
              {loading ? <div className="spinner" style={{ width: 16, height: 16 }} /> : (
                <><span>Create account</span><ArrowRight size={16} /></>
              )}
            </button>
          </form>

          <div className="divider" />

          <p style={{ textAlign: 'center', fontSize: '0.85rem', color: 'var(--text-muted)' }}>
            Already have an account?{' '}
            <Link to="/login" style={{ color: 'var(--gold)', fontWeight: 500 }}>Sign in</Link>
          </p>
        </div>
      </div>
    </div>
  )
}
