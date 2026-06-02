import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import {
  TrendingUp, TrendingDown, CreditCard,
  Upload, MessageSquare, ArrowRight,
  IndianRupee, PieChart, Activity
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, PieChart as RPieChart,
  Pie, Cell
} from 'recharts'
import { expensesApi, portfolioApi } from '../services/api'
import useStore from '../store/useStore'

const COLORS = ['#c9a84c', '#3b82f6', '#22c55e', '#ef4444', '#8b5cf6', '#f59e0b', '#06b6d4']

function StatCard({ label, value, change, positive, icon: Icon, accent }) {
  return (
    <div className="card animate-fadeUp" style={{ position: 'relative', overflow: 'hidden' }}>
      <div style={{
        position: 'absolute', top: 0, right: 0,
        width: 80, height: 80,
        background: `radial-gradient(circle, ${accent}15 0%, transparent 70%)`,
        pointerEvents: 'none',
      }} />
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: 16 }}>
        <div className="stat-label">{label}</div>
        <div style={{
          width: 36, height: 36, borderRadius: 10,
          background: `${accent}15`, border: `1px solid ${accent}30`,
          display: 'flex', alignItems: 'center', justifyContent: 'center',
        }}>
          <Icon size={16} color={accent} />
        </div>
      </div>
      <div className="stat-value" style={{ marginBottom: 8 }}>{value}</div>
      {change && (
        <div className={`stat-change ${positive ? 'pos' : 'neg'}`} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
          {positive ? <TrendingUp size={13} /> : <TrendingDown size={13} />}
          {change}
        </div>
      )}
    </div>
  )
}

const CustomTooltip = ({ active, payload, label }) => {
  if (!active || !payload?.length) return null
  return (
    <div style={{
      background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)',
      borderRadius: 8, padding: '10px 14px', fontSize: '0.8rem',
    }}>
      <div style={{ color: 'var(--text-muted)', marginBottom: 6 }}>{label}</div>
      {payload.map((p, i) => (
        <div key={i} style={{ color: p.color, fontFamily: 'var(--font-mono)' }}>
          ₹{Number(p.value).toLocaleString('en-IN')}
        </div>
      ))}
    </div>
  )
}

export default function DashboardPage() {
  const { user } = useStore()
  const [summary, setSummary] = useState(null)
  const [trends, setTrends] = useState([])
  const [portfolio, setPortfolio] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    async function load() {
      try {
        const [sumRes, trendRes, portRes] = await Promise.allSettled([
          expensesApi.summary(),
          expensesApi.trends(6),
          portfolioApi.summary(),
        ])
        if (sumRes.status === 'fulfilled') setSummary(sumRes.value.data)
        if (trendRes.status === 'fulfilled') setTrends(trendRes.value.data)
        if (portRes.status === 'fulfilled') setPortfolio(portRes.value.data)
      } finally {
        setLoading(false)
      }
    }
    load()
  }, [])

  const totalSpend = summary?.total || 0
  const topCategories = summary?.categories?.slice(0, 5) || []
  const portfolioValue = portfolio?.current_value || 0
  const portfolioPnl = portfolio?.total_pnl || 0
  const portfolioPnlPct = portfolio?.total_pnl_pct || 0

  const hour = new Date().getHours()
  const greeting = hour < 12 ? 'Good morning' : hour < 17 ? 'Good afternoon' : 'Good evening'

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 28 }}>

      {/* Header */}
      <div className="animate-fadeUp">
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <h1 style={{ marginBottom: 4, fontSize: '1.75rem' }}>
              {greeting}, <span style={{ color: 'var(--gold)' }}>{user?.full_name?.split(' ')[0] || 'there'}</span>
            </h1>
            <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>
              Here's your financial overview for this month
            </p>
          </div>
          <Link to="/expenses" className="btn btn-primary" style={{ gap: 8 }}>
            <Upload size={15} />
            Upload Statement
          </Link>
        </div>
      </div>

      {/* Stat cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 16 }}
           className="stagger">
        <StatCard
          label="Monthly Spending"
          value={`₹${totalSpend.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
          change={trends.length >= 2 ? `vs ₹${(trends[trends.length - 2]?.total_debit || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })} last month` : null}
          positive={false}
          icon={CreditCard}
          accent="#ef4444"
        />
        <StatCard
          label="Portfolio Value"
          value={`₹${portfolioValue.toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
          change={`${portfolioPnlPct >= 0 ? '+' : ''}${portfolioPnlPct.toFixed(2)}% total return`}
          positive={portfolioPnlPct >= 0}
          icon={TrendingUp}
          accent="#22c55e"
        />
        <StatCard
          label="Total P&L"
          value={`${portfolioPnl >= 0 ? '+' : ''}₹${Math.abs(portfolioPnl).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`}
          positive={portfolioPnl >= 0}
          icon={Activity}
          accent="#c9a84c"
        />
        <StatCard
          label="Categories Tracked"
          value={topCategories.length.toString()}
          change="from your statements"
          positive={true}
          icon={PieChart}
          accent="#3b82f6"
        />
      </div>

      {/* Charts row */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 360px', gap: 20 }}>

        {/* Spending trend */}
        <div className="card animate-fadeUp">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 24 }}>
            <div className="section-title">Spending Trend</div>
            <Link to="/expenses" style={{ fontSize: '0.8rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4 }}>
              Details <ArrowRight size={13} />
            </Link>
          </div>
          {trends.length > 0 ? (
            <ResponsiveContainer width="100%" height={200}>
              <AreaChart data={trends}>
                <defs>
                  <linearGradient id="spendGrad" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%"  stopColor="#c9a84c" stopOpacity={0.3} />
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
              <p>Upload a bank statement to see your spending trends</p>
              <Link to="/expenses" className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '8px 16px' }}>
                Upload now
              </Link>
            </div>
          )}
        </div>

        {/* Category breakdown */}
        <div className="card animate-fadeUp">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
            <div className="section-title">This Month</div>
          </div>
          {topCategories.length > 0 ? (
            <>
              <ResponsiveContainer width="100%" height={140}>
                <RPieChart>
                  <Pie data={topCategories} dataKey="total" nameKey="category" cx="50%" cy="50%" outerRadius={60} innerRadius={36} strokeWidth={0}>
                    {topCategories.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                  </Pie>
                  <Tooltip
                    formatter={(v) => [`₹${Number(v).toLocaleString('en-IN')}`, '']}
                    contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: '0.8rem' }}
                  />
                </RPieChart>
              </ResponsiveContainer>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 12 }}>
                {topCategories.map((cat, i) => (
                  <div key={cat.category} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                      <div style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS[i % COLORS.length], flexShrink: 0 }} />
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{cat.category}</span>
                    </div>
                    <span style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)' }}>
                      {cat.percentage}%
                    </span>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <div className="empty-state" style={{ height: 200 }}>
              <PieChart size={32} />
              <p>No expense data yet</p>
            </div>
          )}
        </div>
      </div>

      {/* Quick actions */}
      <div className="animate-fadeUp">
        <div className="section-title" style={{ marginBottom: 16 }}>Quick Actions</div>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 12 }}>
          {[
            { to: '/expenses', icon: Upload, label: 'Upload Statement', desc: 'Import bank PDF or CSV', color: '#c9a84c' },
            { to: '/portfolio', icon: TrendingUp, label: 'Add Holdings', desc: 'Track your investments', color: '#22c55e' },
            { to: '/advisor', icon: MessageSquare, label: 'Ask Advisor', desc: 'Get AI financial advice', color: '#3b82f6' },
          ].map(({ to, icon: Icon, label, desc, color }) => (
            <Link
              key={to}
              to={to}
              style={{
                display: 'flex', alignItems: 'center', gap: 14,
                padding: '16px 20px',
                background: 'var(--bg-card)',
                border: '1px solid var(--bg-border)',
                borderRadius: 'var(--radius-lg)',
                textDecoration: 'none',
                transition: 'all 0.2s',
              }}
              onMouseEnter={e => { e.currentTarget.style.borderColor = `${color}40`; e.currentTarget.style.background = 'var(--bg-hover)'; }}
              onMouseLeave={e => { e.currentTarget.style.borderColor = 'var(--bg-border)'; e.currentTarget.style.background = 'var(--bg-card)'; }}
            >
              <div style={{
                width: 40, height: 40, borderRadius: 10, flexShrink: 0,
                background: `${color}15`, border: `1px solid ${color}30`,
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Icon size={18} color={color} />
              </div>
              <div>
                <div style={{ fontSize: '0.875rem', fontWeight: 500, color: 'var(--text-primary)', marginBottom: 2 }}>{label}</div>
                <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{desc}</div>
              </div>
              <ArrowRight size={14} color="var(--text-muted)" style={{ marginLeft: 'auto', flexShrink: 0 }} />
            </Link>
          ))}
        </div>
      </div>
    </div>
  )
}
