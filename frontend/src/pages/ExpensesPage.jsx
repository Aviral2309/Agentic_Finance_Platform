import { useEffect, useState, useCallback, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  Upload, FileText, CheckCircle2, AlertCircle,
  Trash2, Check, X, TrendingUp, TrendingDown,
  Lightbulb, ChevronLeft, ChevronRight, Plus,
  Calendar, BarChart2, AlertTriangle
} from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'
import { expensesApi } from '../services/api'
import api from '../services/api'
import toast from 'react-hot-toast'

const CATEGORY_COLORS = {
  'Food & Dining':    '#f59e0b',
  'Groceries':        '#22c55e',
  'Transport':        '#3b82f6',
  'Shopping':         '#8b5cf6',
  'Entertainment':    '#ec4899',
  'Bills & Utilities':'#06b6d4',
  'Healthcare':       '#ef4444',
  'Education':        '#10b981',
  'Travel':           '#f97316',
  'EMI & Loans':      '#dc2626',
  'Investment':       '#c9a84c',
  'Salary & Income':  '#22c55e',
  'Transfers':        '#6b7280',
  'ATM Withdrawal':   '#9ca3af',
  'Other':            '#4b5563',
}

function getCategoryColor(cat) {
  return CATEGORY_COLORS[cat] || '#6b7280'
}

// ── Upload Zone ────────────────────────────────────────────────
function UploadZone({ onUpload }) {
  const [uploading, setUploading] = useState(false)

  const onDrop = useCallback(async (files) => {
    if (!files.length) return
    setUploading(true)
    try {
      const { data } = await expensesApi.upload(files[0])
      onUpload(data)
      toast.success('Statement uploaded! Processing...')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }, [onUpload])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: { 'application/pdf': ['.pdf'], 'text/csv': ['.csv'] },
    maxFiles: 1,
    disabled: uploading,
  })

  return (
    <div {...getRootProps()} style={{
      border: `2px dashed ${isDragActive ? 'var(--gold)' : 'var(--bg-border)'}`,
      borderRadius: 'var(--radius-lg)',
      padding: '28px 20px',
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      gap: 10, cursor: uploading ? 'not-allowed' : 'pointer',
      background: isDragActive ? 'var(--gold-muted)' : 'var(--bg-elevated)',
      transition: 'all 0.2s', textAlign: 'center',
    }}>
      <input {...getInputProps()} />
      {uploading ? (
        <><div className="spinner" style={{ width: 28, height: 28 }} />
        <p style={{ fontSize: '0.85rem', color: 'var(--text-muted)' }}>Uploading...</p></>
      ) : (
        <>
          <div style={{ width: 48, height: 48, borderRadius: 14, background: 'var(--gold-muted)', border: '1px solid rgba(201,168,76,0.3)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Upload size={22} color="var(--gold)" />
          </div>
          <div>
            <p style={{ fontWeight: 500, color: 'var(--text-primary)', fontSize: '0.9rem', marginBottom: 3 }}>
              {isDragActive ? 'Drop here' : 'Upload bank statement'}
            </p>
            <p style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>PDF or CSV · SBI, HDFC, ICICI, Axis, Kotak</p>
          </div>
          <div className="btn btn-secondary" style={{ fontSize: '0.78rem', padding: '6px 14px' }}>Browse files</div>
        </>
      )}
    </div>
  )
}

// ── Job Progress ───────────────────────────────────────────────
function JobProgress({ job, onComplete }) {
  const [status, setStatus] = useState(job)
  const intervalRef = useRef()

  useEffect(() => {
    if (['done', 'partial', 'failed'].includes(status?.status)) return
    intervalRef.current = setInterval(async () => {
      try {
        const { data } = await expensesApi.jobStatus(job.job_id)
        setStatus(data)
        if (['done', 'partial', 'failed'].includes(data.status)) {
          clearInterval(intervalRef.current)
          if (data.status !== 'failed') onComplete()
        }
      } catch {}
    }, 2000)
    return () => clearInterval(intervalRef.current)
  }, [])

  const pct = status?.progress_pct || 0
  const isDone = ['done', 'partial'].includes(status?.status)
  const isFailed = status?.status === 'failed'

  return (
    <div style={{
      padding: '12px 16px', background: 'var(--bg-elevated)',
      border: `1px solid ${isDone ? 'rgba(34,197,94,0.3)' : isFailed ? 'rgba(239,68,68,0.3)' : 'var(--bg-border)'}`,
      borderRadius: 'var(--radius-md)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: isDone || isFailed ? 0 : 8 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
          <FileText size={13} color="var(--text-muted)" />
          <span style={{ fontSize: '0.8rem', color: 'var(--text-primary)' }}>{status?.filename}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 5 }}>
          {isDone && <CheckCircle2 size={13} color="var(--green)" />}
          {isFailed && <AlertCircle size={13} color="var(--red)" />}
          <span style={{ fontSize: '0.72rem', color: isDone ? 'var(--green)' : isFailed ? 'var(--red)' : 'var(--text-muted)' }}>
            {isDone ? `${status?.transactions_found} transactions found` : isFailed ? 'Failed' : `${pct.toFixed(0)}%`}
          </span>
        </div>
      </div>
      {!isDone && !isFailed && (
        <div className="progress-bar"><div className="progress-fill" style={{ width: `${pct}%` }} /></div>
      )}
    </div>
  )
}

// ── Statement Library ──────────────────────────────────────────
function StatementLibrary({ onRefresh }) {
  const [jobs, setJobs] = useState([])
  const [loading, setLoading] = useState(true)

  async function load() {
    try {
      const { data } = await api.get('/expenses/statements')
      setJobs(data)
    } catch {
      // endpoint might not exist yet — fetch from jobs
      setJobs([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  async function deleteStatement(jobId) {
    if (!confirm('Delete this statement and all its transactions?')) return
    try {
      await api.delete(`/expenses/statements/${jobId}`)
      toast.success('Statement deleted')
      load()
      onRefresh()
    } catch {
      toast.error('Failed to delete')
    }
  }

  if (loading) return <div className="skeleton" style={{ height: 60 }} />

  if (jobs.length === 0) return (
    <div className="empty-state" style={{ padding: '20px 0' }}>
      <FileText size={28} />
      <p>No statements uploaded yet</p>
    </div>
  )

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
      {jobs.map(job => (
        <div key={job.job_id} style={{
          display: 'flex', justifyContent: 'space-between', alignItems: 'center',
          padding: '10px 14px', background: 'var(--bg-elevated)',
          border: '1px solid var(--bg-border)', borderRadius: 'var(--radius-md)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
            <FileText size={14} color="var(--gold)" />
            <div>
              <div style={{ fontSize: '0.82rem', fontWeight: 500, color: 'var(--text-primary)' }}>{job.filename}</div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>
                {job.transactions_found} transactions · {new Date(job.created_at).toLocaleDateString('en-IN')}
              </div>
            </div>
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span className="badge badge-green" style={{ fontSize: '0.65rem' }}>✓ Processed</span>
            <button onClick={() => deleteStatement(job.job_id)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', color: 'var(--text-muted)', padding: 4, display: 'flex' }}
              onMouseEnter={e => e.currentTarget.style.color = 'var(--red)'}
              onMouseLeave={e => e.currentTarget.style.color = 'var(--text-muted)'}>
              <Trash2 size={13} />
            </button>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── HITL Card ──────────────────────────────────────────────────
function HITLCard({ item, onConfirm }) {
  const [selected, setSelected] = useState(item.suggested_category)
  const [custom, setCustom] = useState('')
  const [loading, setLoading] = useState(false)

  async function confirm() {
    setLoading(true)
    try {
      await expensesApi.confirmHitl({ transaction_id: item.transaction_id, confirmed_category: custom || selected })
      toast.success('Confirmed')
      onConfirm(item.hitl_id)
    } catch { toast.error('Failed') }
    finally { setLoading(false) }
  }

  return (
    <div style={{ padding: '14px', background: 'var(--bg-card)', border: '1px solid var(--bg-border)', borderRadius: 'var(--radius-md)' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
        <div>
          <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)', fontWeight: 500 }}>{item.description?.slice(0, 45)}</div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>
            {new Date(item.date).toLocaleDateString('en-IN')} · ₹{item.amount?.toLocaleString('en-IN')}
          </div>
        </div>
        <span className="badge badge-amber" style={{ fontSize: '0.65rem', alignSelf: 'flex-start' }}>Review</span>
      </div>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 5, marginBottom: 8 }}>
        {[item.suggested_category, ...(item.alternative_categories || []).filter(c => c !== item.suggested_category)].filter(Boolean).map(cat => (
          <button key={cat} onClick={() => { setSelected(cat); setCustom('') }} style={{
            padding: '3px 9px', borderRadius: 99, fontSize: '0.72rem', cursor: 'pointer',
            border: `1px solid ${selected === cat ? getCategoryColor(cat) : 'var(--bg-border)'}`,
            background: selected === cat ? `${getCategoryColor(cat)}20` : 'transparent',
            color: selected === cat ? getCategoryColor(cat) : 'var(--text-secondary)',
            transition: 'all 0.15s',
          }}>{cat}</button>
        ))}
      </div>
      <div style={{ display: 'flex', gap: 6 }}>
        <input className="input" placeholder="Custom category..." value={custom}
          onChange={e => setCustom(e.target.value)}
          style={{ flex: 1, padding: '6px 10px', fontSize: '0.78rem' }} />
        <button onClick={confirm} disabled={loading} className="btn btn-primary" style={{ padding: '6px 12px', fontSize: '0.78rem' }}>
          {loading ? <div className="spinner" style={{ width: 13, height: 13 }} /> : <><Check size={12} /> OK</>}
        </button>
      </div>
    </div>
  )
}

// ── Smart Insights ─────────────────────────────────────────────
function SmartInsights({ summary, trends }) {
  const insights = []

  if (!summary || !summary.categories) return null

  const categories = summary.categories || []
  const total = summary.total || 0

  // Find top spending category
  if (categories.length > 0) {
    const top = categories[0]
    if (top.percentage > 35) {
      insights.push({
        type: 'warning',
        icon: AlertTriangle,
        text: `${top.category} is ${top.percentage}% of your total spending — ₹${top.total.toLocaleString('en-IN', { maximumFractionDigits: 0 })}. Consider setting a budget limit.`,
      })
    }
  }

  // Month over month comparison
  if (trends && trends.length >= 2) {
    const thisMonth = trends[trends.length - 1]
    const lastMonth = trends[trends.length - 2]
    if (thisMonth && lastMonth && lastMonth.total_debit > 0) {
      const change = ((thisMonth.total_debit - lastMonth.total_debit) / lastMonth.total_debit) * 100
      if (change > 20) {
        insights.push({
          type: 'warning',
          icon: TrendingUp,
          text: `Spending up ${change.toFixed(0)}% vs last month — ₹${(thisMonth.total_debit - lastMonth.total_debit).toLocaleString('en-IN', { maximumFractionDigits: 0 })} more than usual.`,
        })
      } else if (change < -10) {
        insights.push({
          type: 'success',
          icon: TrendingDown,
          text: `Great job! Spending down ${Math.abs(change).toFixed(0)}% vs last month — you saved ₹${Math.abs(thisMonth.total_debit - lastMonth.total_debit).toLocaleString('en-IN', { maximumFractionDigits: 0 })} more.`,
        })
      }
    }

    // Savings rate
    const income = trends[trends.length - 1]?.total_credit || 0
    if (income > 0) {
      const savingsRate = ((income - total) / income) * 100
      if (savingsRate < 20) {
        insights.push({
          type: 'warning',
          icon: Lightbulb,
          text: `Savings rate is ${savingsRate.toFixed(0)}% — below the recommended 20%. Try reducing discretionary spending.`,
        })
      } else {
        insights.push({
          type: 'success',
          icon: Lightbulb,
          text: `Good savings rate of ${savingsRate.toFixed(0)}% this month. Keep it up!`,
        })
      }
    }
  }

  // EMI check
  const emi = categories.find(c => c.category === 'EMI & Loans')
  const income = trends?.[trends.length - 1]?.total_credit || 0
  if (emi && income > 0) {
    const emiRatio = (emi.total / income) * 100
    if (emiRatio > 30) {
      insights.push({
        type: 'warning',
        icon: AlertTriangle,
        text: `EMI payments are ${emiRatio.toFixed(0)}% of income — above the safe 30% threshold. Review loan obligations.`,
      })
    }
  }

  if (insights.length === 0) {
    insights.push({
      type: 'success',
      icon: CheckCircle2,
      text: 'Your spending looks balanced this month. No major issues detected.',
    })
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {insights.map((ins, i) => (
        <div key={i} style={{
          display: 'flex', alignItems: 'flex-start', gap: 10,
          padding: '10px 14px', borderRadius: 'var(--radius-md)',
          background: ins.type === 'warning' ? 'rgba(245,158,11,0.08)' : 'var(--green-dim)',
          border: `1px solid ${ins.type === 'warning' ? 'rgba(245,158,11,0.2)' : 'rgba(34,197,94,0.2)'}`,
        }}>
          <ins.icon size={14} color={ins.type === 'warning' ? 'var(--amber)' : 'var(--green)'} style={{ flexShrink: 0, marginTop: 2 }} />
          <span style={{ fontSize: '0.8rem', color: ins.type === 'warning' ? 'var(--amber)' : 'var(--green)', lineHeight: 1.5 }}>{ins.text}</span>
        </div>
      ))}
    </div>
  )
}

// ── Manual Add Modal ───────────────────────────────────────────
function ManualAddModal({ onClose, onAdd }) {
  const [form, setForm] = useState({
    date: new Date().toISOString().slice(0, 10),
    amount: '',
    description: '',
    transaction_type: 'debit',
    category: '',
  })
  const [loading, setLoading] = useState(false)

  async function handleSubmit(e) {
    e.preventDefault()
    setLoading(true)
    try {
      await api.post('/expenses/transactions/manual', {
        ...form,
        date: new Date(form.date).toISOString(),
        amount: parseFloat(form.amount),
      })
      toast.success('Transaction added')
      onAdd()
      onClose()
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to add')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div style={{ position: 'fixed', inset: 0, zIndex: 50, background: 'rgba(8,12,20,0.8)', backdropFilter: 'blur(4px)', display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 20 }}
      onClick={e => e.target === e.currentTarget && onClose()}>
      <div className="card animate-fadeUp" style={{ width: '100%', maxWidth: 380, padding: 28 }}>
        <h3 style={{ marginBottom: 4 }}>Add Transaction</h3>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.78rem', marginBottom: 20 }}>Manually enter an expense or income</p>
        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
          <div>
            <label className="input-label">Date</label>
            <input className="input" type="date" value={form.date}
              onChange={e => setForm(f => ({ ...f, date: e.target.value }))} required style={{ fontSize: '0.85rem' }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10 }}>
            <div>
              <label className="input-label">Amount (₹)</label>
              <input className="input" type="number" placeholder="500" value={form.amount}
                onChange={e => setForm(f => ({ ...f, amount: e.target.value }))} required min="1" style={{ fontSize: '0.85rem' }} />
            </div>
            <div>
              <label className="input-label">Type</label>
              <select className="input" value={form.transaction_type}
                onChange={e => setForm(f => ({ ...f, transaction_type: e.target.value }))} style={{ fontSize: '0.85rem', cursor: 'pointer' }}>
                <option value="debit">Expense</option>
                <option value="credit">Income</option>
              </select>
            </div>
          </div>
          <div>
            <label className="input-label">Description</label>
            <input className="input" placeholder="Swiggy order, Salary credit..." value={form.description}
              onChange={e => setForm(f => ({ ...f, description: e.target.value }))} required style={{ fontSize: '0.85rem' }} />
          </div>
          <div>
            <label className="input-label">Category (optional — auto-detected)</label>
            <input className="input" placeholder="Food & Dining, Transport..." value={form.category}
              onChange={e => setForm(f => ({ ...f, category: e.target.value }))} style={{ fontSize: '0.85rem' }} />
          </div>
          <div style={{ display: 'flex', gap: 8, marginTop: 4 }}>
            <button type="button" onClick={onClose} className="btn btn-ghost" style={{ flex: 1, justifyContent: 'center' }}>Cancel</button>
            <button type="submit" disabled={loading} className="btn btn-primary" style={{ flex: 1, justifyContent: 'center' }}>
              {loading ? <div className="spinner" style={{ width: 15, height: 15 }} /> : 'Add'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}

// ── Main Page ──────────────────────────────────────────────────
export default function ExpensesPage() {
  const [activeJobs, setActiveJobs] = useState([])
  const [summary, setSummary] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [hitlQueue, setHitlQueue] = useState([])
  const [trends, setTrends] = useState([])
  const [budgets, setBudgets] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeMonth, setActiveMonth] = useState(null)
  const [availableMonths, setAvailableMonths] = useState([])
  const [showBudgetForm, setShowBudgetForm] = useState(false)
  const [showManualAdd, setShowManualAdd] = useState(false)
  const [newBudget, setNewBudget] = useState({ category: '', monthly_limit: '' })
  const [activeTab, setActiveTab] = useState('overview')

  async function loadData(month = activeMonth) {
    try {
      const [sumRes, txRes, hitlRes, trendRes, budgetRes] = await Promise.allSettled([
        expensesApi.summary(activeMonth),
        expensesApi.transactions({ limit: 100, month }),
        expensesApi.hitlQueue(),
        expensesApi.trends(6),
        expensesApi.budgets(),
      ])
      if (sumRes.status === 'fulfilled') setSummary(sumRes.value.data)
      if (txRes.status === 'fulfilled') {
        setTransactions(txRes.value.data)
        // Extract available months
        const months = [...new Set(txRes.value.data.map(t => t.date?.slice(0, 7)))].sort().reverse()
        setAvailableMonths(months)
      }
      if (hitlRes.status === 'fulfilled') setHitlQueue(hitlRes.value.data)
      if (trendRes.status === 'fulfilled') setTrends(trendRes.value.data)
      if (budgetRes.status === 'fulfilled') setBudgets(budgetRes.value.data)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
  setActiveJobs([])
  loadData()
}, [activeMonth])

  async function handleAddBudget(e) {
    e.preventDefault()
    try {
      await expensesApi.createBudget({ category: newBudget.category, monthly_limit: parseFloat(newBudget.monthly_limit) })
      toast.success('Budget set')
      setShowBudgetForm(false)
      setNewBudget({ category: '', monthly_limit: '' })
      loadData()
    } catch { toast.error('Failed') }
  }

  function navigateMonth(dir) {
    if (!availableMonths.length) return
    const currentIndex = activeMonth ? availableMonths.indexOf(activeMonth) : 0
    const newIndex = currentIndex + dir
    if (newIndex >= 0 && newIndex < availableMonths.length) {
      setActiveMonth(availableMonths[newIndex])
    } else if (newIndex < 0) {
      setActiveMonth(null) // current month
    }
  }

  const categories = summary?.categories || []
  const total = summary?.total || 0

  const tabs = [
    { id: 'overview', label: 'Overview' },
    { id: 'transactions', label: `Transactions (${transactions.length})` },
    { id: 'budgets', label: 'Budgets' },
    { id: 'statements', label: 'Statements' },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>

      {showManualAdd && <ManualAddModal onClose={() => setShowManualAdd(false)} onAdd={() => { loadData(); setShowManualAdd(false) }} />}

      {/* Header */}
      <div className="animate-fadeUp" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', marginBottom: 4 }}>Expense Tracker</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Upload statements · Track spending · Set budgets</p>
        </div>
      <div style={{ display: 'flex', gap: 8 }}>
          <button onClick={() => setShowManualAdd(true)} className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '8px 14px' }}>
            <Plus size={14} /> Add Manual
          </button>
        </div>
      </div>

      {/* Upload zone — show when no transactions */}
      {transactions.length === 0 && (
        <UploadZone onUpload={(job) => setActiveJobs(prev => [job, ...prev])} />
      )}

      {/* Active jobs — only show queued/processing */}
      {activeJobs.filter(j => j.status === 'queued' || j.status === 'processing').length > 0 && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
          {activeJobs
            .filter(j => !['done', 'partial', 'failed'].includes(j.status))
            .map(job => (
              <JobProgress key={job.job_id} job={job} onComplete={() => { setActiveJobs([]); setTimeout(loadData, 1500) }} />
            ))}
        </div>
      )}

      {/* HITL queue */}
      {hitlQueue.length > 0 && (
        <div className="card" style={{ padding: 20 }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <div className="section-title" style={{ fontSize: '0.95rem' }}>
              Needs Your Review
              <span className="badge badge-amber" style={{ marginLeft: 8, fontSize: '0.68rem' }}>{hitlQueue.length}</span>
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
            {hitlQueue.slice(0, 3).map(item => (
              <HITLCard key={item.hitl_id} item={item}
                onConfirm={(id) => { setHitlQueue(q => q.filter(i => i.hitl_id !== id)); loadData() }} />
            ))}
          </div>
        </div>
      )}

      <>
          {/* Month navigator */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button onClick={() => navigateMonth(1)} className="btn btn-ghost" style={{ padding: '6px 10px' }}>
              <ChevronLeft size={15} />
            </button>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <Calendar size={14} color="var(--gold)" />
              <span style={{ fontSize: '0.9rem', fontWeight: 500 }}>
                {activeMonth ? new Date(activeMonth + '-01').toLocaleDateString('en-IN', { month: 'long', year: 'numeric' }) : 'All Time'}
              </span>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>· ₹{total.toLocaleString('en-IN', { maximumFractionDigits: 0 })} spent</span>
            </div>
            <button onClick={() => navigateMonth(-1)} className="btn btn-ghost" style={{ padding: '6px 10px' }} disabled={!activeMonth}>
              <ChevronRight size={15} />
            </button>
            {activeMonth && (
              <button onClick={() => setActiveMonth(null)} className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '5px 10px' }}>
                All Time
              </button>
            )}
          </div>

          {/* Tabs */}
          <div style={{ display: 'flex', gap: 4, borderBottom: '1px solid var(--bg-border)', paddingBottom: 0 }}>
            {tabs.map(tab => (
              <button key={tab.id} onClick={() => setActiveTab(tab.id)} style={{
                padding: '8px 16px', background: 'none', border: 'none',
                borderBottom: `2px solid ${activeTab === tab.id ? 'var(--gold)' : 'transparent'}`,
                color: activeTab === tab.id ? 'var(--gold)' : 'var(--text-muted)',
                fontSize: '0.85rem', fontWeight: activeTab === tab.id ? 500 : 400,
                cursor: 'pointer', transition: 'all 0.15s', marginBottom: -1,
              }}>{tab.label}</button>
            ))}
          </div>

          {/* Tab content */}
          {activeTab === 'overview' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 340px', gap: 18, alignItems: 'start' }}>
              {/* Category breakdown */}
              <div className="card animate-fadeUp">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
                  <div className="section-title">Category Breakdown</div>
                  <span style={{ fontSize: '0.85rem', fontFamily: 'var(--font-mono)', color: 'var(--gold)' }}>
                    ₹{total.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                  </span>
                </div>
                {categories.length > 0 ? (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                    {categories.map(cat => (
                      <div key={cat.category}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                            <div style={{ width: 10, height: 10, borderRadius: '50%', background: getCategoryColor(cat.category), flexShrink: 0 }} />
                            <span style={{ fontSize: '0.82rem', color: 'var(--text-primary)' }}>{cat.category}</span>
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{cat.count} txns</span>
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                            <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>{cat.percentage}%</span>
                            <span style={{ fontSize: '0.82rem', fontFamily: 'var(--font-mono)', color: 'var(--text-primary)', minWidth: 80, textAlign: 'right' }}>
                              ₹{cat.total.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                            </span>
                          </div>
                        </div>
                        <div style={{ height: 6, background: 'var(--bg-elevated)', borderRadius: 99, overflow: 'hidden' }}>
                          <div style={{ height: '100%', width: `${cat.percentage}%`, background: getCategoryColor(cat.category), borderRadius: 99, opacity: 0.8, transition: 'width 0.6s ease' }} />
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="empty-state"><BarChart2 size={32} /><p>No expense data for this period</p></div>
                )}
              </div>

              {/* Right column */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
                {/* Smart insights */}
                <div className="card" style={{ padding: 18 }}>
                  <div className="section-title" style={{ marginBottom: 14, fontSize: '0.9rem' }}>
                    <Lightbulb size={14} color="var(--gold)" /> Smart Insights
                  </div>
                  <SmartInsights summary={summary} trends={trends} />
                </div>

                {/* Spending trend mini chart */}
                <div className="card" style={{ padding: 18 }}>
                  <div className="section-title" style={{ marginBottom: 14, fontSize: '0.9rem' }}>6-Month Trend</div>
                  {trends.length > 0 ? (
                    <ResponsiveContainer width="100%" height={120}>
                      <BarChart data={trends} barSize={20}>
                        <XAxis dataKey="month" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} axisLine={false} tickLine={false}
                          tickFormatter={m => m?.slice(5)} />
                        <YAxis hide />
                        <Tooltip
                          formatter={(v) => [`₹${Number(v).toLocaleString('en-IN')}`, 'Spent']}
                          contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: '0.75rem' }} />
                        <Bar dataKey="total_debit" radius={[4, 4, 0, 0]}>
                          {trends.map((_, i) => (
                            <Cell key={i} fill={i === trends.length - 1 ? 'var(--gold)' : 'var(--bg-hover)'} />
                          ))}
                        </Bar>
                      </BarChart>
                    </ResponsiveContainer>
                  ) : (
                    <div className="empty-state" style={{ padding: '16px 0' }}><p>No trend data</p></div>
                  )}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'transactions' && (
            <div className="card animate-fadeUp" style={{ padding: 0, overflow: 'hidden' }}>
              <div style={{ padding: '16px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div className="section-title" style={{ fontSize: '0.95rem' }}>Transactions</div>
                <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{transactions.length} entries</span>
              </div>
              <div style={{ overflowX: 'auto' }}>
                <table className="table">
                  <thead>
                    <tr><th>Date</th><th>Description</th><th>Category</th><th>Layer</th><th style={{ textAlign: 'right' }}>Amount</th></tr>
                  </thead>
                  <tbody>
                    {transactions.map(tx => (
                      <tr key={tx.id}>
                        <td style={{ whiteSpace: 'nowrap', fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                          {new Date(tx.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: '2-digit' })}
                        </td>
                        <td style={{ maxWidth: 200 }}>
                          <div style={{ fontSize: '0.82rem', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {tx.description?.slice(0, 38)}
                          </div>
                          {tx.is_recurring && <span style={{ fontSize: '0.68rem', color: 'var(--blue)' }}>↻ Recurring</span>}
                        </td>
                        <td>
                          {tx.category ? (
                            <span style={{
                              display: 'inline-flex', alignItems: 'center', gap: 5,
                              padding: '2px 8px', borderRadius: 99, fontSize: '0.7rem', fontWeight: 500,
                              background: `${getCategoryColor(tx.category)}18`,
                              color: getCategoryColor(tx.category),
                              border: `1px solid ${getCategoryColor(tx.category)}30`,
                            }}>{tx.category}</span>
                          ) : <span style={{ color: 'var(--text-muted)', fontSize: '0.78rem' }}>—</span>}
                        </td>
                        <td>
                          <span style={{ fontSize: '0.68rem', color: 'var(--text-muted)' }}>
                            {tx.categorization_layer ? `L${tx.categorization_layer}` : '—'}
                            {tx.is_confirmed && <span style={{ color: 'var(--green)', marginLeft: 3 }}>✓</span>}
                          </span>
                        </td>
                        <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.82rem', whiteSpace: 'nowrap' }}>
                          <span style={{ color: tx.transaction_type === 'credit' ? 'var(--green)' : 'var(--text-primary)' }}>
                            {tx.transaction_type === 'credit' ? '+' : '-'}₹{tx.amount?.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          {activeTab === 'budgets' && (
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 16 }}>
              <div className="card animate-fadeUp">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
                  <div className="section-title" style={{ fontSize: '0.95rem' }}>Budget Limits</div>
                  <button onClick={() => setShowBudgetForm(s => !s)} className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '5px 10px' }}>
                    + Set Budget
                  </button>
                </div>

                {showBudgetForm && (
                  <form onSubmit={handleAddBudget} style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 14, padding: 12, background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)' }}>
                    <input className="input" placeholder="Category (e.g. Food & Dining)" value={newBudget.category}
                      onChange={e => setNewBudget(b => ({ ...b, category: e.target.value }))}
                      style={{ fontSize: '0.8rem', padding: '7px 10px' }} required />
                    <input className="input" type="number" placeholder="Monthly limit (₹)" value={newBudget.monthly_limit}
                      onChange={e => setNewBudget(b => ({ ...b, monthly_limit: e.target.value }))}
                      style={{ fontSize: '0.8rem', padding: '7px 10px' }} required />
                    <div style={{ display: 'flex', gap: 6 }}>
                      <button type="submit" className="btn btn-primary" style={{ flex: 1, fontSize: '0.78rem', padding: '6px', justifyContent: 'center' }}>Set</button>
                      <button type="button" onClick={() => setShowBudgetForm(false)} className="btn btn-ghost" style={{ padding: '6px 10px' }}><X size={13} /></button>
                    </div>
                  </form>
                )}

                {budgets.length === 0 ? (
                  <div className="empty-state" style={{ padding: '20px 0' }}>
                    <p>No budgets set. Add limits to track overspending.</p>
                  </div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
                    {budgets.map(b => (
                      <div key={b.category}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 5 }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 7 }}>
                            <div style={{ width: 8, height: 8, borderRadius: '50%', background: getCategoryColor(b.category) }} />
                            <span style={{ fontSize: '0.82rem', color: 'var(--text-primary)' }}>{b.category}</span>
                          </div>
                          <div style={{ display: 'flex', align: 'center', gap: 8 }}>
                            {b.is_over && <span style={{ fontSize: '0.68rem', color: 'var(--red)' }}>⚠ OVER</span>}
                            <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: b.is_over ? 'var(--red)' : 'var(--text-muted)' }}>
                              ₹{b.spent.toLocaleString('en-IN', { maximumFractionDigits: 0 })} / ₹{b.limit.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                            </span>
                          </div>
                        </div>
                        <div className="progress-bar">
                          <div className={`progress-fill ${b.is_over ? 'danger' : b.percentage_used > 80 ? '' : 'success'}`}
                            style={{ width: `${Math.min(b.percentage_used, 100)}%` }} />
                        </div>
                        <div style={{ fontSize: '0.68rem', color: 'var(--text-muted)', marginTop: 3 }}>
                          {b.percentage_used.toFixed(0)}% used · ₹{b.remaining.toLocaleString('en-IN', { maximumFractionDigits: 0 })} remaining
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>

              {/* Budget suggestions */}
              <div className="card animate-fadeUp">
                <div className="section-title" style={{ marginBottom: 14, fontSize: '0.95rem' }}>Suggested Budgets</div>
                <p style={{ fontSize: '0.78rem', color: 'var(--text-muted)', marginBottom: 14 }}>
                  Based on your spending history — click to set:
                </p>
                <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {categories.slice(0, 5).map(cat => {
                    const suggested = Math.ceil(cat.total * 0.9 / 100) * 100
                    const alreadySet = budgets.find(b => b.category === cat.category)
                    return (
                      <div key={cat.category} style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', padding: '8px 12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--bg-border)' }}>
                        <div>
                          <div style={{ fontSize: '0.8rem', color: 'var(--text-primary)' }}>{cat.category}</div>
                          <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>Spent ₹{cat.total.toLocaleString('en-IN', { maximumFractionDigits: 0 })} · Suggest ₹{suggested.toLocaleString('en-IN')}</div>
                        </div>
                        {alreadySet ? (
                          <span className="badge badge-green" style={{ fontSize: '0.65rem' }}>Set ✓</span>
                        ) : (
                          <button onClick={() => {
                            setNewBudget({ category: cat.category, monthly_limit: suggested.toString() })
                            setShowBudgetForm(true)
                            setActiveTab('budgets')
                          }} className="btn btn-ghost" style={{ fontSize: '0.72rem', padding: '4px 10px' }}>
                            Set ₹{suggested.toLocaleString('en-IN')}
                          </button>
                        )}
                      </div>
                    )
                  })}
                </div>
              </div>
            </div>
          )}

          {activeTab === 'statements' && (
            <div className="card animate-fadeUp">
              <div className="section-title" style={{ marginBottom: 16, fontSize: '0.95rem' }}>Uploaded Statements</div>
              <StatementLibrary onRefresh={loadData} />
              <div style={{ marginTop: 16 }}>
                <UploadZone onUpload={(job) => {
                  setActiveJobs(prev => [job, ...prev])
                }} />
              </div>
            </div>
          )}
        </>
    </div>
  )
}