import { useEffect, useState } from 'react'
import {
  TrendingUp, TrendingDown, Plus, Trash2,
  RefreshCw, BarChart2, Activity, Info
} from 'lucide-react'
import {
  AreaChart, Area, XAxis, YAxis, Tooltip,
  ResponsiveContainer, PieChart, Pie, Cell, Legend
} from 'recharts'
import { portfolioApi } from '../services/api'
import toast from 'react-hot-toast'

const COLORS = ['#c9a84c', '#3b82f6', '#22c55e', '#8b5cf6', '#f59e0b', '#06b6d4', '#ec4899']

const SentimentBadge = ({ label }) => {
  const config = {
    bullish: { color: 'var(--green)', bg: 'var(--green-dim)', border: 'rgba(34,197,94,0.2)', icon: '↑' },
    bearish: { color: 'var(--red)',   bg: 'var(--red-dim)',   border: 'rgba(239,68,68,0.2)', icon: '↓' },
    neutral: { color: 'var(--text-secondary)', bg: 'var(--bg-elevated)', border: 'var(--bg-border)', icon: '→' },
  }[label] || { color: 'var(--text-muted)', bg: 'var(--bg-elevated)', border: 'var(--bg-border)', icon: '?' }

  return (
    <span style={{
      padding: '2px 8px', borderRadius: 99, fontSize: '0.72rem', fontWeight: 600,
      background: config.bg, color: config.color, border: `1px solid ${config.border}`,
      display: 'inline-flex', alignItems: 'center', gap: 3,
    }}>
      {config.icon} {label || 'N/A'}
    </span>
  )
}

function AddHoldingForm({ onAdd, onClose }) {
  const [form, setForm] = useState({ ticker: '', quantity: '', buy_price: '', exchange: 'NSE' })
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      const data = await portfolioApi.addHolding({
        ticker: form.ticker.toUpperCase(),
        quantity: parseFloat(form.quantity),
        buy_price: parseFloat(form.buy_price),
        exchange: form.exchange,
      })
      toast.success(`${form.ticker.toUpperCase()} added! Training LSTM model...`)
      onAdd()
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add holding')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{
      position: 'fixed', inset: 0, zIndex: 50,
      background: 'rgba(8,12,20,0.8)', backdropFilter: 'blur(4px)',
      display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20,
    }} onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="card animate-fadeUp" style={{ width: '100%', maxWidth: 400, padding: 32 }}>
        <h3 style={{ marginBottom: 4 }}>Add Holding</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.8rem', marginBottom: 24 }}>LSTM model will auto-train after adding</p>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
          <div>
            <label className="input-label">Ticker Symbol</label>
            <input className="input" placeholder="TCS, INFY, RELIANCE..." value={form.ticker}
              onChange={e => setForm(f => ({ ...f, ticker: e.target.value }))} required autoFocus />
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
          <div>
            <label className="input-label">Exchange</label>
            <select className="input" value={form.exchange} onChange={e => setForm(f => ({ ...f, exchange: e.target.value }))}
              style={{ cursor: 'pointer' }}>
              <option value="NSE">NSE (India)</option>
              <option value="BSE">BSE (India)</option>
              <option value="NASDAQ">NASDAQ (US)</option>
              <option value="NYSE">NYSE (US)</option>
            </select>
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

function ForecastChart({ ticker }) {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)
  const [view, setView] = useState('7d')

  useEffect(() => {
    portfolioApi.forecast(ticker)
      .then(r => setData(r.data))
      .catch(e => setError(e.response?.data?.detail || 'Model not ready yet'))
      .finally(() => setLoading(false))
  }, [ticker])

  if (loading) return (
    <div style={{ height: 180, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div className="spinner" />
    </div>
  )

  if (error) return (
    <div style={{ height: 120, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 8, color: 'var(--text-muted)', fontSize: '0.8rem', textAlign: 'center' }}>
      <Activity size={24} style={{ opacity: 0.3 }} />
      <p>{error}</p>
      <button onClick={() => portfolioApi.trainModel(ticker).then(() => toast.success('Training started!')).catch(() => {})}
        className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '5px 12px' }}>
        <RefreshCw size={12} /> Train Model
      </button>
    </div>
  )

  const points = view === '7d' ? data.forecast_7d : data.forecast_30d

  return (
    <div>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 12 }}>
        <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
          Current: <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>₹{data.current_price?.toLocaleString('en-IN')}</span>
          {data.model_mae_pct && <span style={{ marginLeft: 8, color: 'var(--text-muted)' }}>MAE: {data.model_mae_pct?.toFixed(1)}%</span>}
        </div>
        <div style={{ display: 'flex', gap: 4 }}>
          {['7d','30d'].map(v => (
            <button key={v} onClick={() => setView(v)} style={{
              padding: '3px 8px', fontSize: '0.7rem', borderRadius: 4,
              border: `1px solid ${view===v ? 'var(--gold-dim)' : 'var(--bg-border)'}`,
              background: view===v ? 'var(--gold-muted)' : 'transparent',
              color: view===v ? 'var(--gold)' : 'var(--text-muted)',
              cursor: 'pointer',
            }}>{v}</button>
          ))}
        </div>
      </div>
      <ResponsiveContainer width="100%" height={160}>
        <AreaChart data={points}>
          <defs>
            <linearGradient id={`grad-${ticker}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#c9a84c" stopOpacity={0.3} />
              <stop offset="95%" stopColor="#c9a84c" stopOpacity={0} />
            </linearGradient>
            <linearGradient id={`band-${ticker}`} x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#3b82f6" stopOpacity={0.1} />
              <stop offset="95%" stopColor="#3b82f6" stopOpacity={0} />
            </linearGradient>
          </defs>
          <XAxis dataKey="date" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} axisLine={false} tickLine={false}
            tickFormatter={d => d?.slice(5)} />
          <YAxis hide domain={['auto','auto']} />
          <Tooltip
            formatter={(v, n) => [`₹${Number(v).toLocaleString('en-IN')}`, n]}
            contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: '0.75rem' }}
          />
          <Area type="monotone" dataKey="upper_band" stroke="none" fill={`url(#band-${ticker})`} />
          <Area type="monotone" dataKey="lower_band" stroke="none" fill={`url(#band-${ticker})`} />
          <Area type="monotone" dataKey="predicted_price" stroke="#c9a84c" strokeWidth={2} fill={`url(#grad-${ticker})`} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  )
}

export default function PortfolioPage() {
  const [portfolio, setPortfolio] = useState(null)
  const [loading, setLoading] = useState(true)
  const [showAddForm, setShowAddForm] = useState(false)
  const [selectedTicker, setSelectedTicker] = useState(null)

  async function loadPortfolio() {
    try {
      const { data } = await portfolioApi.summary()
      setPortfolio(data)
      if (data.holdings?.length > 0 && !selectedTicker) {
        setSelectedTicker(data.holdings[0].ticker)
      }
    } catch (err) {
      toast.error('Failed to load portfolio')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadPortfolio() }, [])

  async function handleDelete(id, ticker) {
    if (!confirm(`Remove ${ticker} from portfolio?`)) return
    try {
      await portfolioApi.deleteHolding(id)
      toast.success(`${ticker} removed`)
      loadPortfolio()
    } catch { toast.error('Failed to remove') }
  }

  if (loading) return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', height: 400, gap: 12, color: 'var(--text-muted)' }}>
      <div className="spinner" />
      <span>Loading portfolio...</span>
    </div>
  )

  const holdings = portfolio?.holdings || []
  const sectorData = Object.entries(portfolio?.allocation_by_sector || {}).map(([name, value]) => ({ name, value }))

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      {showAddForm && <AddHoldingForm onAdd={loadPortfolio} onClose={() => setShowAddForm(false)} />}

      {/* Header */}
      <div className="animate-fadeUp" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', marginBottom: 4 }}>Portfolio</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Live prices · LSTM forecasts · FinBERT sentiment</p>
        </div>
        <button onClick={() => setShowAddForm(true)} className="btn btn-primary">
          <Plus size={15} /> Add Holding
        </button>
      </div>

      {/* Summary stats */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: 14 }} className="stagger">
        {[
          { label: 'Invested', value: `₹${(portfolio?.total_invested||0).toLocaleString('en-IN',{maximumFractionDigits:0})}`, color: 'var(--text-primary)' },
          { label: 'Current Value', value: `₹${(portfolio?.current_value||0).toLocaleString('en-IN',{maximumFractionDigits:0})}`, color: 'var(--text-primary)' },
          { label: 'Total P&L', value: `${(portfolio?.total_pnl||0)>=0?'+':''}₹${Math.abs(portfolio?.total_pnl||0).toLocaleString('en-IN',{maximumFractionDigits:0})}`, color: (portfolio?.total_pnl||0)>=0?'var(--green)':'var(--red)' },
          { label: 'Sharpe Ratio', value: portfolio?.sharpe_ratio ? portfolio.sharpe_ratio.toFixed(2) : 'N/A', color: 'var(--gold)' },
        ].map(s => (
          <div key={s.label} className="card animate-fadeUp" style={{ padding: '18px 20px' }}>
            <div className="stat-label" style={{ marginBottom: 8 }}>{s.label}</div>
            <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.35rem', fontWeight: 600, color: s.color }}>{s.value}</div>
          </div>
        ))}
      </div>

      {holdings.length === 0 ? (
        <div className="card animate-fadeUp">
          <div className="empty-state" style={{ padding: '60px 24px' }}>
            <TrendingUp size={48} />
            <h3 style={{ fontFamily: 'var(--font-display)' }}>No holdings yet</h3>
            <p>Add your stocks and mutual funds to get LSTM price forecasts and FinBERT sentiment analysis</p>
            <button onClick={() => setShowAddForm(true)} className="btn btn-primary">
              <Plus size={15} /> Add your first holding
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 20, alignItems: 'start' }}>

          {/* Holdings table + forecast */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

            {/* Holdings */}
            <div className="card animate-fadeUp" style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ padding: '20px 20px 16px' }}>
                <div className="section-title">Holdings</div>
              </div>
              <table className="table">
                <thead>
                  <tr>
                    <th>Stock</th>
                    <th>Qty</th>
                    <th>Buy Price</th>
                    <th>Current</th>
                    <th>P&L</th>
                    <th>Sentiment</th>
                    <th></th>
                  </tr>
                </thead>
                <tbody>
                  {holdings.map(h => (
                    <tr
                      key={h.id}
                      onClick={() => setSelectedTicker(h.ticker)}
                      style={{ cursor: 'pointer', background: selectedTicker === h.ticker ? 'var(--gold-muted)' : 'transparent' }}
                    >
                      <td>
                        <div style={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '0.875rem' }}>{h.ticker}</div>
                        <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>{h.company_name?.slice(0,20) || h.exchange}</div>
                      </td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>{h.quantity}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem' }}>₹{h.buy_price?.toLocaleString('en-IN')}</td>
                      <td style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: 'var(--text-primary)' }}>
                        {h.current_price ? `₹${h.current_price?.toLocaleString('en-IN')}` : '—'}
                      </td>
                      <td>
                        <div style={{ fontFamily: 'var(--font-mono)', fontSize: '0.85rem', color: (h.pnl||0)>=0?'var(--green)':'var(--red)' }}>
                          {h.pnl != null ? `${h.pnl>=0?'+':''}₹${Math.abs(h.pnl).toLocaleString('en-IN',{maximumFractionDigits:0})}` : '—'}
                        </div>
                        <div style={{ fontSize: '0.7rem', color: (h.pnl_pct||0)>=0?'var(--green)':'var(--red)' }}>
                          {h.pnl_pct != null ? `${h.pnl_pct>=0?'+':''}${h.pnl_pct?.toFixed(2)}%` : ''}
                        </div>
                      </td>
                      <td><SentimentBadge label={h.sentiment_label} /></td>
                      <td>
                        <button onClick={e => { e.stopPropagation(); handleDelete(h.id, h.ticker) }}
                          style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4, display: 'flex' }}
                          onMouseEnter={e => e.currentTarget.style.color='var(--red)'}
                          onMouseLeave={e => e.currentTarget.style.color='var(--text-muted)'}>
                          <Trash2 size={13} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* LSTM Forecast */}
            {selectedTicker && (
              <div className="card animate-fadeUp">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <div className="section-title">
                    LSTM Forecast — {selectedTicker}
                  </div>
                  <span className="badge badge-gold" style={{ fontSize: '0.7rem' }}>
                    Monte Carlo · ±1σ bands
                  </span>
                </div>
                <ForecastChart ticker={selectedTicker} />
                <div style={{ marginTop: 10, padding: '8px 12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-sm)', fontSize: '0.72rem', color: 'var(--text-muted)' }}>
                  <Info size={11} style={{ display: 'inline', marginRight: 4 }} />
                  LSTM forecasts are for educational purposes. Past performance does not predict future results.
                </div>
              </div>
            )}
          </div>

          {/* Right: sector allocation */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
            <div className="card animate-fadeUp">
              <div className="section-title" style={{ marginBottom: 20 }}>Sector Allocation</div>
              {sectorData.length > 0 ? (
                <>
                  <ResponsiveContainer width="100%" height={200}>
                    <PieChart>
                      <Pie data={sectorData} dataKey="value" nameKey="name" cx="50%" cy="50%"
                        outerRadius={80} innerRadius={48} strokeWidth={0}>
                        {sectorData.map((_, i) => <Cell key={i} fill={COLORS[i % COLORS.length]} />)}
                      </Pie>
                      <Tooltip
                        formatter={(v) => [`${v}%`, '']}
                        contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: '0.8rem' }}
                      />
                    </PieChart>
                  </ResponsiveContainer>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 8, marginTop: 8 }}>
                    {sectorData.map((s, i) => (
                      <div key={s.name} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <div style={{ width: 8, height: 8, borderRadius: '50%', background: COLORS[i % COLORS.length] }} />
                          <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{s.name}</span>
                        </div>
                        <span style={{ fontSize: '0.8rem', fontFamily: 'var(--font-mono)', color: s.value > 60 ? 'var(--red)' : 'var(--text-primary)' }}>
                          {s.value}%
                          {s.value > 60 && <span style={{ marginLeft: 4, color: 'var(--red)', fontSize: '0.7rem' }}>⚠</span>}
                        </span>
                      </div>
                    ))}
                  </div>
                </>
              ) : (
                <div className="empty-state"><BarChart2 size={32} /><p>Sector data unavailable</p></div>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
