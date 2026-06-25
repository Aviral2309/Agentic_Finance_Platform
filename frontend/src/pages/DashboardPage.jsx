import { useEffect, useState, useCallback } from 'react'
import { Link } from 'react-router-dom'
import {
  TrendingUp, TrendingDown, CreditCard, Upload,
  MessageSquare, ArrowRight, PieChart, Activity,
  RefreshCw, AlertTriangle, Target, Plus, X, CheckCircle
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, PieChart as RPieChart, Pie, Cell
} from 'recharts'
import { expensesApi, portfolioApi } from '../services/api'
import api from '../services/api'
import useStore from '../store/useStore'
import toast from 'react-hot-toast'

const COLORS = ['#c9a84c', '#3b82f6', '#22c55e', '#ef4444', '#8b5cf6', '#f59e0b', '#06b6d4']

const cache = {
  data: {},
  set(key, val) { this.data[key] = { val, ts: Date.now() } },
  get(key, maxAgeMs = 30000) {
    const entry = this.data[key]
    if (!entry || Date.now() - entry.ts > maxAgeMs) return null
    return entry.val
  }
}

function StatCard({ label, value, change, positive, icon: Icon, accent, loading }) {
  return (
    <div className="card animate-fadeUp" style={{ position: 'relative', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', top: 0, right: 0, width: 80, height: 80, background: `radial-gradient(circle, ${accent}15 0%, transparent 70%)`, pointerEvents: 'none' }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 12 }}>
        <div className="stat-label">{label}</div>
        <div style={{ width: 34, height: 34, borderRadius: 10, background: `${accent}15`, border: `1px solid ${accent}30`, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Icon size={15} color={accent} />
        </div>
      </div>
      {loading ? <div className="skeleton" style={{ height: 28, width: '60%', marginBottom: 8 }} /> : (
        <div className="stat-value" style={{ marginBottom: 6 }}>{value}</div>
      )}
      {change && !loading && (
        <div className={`stat-change ${positive ? 'pos' : 'neg'}`} style={{ display: 'flex', alignItems: 'center', gap: 4, fontSize: '0.75rem' }}>
          {positive ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
          {change}
        </div>
      )}
    </div>
  )
}

// ── Goal Tracker ───────────────────────────────────────────────
function GoalTracker() {
  const [goals, setGoals] = useState([])
  const [showAdd, setShowAdd] = useState(false)
  const [form, setForm] = useState({ name: '', target_amount: '', current_amount: '', target_date: '' })

  useEffect(() => {
    api.get('/features/goals').then(r => setGoals(r.data.goals)).catch(() => {})
  }, [])

  async function addGoal(e) {
    e.preventDefault()
    try {
      const { data } = await api.post('/features/goals', {
        name: form.name,
        target_amount: parseFloat(form.target_amount),
        current_amount: parseFloat(form.current_amount || 0),
        target_date: form.target_date || null,
      })
      setGoals(prev => [...prev, data])
      setForm({ name: '', target_amount: '', current_amount: '', target_date: '' })
      setShowAdd(false)
      toast.success('Goal added!')
    } catch { toast.error('Failed to add goal') }
  }

  async function deleteGoal(id) {
    await api.delete(`/features/goals/${id}`)
    setGoals(prev => prev.filter(g => g.id !== id))
  }

  const GOAL_COLORS = { savings: '#22c55e', vacation: '#3b82f6', emergency: '#f59e0b', investment: '#c9a84c', other: '#8b5cf6' }

  return (
    <div className="card animate-fadeUp">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div className="section-title">Financial Goals</div>
        <button onClick={() => setShowAdd(s => !s)} className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '5px 10px' }}>
          <Plus size={13} /> Add Goal
        </button>
      </div>

      {showAdd && (
        <form onSubmit={addGoal} style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16, padding: 12, background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)' }}>
          <input className="input" placeholder="Goal name (e.g. Vacation to Goa)" value={form.name}
            onChange={e => setForm(f => ({ ...f, name: e.target.value }))} required style={{ fontSize: '0.82rem', padding: '7px 10px' }} />
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 8 }}>
            <input className="input" type="number" placeholder="Target ₹" value={form.target_amount}
              onChange={e => setForm(f => ({ ...f, target_amount: e.target.value }))} required style={{ fontSize: '0.82rem', padding: '7px 10px' }} />
            <input className="input" type="number" placeholder="Saved so far ₹" value={form.current_amount}
              onChange={e => setForm(f => ({ ...f, current_amount: e.target.value }))} style={{ fontSize: '0.82rem', padding: '7px 10px' }} />
          </div>
          <input className="input" type="date" value={form.target_date}
            onChange={e => setForm(f => ({ ...f, target_date: e.target.value }))} style={{ fontSize: '0.82rem', padding: '7px 10px' }} />
          <div style={{ display: 'flex', gap: 6 }}>
            <button type="submit" className="btn btn-primary" style={{ flex: 1, justifyContent: 'center', fontSize: '0.82rem', padding: '7px' }}>Add</button>
            <button type="button" onClick={() => setShowAdd(false)} className="btn btn-ghost" style={{ padding: '7px 10px' }}><X size={13} /></button>
          </div>
        </form>
      )}

      {goals.length === 0 ? (
        <div className="empty-state" style={{ padding: '20px 0' }}>
          <Target size={28} />
          <p>Set financial goals to track your progress</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          {goals.map(goal => {
            const color = GOAL_COLORS[goal.category] || '#6b7280'
            const pct = Math.min(100, goal.progress_pct)
            return (
              <div key={goal.id}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    {pct >= 100 ? <CheckCircle size={14} color="var(--green)" /> : <Target size={14} color={color} />}
                    <span style={{ fontSize: '0.82rem', color: 'var(--text-primary)', fontWeight: 500 }}>{goal.name}</span>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                    <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: 'var(--text-muted)' }}>
                      ₹{goal.current_amount.toLocaleString('en-IN')} / ₹{goal.target_amount.toLocaleString('en-IN')}
                    </span>
                    <button onClick={() => deleteGoal(goal.id)} style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 2 }}
                      onMouseEnter={e => e.currentTarget.style.color = 'var(--red)'}
                      onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}>
                      <X size={12} />
                    </button>
                  </div>
                </div>
                <div className="progress-bar">
                  <div style={{ height: '100%', width: `${pct}%`, background: pct >= 100 ? 'var(--green)' : color, borderRadius: 99, transition: 'width 0.8s ease' }} />
                </div>
                <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: 3 }}>
                  {pct.toFixed(0)}% complete
                  {goal.target_date && ` · Target: ${new Date(goal.target_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' })}`}
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}

// ── Anomaly Alerts ─────────────────────────────────────────────
function AnomalyAlerts() {
  const [anomalies, setAnomalies] = useState([])

  useEffect(() => {
    api.get('/features/anomalies').then(r => setAnomalies(r.data.anomalies)).catch(() => {})
  }, [])

  if (anomalies.length === 0) return null

  return (
    <div className="animate-fadeUp">
      <div className="section-title" style={{ marginBottom: 12 }}>Spending Alerts</div>
      <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
        {anomalies.slice(0, 3).map((a, i) => (
          <div key={i} style={{
            display: 'flex', alignItems: 'flex-start', gap: 10,
            padding: '10px 14px', borderRadius: 'var(--radius-md)',
            background: a.severity === 'high' ? 'var(--red-dim)' : 'rgba(245,158,11,0.08)',
            border: `1px solid ${a.severity === 'high' ? 'rgba(239,68,68,0.2)' : 'rgba(245,158,11,0.2)'}`,
          }}>
            <AlertTriangle size={14} color={a.severity === 'high' ? 'var(--red)' : 'var(--amber)'} style={{ flexShrink: 0, marginTop: 2 }} />
            <div>
              <div style={{ fontSize: '0.8rem', fontWeight: 500, color: a.severity === 'high' ? 'var(--red)' : 'var(--amber)', marginBottom: 2 }}>
                {a.category} up {a.pct_change.toFixed(0)}%
              </div>
              <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>{a.message}</div>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, padding: '10px 14px', fontSize: '0.8rem' }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 6 }}>{label}</div>
      {payload.map((p, i) => <div key={i} style={{ color: p.color, fontFamily: 'var(--font-mono)' }}>₹{Number(p.value).toLocaleString('en-IN')}</div>)}
    </div>
  )
}

export default function DashboardPage() {
  const { user } = useStore()
  const [summary, setSummary] = useState(null)
  const [trends, setTrends] = useState([])
  const [portfolio, setPortfolio] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [lastUpdated, setLastUpdated] = useState(null)

  const loadData = useCallback(async (forceRefresh = false) => {
    if (!forceRefresh) {
      const cached = cache.get('dashboard', 30000)
      if (cached) {
        setSummary(cached.summary); setTrends(cached.trends); setPortfolio(cached.portfolio)
        setLoading(false); setLastUpdated(cached.ts); return
      }
    }
    if (forceRefresh) setRefreshing(true)
    try {
      const [sumRes, trendRes, portRes] = await Promise.allSettled([
        expensesApi.summary(), expensesApi.trends(6), portfolioApi.summary(),
      ])
      const s = sumRes.status === 'fulfilled' ? sumRes.value.data : null
      const t = trendRes.status === 'fulfilled' ? trendRes.value.data : []
      const p = portRes.status === 'fulfilled' ? portRes.value.data : null
      setSummary(s); setTrends(t); setPortfolio(p)
      const ts = new Date(); setLastUpdated(ts)
      cache.set('dashboard', { summary: s, trends: t, portfolio: p, ts })
    } finally { setLoading(false); setRefreshing(false) }
  }, [])

  useEffect(() => { loadData(); const i = setInterval(() => loadData(true), 60000); return () => clearInterval(i) }, [loadData])

  const totalSpend = summary?.total || 0
  const topCategories = summary?.categories?.slice(0, 5) || []
  const portfolioValue = portfolio?.current_value || 0
  const portfolioPnl = portfolio?.total_pnl || 0
  const portfolioPnlPct = portfolio?.total_pnl_pct || 0
  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 22 }}>

      {/* Header */}
      <div className="animate-fadeUp" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ marginBottom: 4, fontSize: '1.75rem' }}>
            {greeting}, <span style={{ color: 'var(--gold)' }}>{user?.full_name?.split(' ')[0] || 'there'}</span>
          </h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem', display: 'flex', alignItems: 'center', gap: 8 }}>
            Financial overview
            {lastUpdated && <span style={{ fontSize: '0.72rem' }}>· Updated {lastUpdated instanceof Date ? lastUpdated.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }) : ''}</span>}
          </p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => loadData(true)} disabled={refreshing} className="btn btn-ghost" style={{ fontSize: '0.8rem', padding: '8px 12px' }}>
            <RefreshCw size={14} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
          </button>
          <Link to="/expenses" className="btn btn-primary" style={{ fontSize: '0.875rem' }}>
            <Upload size={14} /> Upload Statement
          </Link>
        </div>
      </div>

      {/* Anomaly Alerts */}
      <AnomalyAlerts />

      {/* Stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 14 }} className="stagger">
        <StatCard label="Monthly Spending" value={`₹${totalSpend.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`} positive={false} icon={CreditCard} accent="#ef4444" loading={loading} />
        <StatCard label="Portfolio Value" value={`₹${portfolioValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`} change={`${portfolioPnlPct >= 0 ? '+' : ''}${portfolioPnlPct.toFixed(2)}% return`} positive={portfolioPnlPct >= 0} icon={TrendingUp} accent="#22c55e" loading={loading} />
        <StatCard label="Total P&L" value={`${portfolioPnl >= 0 ? '+' : ''}₹${Math.abs(portfolioPnl).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`} positive={portfolioPnl >= 0} icon={Activity} accent="#c9a84c" loading={loading} />
        <StatCard label="Categories" value={topCategories.length.toString()} positive={true} icon={PieChart} accent="#3b82f6" loading={loading} />
      </div>

      {/* Charts */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 18 }}>
        <div className="card animate-fadeUp">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <div className="section-title">Spending Trend</div>
            <Link to="/expenses" style={{ fontSize: '0.78rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
              Details <ArrowRight size={12} />
            </Link>
          </div>
          {loading ? <div className="skeleton" style={{ height: 200 }} /> : trends.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={trends}>
                <defs>
                  <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#c9a84c" stopOpacity={0.3} />
                    <stop offset="95%" stopColor="#c9a84c" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <XAxis dataKey="month" tick={{ fill: 'var(--text-muted)', fontSize: 11 }} axisLine={false} tickLine={false} />
                <YAxis hide />
                <Tooltip content={<CustomTooltip />} />
                <Area type="monotone" dataKey="total_debit" stroke="#c9a84c" strokeWidth={2} fill="url(#spendGrad)" dot={false} />
              </AreaChart>
            </ResponsiveContainer>
          ) : (
            <div className="empty-state" style={{ height: 200 }}>
              <CreditCard size={32} />
              <p>Upload a bank statement to see trends</p>
              <Link to="/expenses" className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '7px 14px' }}>Upload now</Link>
            </div>
          )}
        </div>

        <div className="card animate-fadeUp">
          <div className="section-title" style={{ marginBottom: 18 }}>This Month</div>
          {loading ? <div className="skeleton" style={{ height: 200 }} /> : topCategories.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={130}>
                <RPieChart>
                  <Pie data={topCategories} dataKey="total" nameKey="category" cx="50%" cy="50%" outerRadius={55} innerRadius={32} strokeWidth={0}>
                    {topCategories.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip formatter={(v) => [`₹${Number(v).toLocaleString('en-IN')}`, '']}
                    contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: '0.78rem' }} />
                </RPieChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
                {topCategories.map((cat, i) => (
                  <div key={cat.category} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                      <div style={{ width: 7, height: 7, borderRadius: '50%', background: COLORS[i % COLORS.length] }} />
                      <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{cat.category}</span>
                    </div>
                    <span style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>{cat.percentage}%</span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="empty-state" style={{ height: 200 }}>
              <PieChart size={32} /><p>No expense data yet</p>
            </div>
          )}
        </div>
      </div>

      {/* Goals + Quick Actions */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 18 }}>
        <GoalTracker />
        <div className="card animate-fadeUp">
          <div className="section-title" style={{ marginBottom: 14 }}>Quick Actions</div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {[
              { to: '/expenses', icon: Upload, label: 'Upload Statement', desc: 'Import bank PDF or CSV', color: '#c9a84c' },
              { to: '/portfolio', icon: TrendingUp, label: 'Add Holdings', desc: 'Track investments', color: '#22c55e' },
              { to: '/advisor', icon: MessageSquare, label: 'Ask Advisor', desc: 'AI financial advice', color: '#3b82f6' },
            ].map(({ to, icon: Icon, label, desc, color }) => (
              <Link key={to} to={to} style={{ display: 'flex', alignItems: 'center', gap: 12, padding: '12px 16px', background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 'var(--radius-md)', textDecoration: 'none', transition: 'all 0.2s' }}
                onMouseEnter={e => { e.currentTarget.style.borderColor = `${color}40`; e.currentTarget.style.background = 'var(--bg-hover)' }}
                onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--bg-border)'; e.currentTarget.style.background = 'var(--bg-elevated)' }}>
                <div style={{ width: 34, height: 34, borderRadius: 9, background: `${color}15`, border: `1px solid ${color}30`, display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                  <Icon size={16} color={color} />
                </div>
                <div>
                  <div style={{ fontSize: '0.83rem', fontWeight: 500, color: 'var(--text-primary)', marginBottom: 1 }}>{label}</div>
                  <div style={{ fontSize: '0.71rem', color: 'var(--text-muted)' }}>{desc}</div>
                </div>
                <ArrowRight size={13} color="var(--text-muted)" style={{ marginLeft: 'auto', flexShrink: 0 }} />
              </Link>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}
