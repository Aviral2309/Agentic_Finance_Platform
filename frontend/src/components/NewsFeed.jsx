import { useEffect, useState } from 'react'
import { ExternalLink, TrendingUp, TrendingDown, Minus, RefreshCw, Newspaper } from 'lucide-react'
import api from '../services/api'

const SentimentIcon = ({ s }) => {
  if (s === 'bullish') return <TrendingUp size={12} color="var(--green)" />
  if (s === 'bearish') return <TrendingDown size={12} color="var(--red)" />
  return <Minus size={12} color="var(--text-muted)" />
}

const SentimentBadge = ({ sentiment }) => {
  const config = {
    bullish: { color: 'var(--green)', bg: 'var(--green-dim)', label: 'Bullish' },
    bearish: { color: 'var(--red)', bg: 'var(--red-dim)', label: 'Bearish' },
    neutral: { color: 'var(--text-secondary)', bg: 'var(--bg-elevated)', label: 'Neutral' },
  }[sentiment] || { color: 'var(--text-muted)', bg: 'var(--bg-elevated)', label: 'N/A' }

  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: 4, padding: '2px 8px', borderRadius: 99, fontSize: '0.7rem', fontWeight: 500, background: config.bg, color: config.color }}>
      <SentimentIcon s={sentiment} />
      {config.label}
    </span>
  )
}

export default function NewsFeed() {
  const [news, setNews] = useState([])
  const [loading, setLoading] = useState(true)
  const [filter, setFilter] = useState('all')

  async function loadNews() {
    setLoading(true)
    try {
      const { data } = await api.get('/features/news')
      setNews(data.articles || [])
    } catch {
      setNews([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { loadNews() }, [])

  const filtered = filter === 'portfolio'
    ? news.filter(n => n.affects_portfolio)
    : filter === 'bullish'
    ? news.filter(n => n.sentiment === 'bullish')
    : filter === 'bearish'
    ? news.filter(n => n.sentiment === 'bearish')
    : news

  return (
    <div className="card animate-fadeUp">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <div className="section-title">Market News</div>
          {news.filter(n => n.affects_portfolio).length > 0 && (
            <span style={{ padding: '2px 8px', background: 'var(--red-dim)', color: 'var(--red)', borderRadius: 99, fontSize: '0.68rem', fontWeight: 600 }}>
              {news.filter(n => n.affects_portfolio).length} affect your portfolio
            </span>
          )}
        </div>
        <button onClick={loadNews} disabled={loading} className="btn btn-ghost" style={{ padding: '5px 8px' }}>
          <RefreshCw size={13} style={{ animation: loading ? 'spin 1s linear infinite' : 'none' }} />
        </button>
      </div>

      {/* Filters */}
      <div style={{ display: 'flex', gap: 6, marginBottom: 14, flexWrap: 'wrap' }}>
        {[
          { id: 'all', label: 'All' },
          { id: 'portfolio', label: 'My Portfolio' },
          { id: 'bullish', label: 'Bullish' },
          { id: 'bearish', label: 'Bearish' },
        ].map(f => (
          <button key={f.id} onClick={() => setFilter(f.id)} style={{
            padding: '4px 10px', borderRadius: 99, fontSize: '0.74rem', cursor: 'pointer',
            background: filter === f.id ? 'var(--gold-muted)' : 'var(--bg-elevated)',
            border: `1px solid ${filter === f.id ? 'rgba(201,168,76,0.3)' : 'var(--bg-border)'}`,
            color: filter === f.id ? 'var(--gold)' : 'var(--text-secondary)',
            transition: 'all 0.15s',
          }}>{f.label}</button>
        ))}
      </div>

      {loading ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
          {[1, 2, 3].map(i => <div key={i} className="skeleton" style={{ height: 72, borderRadius: 8 }} />)}
        </div>
      ) : filtered.length === 0 ? (
        <div className="empty-state" style={{ padding: '24px 0' }}>
          <Newspaper size={28} />
          <p>No news articles matching this filter</p>
        </div>
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
          {filtered.map((article, i) => (
            <a key={i} href={article.url} target="_blank" rel="noopener noreferrer" style={{
              display: 'block', padding: '12px 14px',
              background: article.affects_portfolio ? 'rgba(201,168,76,0.05)' : 'var(--bg-elevated)',
              border: `1px solid ${article.affects_portfolio ? 'rgba(201,168,76,0.2)' : 'var(--bg-border)'}`,
              borderRadius: 'var(--radius-md)', textDecoration: 'none',
              transition: 'all 0.15s',
            }}
              onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(201,168,76,0.3)'}
              onMouseLeave={e => e.currentTarget.style.borderColor = article.affects_portfolio ? 'rgba(201,168,76,0.2)' : 'var(--bg-border)'}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', gap: 8, marginBottom: 6 }}>
                <div style={{ fontSize: '0.82rem', fontWeight: 500, color: 'var(--text-primary)', lineHeight: 1.4, flex: 1 }}>
                  {article.title}
                </div>
                <ExternalLink size={12} color="var(--text-muted)" style={{ flexShrink: 0, marginTop: 2 }} />
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, flexWrap: 'wrap' }}>
                <SentimentBadge sentiment={article.sentiment} />
                <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{article.source}</span>
                {article.affects_portfolio && article.portfolio_impact.length > 0 && (
                  <span style={{ fontSize: '0.68rem', color: 'var(--gold)', background: 'var(--gold-muted)', padding: '1px 6px', borderRadius: 99 }}>
                    Affects: {article.portfolio_impact.join(', ')}
                  </span>
                )}
              </div>
            </a>
          ))}
        </div>
      )}
    </div>
  )
}
