import { useEffect, useState, useCallback } from 'react'
import {
  TrendingUp, TrendingDown, Plus, Trash2,
  RefreshCw, BarChart2, Activity, Info,
  MessageSquare, AlertTriangle, CheckCircle
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell,
  BarChart, Bar
} from 'recharts'
import { portfolioApi } from '../services/api'
import api from '../services/api'
import toast from 'react-hot-toast'

const COLORS = ['#c9a84c', '#3b82f6', '#22c55e', '#8b5cf6', '#f59e0b', '#06b6d4', '#ec4899']

const SentimentBadge = ({ label }) => {
  const config = {
    bullish: { color: 'var(--green)', bg: 'var(--green-dim)', icon: '↑' },
    bearish: { color: 'var(--red)', bg: 'var(--red-dim)', icon: '↓' },
    neutral: { color: 'var(--text-secondary)', bg: 'var(--bg-elevated)', icon: '→' },
  }[label] || { color: 'var(--text-muted)', bg: 'var(--bg-elevated)', icon: '?' }

  return (
    <span style={{
      padding: '2px 8px', borderRadius: 99, fontSize: '0.7rem', fontWeight: 600,
      background: config.bg, color: config.color,
      display: 'inline-flex', alignItems: 'center', gap: 3,
    }}>
      {config.icon} {label || 'N/A'}
    </span>
  )
}

const SignalBadge = ({ signal }) => {
  const config = {
    bullish: { label: '↑ Bullish', color: 'var(--green)', bg: 'var(--green-dim)' },
    bearish: { label: '↓ Bearish', color: 'var(--red)', bg: 'var(--red-dim)' },
    neutral: { label: '→ Neutral', color: 'var(--text-secondary)', bg: 'var(--bg-elevated)' },
  }[signal] || { label: '? Unknown', color: 'var(--text-muted)', bg: 'var(--bg-elevated)' }

  return (
    <span style={{ padding: '3px 10px', borderRadius: 99, fontSize: '0.75rem', fontWeight: 600, background: config.bg, color: config.color }}>
      {config.label}
    </span>
  )
}

function TechnicalAnalysisPanel({ ticker }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const { data: d } = await api.get(`/portfolio/analysis/${ticker}`)
      setData(d)
    } catch (e) {
      setError(e.response?.data?.detail || 'Analysis failed')
    } finally {
      setLoading(false)
    }
  }, [ticker])

  useEffect(() => { load() }, [load])

  if (loading) return (
    <div style={{ padding: 24, display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 10, color: 'var(--text-muted)' }}>
      <div className="spinner" />
      <span style={{ fontSize: '0.85rem' }}>Running technical analysis...</span>
    </div>
  )

  if (error) return (
    <div className="empty-state" style={{ padding: '24px' }}>
      <Activity size={28} />
      <p>{error}</p>
      <button onClick={load} className="btn btn-ghost" style={{ fontSize: '0.78rem' }}>
        <RefreshCw size={12} /> Retry
      </button>
    </div>
  )

  if (!data || data.error) return (
    <div className="empty-state" style={{ padding: '24px' }}>
      <p>{data?.error || 'No data available'}</p>
    </div>
  )

  const indicators = [
    { label: 'RSI (14)', value: data.rsi, note: data.rsi < 35 ? 'Oversold' : data.rsi > 70 ? 'Overbought' : 'Neutral', color: data.rsi < 35 ? 'var(--green)' : data.rsi > 70 ? 'var(--red)' : 'var(--text-secondary)' },
    { label: 'MACD', value: data.macd?.crossover?.replace(/_/g, ' '), note: `Histogram: ${data.macd?.histogram?.toFixed(3)}`, color: data.macd?.crossover?.includes('bullish') ? 'var(--green)' : 'var(--red)' },
    { label: 'MA Trend', value: data.moving_averages?.trend, note: `50MA: ₹${data.moving_averages?.ma50 || 'N/A'}`, color: data.moving_averages?.trend === 'bullish' ? 'var(--green)' : 'var(--red)' },
    { label: 'Bollinger', value: data.bollinger?.position?.replace(/_/g, ' '), note: `BW: ${data.bollinger?.bandwidth}%`, color: data.bollinger?.position === 'below_lower' ? 'var(--green)' : data.bollinger?.position === 'above_upper' ? 'var(--red)' : 'var(--text-secondary)' },
    { label: 'Volume', value: data.volume?.signal, note: `${data.volume?.volume_ratio}x avg volume`, color: data.volume?.signal === 'accumulation' ? 'var(--green)' : data.volume?.signal === 'distribution' ? 'var(--red)' : 'var(--text-secondary)' },
  ]

  const sr = data.support_resistance || {}
  const ma = data.moving_averages || {}

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
      {/* Signal + price */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <div style={{ fontSize: '1.25rem', fontFamily: 'var(--font-display)', fontWeight: 600 }}>
            ₹{data.current_price?.toLocaleString('en-IN')}
          </div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 2 }}>
            52W: ₹{sr.week52_low} — ₹{sr.week52_high}
          </div>
        </div>
        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 4 }}>
          <SignalBadge signal={data.overall_signal} />
          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
            {data.bullish_signals} bullish · {data.bearish_signals} bearish signals
          </div>
        </div>
      </div>

      {/* Indicators grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(5, 1fr)', gap: 8 }}>
        {indicators.map(ind => (
          <div key={ind.label} style={{ padding: '10px 10px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--bg-border)', textAlign: 'center' }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: 4, textTransform: 'uppercase', letterSpacing: '0.05em' }}>{ind.label}</div>
            <div style={{ fontSize: '0.78rem', fontWeight: 600, color: ind.color, textTransform: 'capitalize', marginBottom: 2 }}>{ind.value}</div>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)' }}>{ind.note}</div>
          </div>
        ))}
      </div>

      {/* Support/Resistance */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 8 }}>
        {[
          { label: 'Support', value: `₹${sr.support}`, color: 'var(--green)' },
          { label: 'Resistance', value: `₹${sr.resistance}`, color: 'var(--red)' },
          { label: '50-day MA', value: ma.ma50 ? `₹${ma.ma50}` : 'N/A', color: 'var(--blue)' },
          { label: '200-day MA', value: ma.ma200 ? `₹${ma.ma200}` : 'N/A', color: 'var(--purple)' },
        ].map(s => (
          <div key={s.label} style={{ padding: '8px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--bg-border)', textAlign: 'center' }}>
            <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', marginBottom: 3 }}>{s.label}</div>
            <div style={{ fontSize: '0.82rem', fontFamily: 'var(--font-mono)', color: s.color, fontWeight: 600 }}>{s.value}</div>
          </div>
        ))}
      </div>

      {/* AI Interpretation */}
      {data.interpretation && (
        <div style={{ padding: '14px 16px', background: 'var(--gold-muted)', border: '1px solid rgba(201,168,76,0.2)', borderRadius: 'var(--radius-md)' }}>
          <div style={{ fontSize: '0.72rem', color: 'var(--gold)', fontWeight: 600, marginBottom: 6, textTransform: 'uppercase', letterSpacing: '0.06em' }}>
            Gemini AI Analysis
          </div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            {data.interpretation}
          </div>
        </div>
      )}

      <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', padding: '6px 10px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)' }}>
        <Info size={10} style={{ display: 'inline', marginRight: 4 }} />
        Technical analysis is for educational purposes only. Not investment advice.
      </div>
    </div>
  )
}

function AddHoldingForm({ onAdd, onClose }) {
  const [form, setForm] = useState({ ticker: '', quantity: '', buy_price: '', exchange: 'NSE' })
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await portfolioApi.addHolding({
        ticker: form.ticker.toUpperCase(),
        quantity: parseFloat(form.quantity),
        buy_price: parseFloat(form.buy_price),
        exchange: form.exchange,
      })
      toast.success(`${form.ticker.toUpperCase()} added! Technical analysis will load shortly.`)
      onAdd()
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add holding')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 50, background: 'rgba(8,12,20,0.8)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="card animate-fadeUp" style={{ width: '100%', maxWidth: 400, padding: 32 }}>
        <h3 style={{ marginBottom: 4 }}>Add Holding</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginBottom: 24 }}>Technical analysis runs automatically after adding</p>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label className="input-label">NSE Ticker</label>
            <input className="input" placeholder="TCS, RELIANCE, INFY, HDFCBANK..." value={form.ticker}
              onChange={e => setForm(f => ({ ...f, ticker: e.target.value }))} required autoFocus />
            <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', marginTop: 4 }}>Enter NSE symbol without .NS suffix</div>
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            <div>
              <label className="input-label">Quantity</label>
              <input className="input" type="number" placeholder="10" value={form.quantity}
                onChange={e => setForm(f => ({ ...f, quantity: e.target.value }))} required min="0.01" step="0.01" />
            </div>
            <div>
              <label className="input-label">Buy Price (₹)</label>
              <input className="input" type="number" placeholder="3500" value={form.buy_price}
                onChange={e => setForm(f => ({ ...f, buy_price: e.target.value }))} required min="0.01" step="0.01" />
            </div>
          </div>
          <div style={{ display: 'flex', gap: 10, marginTop: 4 }}>
            <button type="button" onClick={onClose} className="btn btn-ghost" style={{ flex: 1, justifyContent: 'center' }}>Cancel</button>
            <button type="submit" disabled={loading} className="btn btn-primary" style={{ flex: 1, justifyContent: 'center' }}>
              {loading ? <div className="spinner" style={{ width: 16, height: 16 }} /> : 'Add Holding'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

export default function PortfolioPage() {
  const [portfolio, setPortfolio] = useState(null)
  const [loading, setLoading] = useState(true)
  const [refreshing, setRefreshing] = useState(false)
  const [showAddForm, setShowAddForm] = useState(false)
  const [selectedTicker, setSelectedTicker] = useState(null)

  async function loadPortfolio(force = false) {
    if (force) setRefreshing(true)
    try {
      const { data } = await portfolioApi.summary()
      setPortfolio(data)
      if (data.holdings?.length > 0 && !selectedTicker) {
        setSelectedTicker(data.holdings[0].ticker)
      }
    } catch {
      toast.error('Failed to load portfolio')
    } finally {
      setLoading(false)
      setRefreshing(false)
    }
  }

  useEffect(() => { loadPortfolio() }, [])

  async function handleDelete(id, ticker) {
    if (!confirm(`Remove ${ticker} from portfolio?`)) return
    try {
      await portfolioApi.deleteHolding(id)
      toast.success(`${ticker} removed`)
      setSelectedTicker(null)
      loadPortfolio(true)
    } catch { toast.error('Failed to remove') }
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 400, gap: 10, color: 'var(--text-muted)' }}>
      <div className="spinner" />
      <span>Loading portfolio...</span>
    </div>
  )

  const holdings = portfolio?.holdings || []
  const sectorData = Object.entries(portfolio?.allocation_by_sector || {}).map(([name, value]) => ({ name, value }))
  const warnings = portfolio?.warnings || []
  const insights = portfolio?.insights || []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      {showAddForm && <AddHoldingForm onAdd={() => loadPortfolio(true)} onClose={() => setShowAddForm(false)} />}

      {/* Header */}
      <div className="animate-fadeUp" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', marginBottom: 4 }}>Portfolio</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Live prices · Technical analysis · AI interpretation</p>
        </div>
        <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => loadPortfolio(true)} disabled={refreshing} className="btn btn-ghost" style={{ fontSize: '0.8rem', padding: '8px 12px' }}>
            <RefreshCw size={14} style={{ animation: refreshing ? 'spin 1s linear infinite' : 'none' }} />
          </button>
          <button onClick={() => setShowAddForm(true)} className="btn btn-primary">
            <Plus size={15} /> Add Holding
          </button>
        </div>
      </div>

      {/* Warnings + insights */}
      {[...warnings, ...insights].length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {warnings.map((w, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px', background: 'rgba(245,158,11,0.08)', border: '1px solid rgba(245,158,11,0.2)', borderRadius: 'var(--radius-md)', fontSize: '0.8rem', color: 'var(--amber)' }}>
              <AlertTriangle size={13} />{w}
            </div>
          ))}
          {insights.map((ins, i) => (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '8px 14px', background: 'var(--green-dim)', border: '1px solid rgba(34,197,94,0.2)', borderRadius: 'var(--radius-md)', fontSize: '0.8rem', color: 'var(--green)' }}>
              <CheckCircle size={13} />{ins}
            </div>
          ))}
        </div>
      )}

      {/* Summary stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 12 }} className="stagger">
        {[
          { label: 'Invested', value: `₹${(portfolio?.total_invested||0).toLocaleString('en-IN',{maximumFractionDigits:0})}`, color: 'var(--text-primary)' },
          { label: 'Current Value', value: `₹${(portfolio?.current_value||0).toLocaleString('en-IN',{maximumFractionDigits:0})}`, color: 'var(--text-primary)' },
          { label: 'Total P&L', value: `${(portfolio?.total_pnl||0)>=0?'+':''}₹${Math.abs(portfolio?.total_pnl||0).toLocaleString('en-IN',{maximumFractionDigits:0})}`, color: (portfolio?.total_pnl||0)>=0?'var(--green)':'var(--red)' },
          { label: 'Sharpe Ratio', value: portfolio?.sharpe_ratio?.toFixed(2) || 'N/A', color: 'var(--gold)' },
        ].map(s => (
          <div key={s.label} className="card animate-fadeUp" style={{ padding: '16px 18px' }}>
            <div className="stat-label" style={{ marginBottom: 6 }}>{s.label}</div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.25rem', fontWeight: 600, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {holdings.length === 0 ? (
        <div className="card animate-fadeUp">
          <div className="empty-state" style={{ padding: '60px 24px' }}>
            <TrendingUp size={48} />
            <h3 style={{ fontFamily: 'var(--font-display)' }}>No holdings yet</h3>
            <p>Add your stocks to get technical analysis, RSI, MACD, support/resistance levels, and AI interpretation.</p>
            <button onClick={() => setShowAddForm(true)} className="btn btn-primary">
              <Plus size={15} /> Add your first holding
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 320px', gap: 18, alignItems: 'start' }}>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            {/* Holdings table */}
            <div className="card animate-fadeUp" style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ padding: '18px 20px 14px' }}>
                <div className="section-title">Holdings — click to analyse</div>
              </div>
              <table className="table">
                <thead>
                  <tr>
                    <th>Stock</th><th>Qty</th><th>Buy</th><th>Current</th><th>P&L</th><th>Sentiment</th><th></th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map(h => (
                    <tr key={h.id} onClick={() => setSelectedTicker(h.ticker)}
                      style={{ cursor: 'pointer', background: selectedTicker === h.ticker ? 'var(--gold-muted)' : 'transparent' }}>
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.875rem' }}>{h.ticker}</div>
                        <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{h.company_name?.slice(0,22) || h.sector || h.exchange}</div>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>{h.quantity}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>₹{h.buy_price}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                        {h.current_price ? `₹${h.current_price.toLocaleString('en-IN')}` : '—'}
                      </td>
                      <td>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.82rem', color: (h.pnl||0)>=0?'var(--green)':'var(--red)' }}>
                          {h.pnl!=null ? `${h.pnl>=0?'+':''}₹${Math.abs(h.pnl).toLocaleString('en-IN',{maximumFractionDigits:0})}` : '—'}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: (h.pnl_pct||0)>=0?'var(--green)':'var(--red)' }}>
                          {h.pnl_pct!=null ? `${h.pnl_pct>=0?'+':''}${h.pnl_pct.toFixed(1)}%` : ''}
                        </div>
                      </td>
                      <td><SentimentBadge label={h.sentiment_label} /></td>
                      <td>
                        <button onClick={e => { e.stopPropagation(); handleDelete(h.id, h.ticker) }}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4, display: 'flex' }}
                          onMouseEnter={e => e.currentTarget.style.color = 'var(--red)'}
                          onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}>
                          <Trash2 size={13} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Technical Analysis Panel */}
            {selectedTicker && (
              <div className="card animate-fadeUp">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <div className="section-title">Technical Analysis — {selectedTicker}</div>
                  <div style={{ display: 'flex', gap: 6 }}>
                    <span className="badge badge-gold" style={{ fontSize: '0.68rem' }}>RSI · MACD · Bollinger</span>
                    <span className="badge badge-blue" style={{ fontSize: '0.68rem' }}>Gemini AI</span>
                  </div>
                </div>
                <TechnicalAnalysisPanel ticker={selectedTicker} />
              </div>
            )}
          </div>

          {/* Sector allocation */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="card animate-fadeUp">
              <div className="section-title" style={{ marginBottom: 18 }}>Sector Allocation</div>
              {sectorData.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={180}>
                    <PieChart>
                      <Pie data={sectorData} dataKey="value" nameKey="name" cx="50%" cy="50%" outerRadius={70} innerRadius={44} strokeWidth={0}>
                        {sectorData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip formatter={(v) => [`${v}%`, '']}
                        contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: '0.78rem' }} />
                    </PieChart>
                  </ResponsiveContainer>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
                    {sectorData.map((s, i) => (
                      <div key={s.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                          <div style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS[i % COLORS.length] }} />
                          <span style={{ fontSize: '0.78rem', color: 'var(--text-secondary)' }}>{s.name}</span>
                        </div>
                        <span style={{ fontSize: '0.78rem', fontFamily: 'var(--font-mono)', color: s.value > 60 ? 'var(--red)' : 'var(--text-primary)' }}>
                          {s.value}%{s.value > 60 && ' ⚠'}
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="empty-state"><BarChart2 size={28} /><p>No sector data</p></div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
