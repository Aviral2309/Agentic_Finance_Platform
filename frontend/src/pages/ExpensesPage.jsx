import { useEffect, useState, useCallback, useRef } from 'react'
import { useDropzone } from 'react-dropzone'
import {
  Upload, FileText, CheckCircle2, AlertCircle,
  ChevronDown, Filter, TrendingDown, Check, X
} from 'lucide-react'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip,
  ResponsiveContainer, Cell
} from 'recharts'
import { expensesApi } from '../services/api'
import useStore from '../store/useStore'
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

// ── Upload zone ────────────────────────────────────────────────
function UploadZone({ onUpload }) {
  const [uploading, setUploading] = useState(false)

  const onDrop = useCallback(async (files) => {
    if (!files.length) return
    const file = files[0]
    setUploading(true)
    try {
      const { data } = await expensesApi.upload(file)
      onUpload(data)
      toast.success('File uploaded! Processing started.')
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Upload failed')
    } finally {
      setUploading(false)
    }
  }, [onUpload])

  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop, accept: { 'application/pdf': ['.pdf'], 'text/csv': ['.csv'] },
    maxFiles: 1, disabled: uploading,
  })

  return (
    <div
      {...getRootProps()}
      style={{
        border: `2px dashed ${isDragActive ? 'var(--gold)' : 'var(--bg-border)'}`,
        borderRadius: 'var(--radius-lg)',
        padding: '40px 24px',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        gap: 12,
        cursor: uploading ? 'not-allowed' : 'pointer',
        background: isDragActive ? 'var(--gold-muted)' : 'var(--bg-card)',
        transition: 'all 0.2s',
        textAlign: 'center',
      }}
    >
      <input {...getInputProps()} />
      {uploading ? (
        <>
          <div className="spinner" style={{ width: 32, height: 32 }} />
          <p style={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>Uploading...</p>
        </>
      ) : (
        <>
          <div style={{
            width: 56, height: 56, borderRadius: 16,
            background: 'var(--gold-muted)', border: '1px solid rgba(201,168,76,0.3)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Upload size={24} color="var(--gold)" />
          </div>
          <div>
            <p style={{ fontWeight: 500, color: 'var(--text-primary)', marginBottom: 4 }}>
              {isDragActive ? 'Drop your statement here' : 'Upload bank statement'}
            </p>
            <p style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
              PDF or CSV · SBI, HDFC, ICICI, Axis, Kotak
            </p>
          </div>
          <div className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '8px 16px' }}>
            Browse files
          </div>
        </>
      )}
    </div>
  )
}

// ── Job progress ───────────────────────────────────────────────
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
      padding: '16px 20px',
      background: 'var(--bg-elevated)',
      border: `1px solid ${isDone ? 'rgba(34,197,94,0.3)' : isFailed ? 'rgba(239,68,68,0.3)' : 'var(--bg-border)'}`,
      borderRadius: 'var(--radius-md)',
      display: 'flex', flexDirection: 'column', gap: 10,
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <FileText size={14} color="var(--text-muted)" />
          <span style={{ fontSize: '0.8rem', color: 'var(--text-primary)' }}>{status?.filename}</span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          {isDone && <CheckCircle2 size={14} color="var(--green)" />}
          {isFailed && <AlertCircle size={14} color="var(--red)" />}
          <span style={{ fontSize: '0.75rem', color: isDone ? 'var(--green)' : isFailed ? 'var(--red)' : 'var(--text-muted)', textTransform: 'capitalize' }}>
            {isDone ? `Done · ${status?.transactions_found} transactions` : isFailed ? 'Failed' : `${pct.toFixed(0)}% · ${status?.transactions_found} found`}
          </span>
        </div>
      </div>
      {!isDone && !isFailed && (
        <div className="progress-bar">
          <div className="progress-fill" style={{ width: `${pct}%` }} />
        </div>
      )}
    </div>
  )
}

// ── HITL card ──────────────────────────────────────────────────
function HITLCard({ item, onConfirm }) {
  const [selected, setSelected] = useState(item.suggested_category)
  const [custom, setCustom] = useState('')
  const [loading, setLoading] = useState(false)
  const cats = item.alternative_categories || []

  async function confirm() {
    setLoading(true)
    try {
      await expensesApi.confirmHitl({
        transaction_id: item.transaction_id,
        confirmed_category: custom || selected,
      })
      toast.success('Category confirmed')
      onConfirm(item.hitl_id)
    } catch { toast.error('Failed to confirm') }
    finally { setLoading(false) }
  }

  return (
    <div style={{
      padding: '16px 18px',
      background: 'var(--bg-card)',
      border: '1px solid var(--bg-border)',
      borderRadius: 'var(--radius-md)',
    }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
        <div>
          <div style={{ fontSize: '0.875rem', color: 'var(--text-primary)', fontWeight: 500 }}>{item.description?.slice(0, 50)}</div>
          <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 2 }}>
            {new Date(item.date).toLocaleDateString('en-IN')} · ₹{item.amount?.toLocaleString('en-IN')}
          </div>
        </div>
        <span className="badge badge-amber">Needs review</span>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 10 }}>
        {[item.suggested_category, ...cats.filter(c => c !== item.suggested_category)].filter(Boolean).map(cat => (
          <button
            key={cat}
            onClick={() => { setSelected(cat); setCustom('') }}
            style={{
              padding: '4px 10px',
              borderRadius: 99,
              border: `1px solid ${selected === cat ? getCategoryColor(cat) : 'var(--bg-border)'}`,
              background: selected === cat ? `${getCategoryColor(cat)}20` : 'transparent',
              color: selected === cat ? getCategoryColor(cat) : 'var(--text-secondary)',
              fontSize: '0.75rem', cursor: 'pointer', transition: 'all 0.15s',
            }}
          >{cat}</button>
        ))}
      </div>

      <div style={{ display: 'flex', gap: 8 }}>
        <input
          className="input"
          placeholder="Or type custom category..."
          value={custom}
          onChange={e => setCustom(e.target.value)}
          style={{ flex: 1, padding: '7px 12px', fontSize: '0.8rem' }}
        />
        <button onClick={confirm} disabled={loading} className="btn btn-primary" style={{ padding: '7px 14px', fontSize: '0.8rem' }}>
          {loading ? <div className="spinner" style={{ width: 14, height: 14 }} /> : <><Check size={13} /> Confirm</>}
        </button>
      </div>
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────
export default function ExpensesPage() {
  const [jobs, setJobs] = useState([])
  const [summary, setSummary] = useState(null)
  const [transactions, setTransactions] = useState([])
  const [hitlQueue, setHitlQueue] = useState([])
  const [trends, setTrends] = useState([])
  const [budgets, setBudgets] = useState([])
  const [loading, setLoading] = useState(true)
  const [activeMonth, setActiveMonth] = useState(null)
  const [showBudgetForm, setShowBudgetForm] = useState(false)
  const [newBudget, setNewBudget] = useState({ category: '', monthly_limit: '' })

  async function loadData() {
    try {
      const [sumRes, txRes, hitlRes, trendRes, budgetRes] = await Promise.allSettled([
        expensesApi.summary(activeMonth),
        expensesApi.transactions({ limit: 50, month: activeMonth }),
        expensesApi.hitlQueue(),
        expensesApi.trends(6),
        expensesApi.budgets(),
      ])
      if (sumRes.status === 'fulfilled') setSummary(sumRes.value.data)
      if (txRes.status === 'fulfilled') setTransactions(txRes.value.data)
      if (hitlRes.status === 'fulfilled') setHitlQueue(hitlRes.value.data)
      if (trendRes.status === 'fulfilled') setTrends(trendRes.value.data)
      if (budgetRes.status === 'fulfilled') setBudgets(budgetRes.value.data)
    } finally { setLoading(false) }
  }

  useEffect(() => { loadData() }, [activeMonth])

  function handleJobComplete() {
    setTimeout(loadData, 1500)
  }

  async function handleAddBudget(e) {
    e.preventDefault()
    try {
      await expensesApi.createBudget({ category: newBudget.category, monthly_limit: parseFloat(newBudget.monthly_limit) })
      toast.success('Budget limit set')
      setShowBudgetForm(false)
      setNewBudget({ category: '', monthly_limit: '' })
      loadData()
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed') }
  }

  const categories = summary?.categories || []

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>

      <div className="animate-fadeUp" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div>
          <h1 style={{ fontSize: '1.5rem', marginBottom: 4 }}>Expense Tracker</h1>
          <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Upload statements · Auto-categorize · Set budgets</p>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '380px 1fr', gap: 20, alignItems: 'start' }}>

        {/* Left column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          <UploadZone onUpload={(job) => setJobs(prev => [job, ...prev])} />

          {/* Active jobs */}
          {jobs.length > 0 && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
              {jobs.map(job => (
                <JobProgress key={job.job_id} job={job} onComplete={handleJobComplete} />
              ))}
            </div>
          )}

          {/* HITL queue */}
          {hitlQueue.length > 0 && (
            <div className="card" style={{ padding: 20 }}>
              <div className="section-title" style={{ marginBottom: 16, fontSize: '0.95rem' }}>
                Needs Your Review
                <span className="badge badge-amber" style={{ marginLeft: 8, fontSize: '0.7rem' }}>{hitlQueue.length}</span>
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                {hitlQueue.slice(0, 3).map(item => (
                  <HITLCard
                    key={item.hitl_id}
                    item={item}
                    onConfirm={(id) => {
                      setHitlQueue(q => q.filter(i => i.hitl_id !== id))
                      loadData()
                    }}
                  />
                ))}
              </div>
            </div>
          )}

          {/* Budget status */}
          <div className="card" style={{ padding: 20 }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 16 }}>
              <div className="section-title" style={{ fontSize: '0.95rem' }}>Budgets</div>
              <button onClick={() => setShowBudgetForm(s => !s)} className="btn btn-ghost" style={{ fontSize: '0.75rem', padding: '4px 10px' }}>
                + Add
              </button>
            </div>

            {showBudgetForm && (
              <form onSubmit={handleAddBudget} style={{ display: 'flex', flexDirection: 'column', gap: 8, marginBottom: 16, padding: '12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)' }}>
                <input className="input" placeholder="Category (e.g. Food & Dining)" value={newBudget.category}
                  onChange={e => setNewBudget(b => ({ ...b, category: e.target.value }))} style={{ fontSize: '0.8rem', padding: '8px 12px' }} required />
                <input className="input" type="number" placeholder="Monthly limit (₹)" value={newBudget.monthly_limit}
                  onChange={e => setNewBudget(b => ({ ...b, monthly_limit: e.target.value }))} style={{ fontSize: '0.8rem', padding: '8px 12px' }} required />
                <div style={{ display: 'flex', gap: 6 }}>
                  <button type="submit" className="btn btn-primary" style={{ flex: 1, fontSize: '0.8rem', padding: '7px 12px', justifyContent: 'center' }}>Set Limit</button>
                  <button type="button" onClick={() => setShowBudgetForm(false)} className="btn btn-ghost" style={{ fontSize: '0.8rem', padding: '7px 12px' }}><X size={13} /></button>
                </div>
              </form>
            )}

            {budgets.length === 0 ? (
              <div className="empty-state" style={{ padding: '20px 0' }}>
                <p>No budgets set yet. Add limits to track overspending.</p>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
                {budgets.map(b => (
                  <div key={b.category}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <span style={{ fontSize: '0.8rem', color: 'var(--text-secondary)' }}>{b.category}</span>
                      <span style={{ fontSize: '0.75rem', fontFamily: 'var(--font-mono)', color: b.is_over ? 'var(--red)' : 'var(--text-muted)' }}>
                        ₹{b.spent.toLocaleString('en-IN', {maximumFractionDigits:0})} / ₹{b.limit.toLocaleString('en-IN', {maximumFractionDigits:0})}
                      </span>
                    </div>
                    <div className="progress-bar">
                      <div
                        className={`progress-fill ${b.is_over ? 'danger' : b.percentage_used > 80 ? '' : 'success'}`}
                        style={{ width: `${Math.min(b.percentage_used, 100)}%` }}
                      />
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>

        {/* Right column */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>

          {/* Summary bar chart */}
          <div className="card animate-fadeUp">
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
              <div className="section-title">Category Breakdown</div>
              <div style={{ fontSize: '0.875rem', fontFamily: 'var(--font-mono)', color: 'var(--gold)' }}>
                ₹{(summary?.total || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}
              </div>
            </div>
            {categories.length > 0 ? (
              <ResponsiveContainer width="100%" height={220}>
                <BarChart data={categories.slice(0, 8)} layout="vertical">
                  <XAxis type="number" hide />
                  <YAxis type="category" dataKey="category" tick={{ fill: 'var(--text-secondary)', fontSize: 11 }} width={110} axisLine={false} tickLine={false} />
                  <Tooltip
                    formatter={(v) => [`₹${Number(v).toLocaleString('en-IN')}`, 'Spent']}
                    contentStyle={{ background: 'var(--bg-elevated)', border: '1px solid var(--bg-border)', borderRadius: 8, fontSize: '0.8rem' }}
                  />
                  <Bar dataKey="total" radius={[0, 4, 4, 0]}>
                    {categories.slice(0, 8).map((cat, i) => (
                      <Cell key={i} fill={getCategoryColor(cat.category)} fillOpacity={0.8} />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            ) : (
              <div className="empty-state">
                <TrendingDown size={36} />
                <p>Upload a bank statement to see your spending breakdown</p>
              </div>
            )}
          </div>

          {/* Transactions table */}
          <div className="card animate-fadeUp" style={{ padding: 0, overflow: 'hidden' }}>
            <div style={{ padding: '20px 20px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
              <div className="section-title">Recent Transactions</div>
              <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{transactions.length} entries</span>
            </div>
            {transactions.length === 0 ? (
              <div className="empty-state" style={{ padding: '32px 24px' }}>
                <FileText size={32} />
                <p>No transactions yet. Upload a bank statement to get started.</p>
              </div>
            ) : (
              <div style={{ overflowX: 'auto' }}>
                <table className="table">
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Description</th>
                      <th>Category</th>
                      <th style={{ textAlign: 'right' }}>Amount</th>
                      <th>Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {transactions.map(tx => (
                      <tr key={tx.id}>
                        <td style={{ whiteSpace: 'nowrap', color: 'var(--text-muted)', fontSize: '0.8rem' }}>
                          {new Date(tx.date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short' })}
                        </td>
                        <td style={{ maxWidth: 200 }}>
                          <div style={{ fontSize: '0.85rem', color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                            {tx.description?.slice(0, 40)}
                          </div>
                          {tx.is_recurring && <span style={{ fontSize: '0.7rem', color: 'var(--blue)' }}>↻ Recurring</span>}
                        </td>
                        <td>
                          {tx.category ? (
                            <span style={{
                              display: 'inline-flex', alignItems: 'center', gap: 6,
                              padding: '3px 8px', borderRadius: 99,
                              background: `${getCategoryColor(tx.category)}18`,
                              color: getCategoryColor(tx.category),
                              fontSize: '0.72rem', fontWeight: 500, border: `1px solid ${getCategoryColor(tx.category)}30`,
                            }}>
                              {tx.category}
                            </span>
                          ) : (
                            <span style={{ color: 'var(--text-muted)', fontSize: '0.8rem' }}>—</span>
                          )}
                        </td>
                        <td style={{ textAlign: 'right', fontFamily: 'var(--font-mono)', fontSize: '0.85rem', whiteSpace: 'nowrap' }}>
                          <span style={{ color: tx.transaction_type === 'credit' ? 'var(--green)' : 'var(--text-primary)' }}>
                            {tx.transaction_type === 'credit' ? '+' : '-'}₹{tx.amount?.toLocaleString('en-IN', { maximumFractionDigits: 0 })}
                          </span>
                        </td>
                        <td>
                          <span style={{ fontSize: '0.7rem', color: `var(--text-muted)` }}>
                            L{tx.categorization_layer || '—'}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  )
}
