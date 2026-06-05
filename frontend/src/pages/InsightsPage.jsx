import { useState } from 'react'
import { Shield, Target, Calculator, ChevronDown, ChevronUp, TrendingUp, AlertTriangle, CheckCircle } from 'lucide-react'
import { RadarChart, PolarGrid, PolarAngleAxis, Radar, ResponsiveContainer, BarChart, Bar, XAxis, YAxis, Tooltip, Cell } from 'recharts'
import api from '../services/api'
import toast from 'react-hot-toast'

// ── Money Health Score ─────────────────────────────────────────
function HealthScorePanel() {
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)

  async function load() {
    setLoading(true)
    try {
      const { data: d } = await api.get('/insights/health-score')
      setData(d)
    } catch (e) {
      toast.error('Failed to load health score')
    } finally {
      setLoading(false)
    }
  }

  const gradeColor = { A: '#22c55e', B: '#c9a84c', C: '#f59e0b', D: '#ef4444' }

  const radarData = data ? Object.entries(data.scores).map(([key, val]) => ({
    subject: key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()),
    value: val,
    fullMark: 100,
  })) : []

  return (
    <div className="card">
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <div style={{ width: 36, height: 36, background: 'rgba(34,197,94,0.15)', border: '1px solid rgba(34,197,94,0.3)', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
            <Shield size={18} color="#22c55e" />
          </div>
          <div>
            <div className="section-title" style={{ marginBottom: 0 }}>Money Health Score</div>
            <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>6-dimension financial wellness analysis</div>
          </div>
        </div>
        <button onClick={load} disabled={loading} className="btn btn-secondary" style={{ fontSize: '0.8rem', padding: '7px 14px' }}>
          {loading ? <><div className="spinner" style={{ width: 14, height: 14 }} /> Computing...</> : 'Calculate Score'}
        </button>
      </div>

      {data ? (
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 20 }}>
          {/* Radar chart */}
          <div>
            <ResponsiveContainer width="100%" height={220}>
              <RadarChart data={radarData}>
                <PolarGrid stroke="var(--bg-border)" />
                <PolarAngleAxis dataKey="subject" tick={{ fill: 'var(--text-muted)', fontSize: 10 }} />
                <Radar name="Score" dataKey="value" stroke="#c9a84c" fill="#c9a84c" fillOpacity={0.2} strokeWidth={2} />
              </RadarChart>
            </ResponsiveContainer>
          </div>

          {/* Score + grade */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 12 }}>
            <div style={{ textAlign: 'center', padding: '16px 0' }}>
              <div style={{ fontSize: '3.5rem', fontFamily: 'var(--font-display)', fontWeight: 700, color: gradeColor[data.grade] || 'var(--gold)', lineHeight: 1 }}>
                {data.grade}
              </div>
              <div style={{ fontSize: '1.2rem', fontFamily: 'var(--font-display)', color: 'var(--text-primary)', marginTop: 4 }}>
                {data.composite}/100
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>Overall Health Score</div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {Object.entries(data.scores).map(([key, val]) => (
                <div key={key}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 3 }}>
                    <span style={{ fontSize: '0.72rem', color: 'var(--text-secondary)' }}>
                      {key.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())}
                    </span>
                    <span style={{ fontSize: '0.72rem', fontFamily: 'var(--font-mono)', color: val >= 70 ? 'var(--green)' : val >= 40 ? 'var(--amber)' : 'var(--red)' }}>
                      {val}
                    </span>
                  </div>
                  <div className="progress-bar" style={{ height: 4 }}>
                    <div className={`progress-fill ${val >= 70 ? 'success' : val < 40 ? 'danger' : ''}`} style={{ width: `${val}%` }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Recommendations */}
          <div style={{ gridColumn: '1 / -1' }}>
            <div style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Recommendations</div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
              {data.recommendations.map((r, i) => (
                <div key={i} style={{
                  padding: '8px 12px', borderRadius: 'var(--radius-md)', fontSize: '0.8rem',
                  background: r.startsWith('✓') ? 'var(--green-dim)' : 'rgba(245,158,11,0.08)',
                  border: `1px solid ${r.startsWith('✓') ? 'rgba(34,197,94,0.2)' : 'rgba(245,158,11,0.2)'}`,
                  color: r.startsWith('✓') ? 'var(--green)' : 'var(--amber)',
                }}>{r}</div>
              ))}
            </div>
          </div>
        </div>
      ) : (
        <div className="empty-state">
          <Shield size={40} />
          <p>Click "Calculate Score" to get your 6-dimension financial health analysis based on your actual expenses and portfolio data.</p>
        </div>
      )}
    </div>
  )
}

// ── FIRE Calculator ────────────────────────────────────────────
function FIRECalculator() {
  const [form, setForm] = useState({
    current_age: 25, target_retirement_age: 45,
    monthly_income: 80000, monthly_expenses: 50000,
    existing_corpus: 0, existing_term_cover: 0,
    liquid_savings: 0, expected_return_pct: 12,
    inflation_pct: 6, safe_withdrawal_rate: 4,
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  async function calculate() {
    setLoading(true)
    try {
      const { data } = await api.post('/insights/fire-calculator', form)
      setResult(data)
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Calculation failed')
    } finally {
      setLoading(false)
    }
  }

  const field = (label, key, type = 'number', min = 0) => (
    <div>
      <label className="input-label">{label}</label>
      <input className="input" type={type} min={min} value={form[key]}
        onChange={e => setForm(f => ({ ...f, [key]: parseFloat(e.target.value) || 0 }))}
        style={{ fontSize: '0.85rem', padding: '8px 12px' }} />
    </div>
  )

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <div style={{ width: 36, height: 36, background: 'rgba(201,168,76,0.15)', border: '1px solid rgba(201,168,76,0.3)', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Target size={18} color="var(--gold)" />
        </div>
        <div>
          <div className="section-title" style={{ marginBottom: 0 }}>FIRE Calculator</div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Financial Independence, Retire Early planner</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
        {field("Current Age", "current_age", "number", 18)}
        {field("Target Retirement Age", "target_retirement_age", "number", 20)}
        {field("Monthly Income (₹)", "monthly_income")}
        {field("Monthly Expenses (₹)", "monthly_expenses")}
        {field("Existing Corpus (₹)", "existing_corpus")}
        {field("Liquid Savings (₹)", "liquid_savings")}
        {field("Expected Return % (annual)", "expected_return_pct")}
        {field("Inflation % (annual)", "inflation_pct")}
      </div>

      <button onClick={calculate} disabled={loading} className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', marginBottom: result ? 20 : 0 }}>
        {loading ? <><div className="spinner" style={{ width: 16, height: 16 }} /> Calculating...</> : 'Calculate FIRE Plan'}
      </button>

      {result && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Key numbers */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 10 }}>
            {[
              { label: 'Corpus Needed', value: result.results.corpus_needed_readable, color: 'var(--gold)' },
              { label: 'Monthly SIP', value: `₹${result.results.monthly_sip_needed.toLocaleString('en-IN')}`, color: result.results.can_afford_sip ? 'var(--green)' : 'var(--red)' },
              { label: 'Years to FIRE', value: `${result.inputs.years_to_retire} years`, color: 'var(--blue)' },
            ].map(s => (
              <div key={s.label} style={{ padding: '14px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--bg-border)', textAlign: 'center' }}>
                <div style={{ fontSize: '0.65rem', color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: 6 }}>{s.label}</div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: '1.1rem', fontWeight: 600, color: s.color }}>{s.value}</div>
              </div>
            ))}
          </div>

          {/* Affordability */}
          <div style={{
            padding: '12px 16px', borderRadius: 'var(--radius-md)', fontSize: '0.8rem',
            background: result.results.can_afford_sip ? 'var(--green-dim)' : 'var(--red-dim)',
            border: `1px solid ${result.results.can_afford_sip ? 'rgba(34,197,94,0.2)' : 'rgba(239,68,68,0.2)'}`,
            color: result.results.can_afford_sip ? 'var(--green)' : 'var(--red)',
          }}>
            {result.results.can_afford_sip
              ? `✓ SIP of ₹${result.results.monthly_sip_needed.toLocaleString('en-IN')}/month is ${result.results.sip_as_pct_of_savings.toFixed(1)}% of your current savings — achievable`
              : `⚠ Required SIP exceeds your current savings capacity — increase income or reduce expenses`}
          </div>

          {/* Action items */}
          {result.action_items?.length > 0 && (
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Action Plan</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                {result.action_items.map((item, i) => (
                  <div key={i} style={{ padding: '8px 12px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', fontSize: '0.8rem', color: 'var(--text-secondary)', border: '1px solid var(--bg-border)' }}>
                    {item}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Milestones */}
          {result.milestones?.length > 0 && (
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Milestone Roadmap</div>
              <div style={{ overflowX: 'auto' }}>
                <table className="table" style={{ fontSize: '0.78rem' }}>
                  <thead>
                    <tr>
                      <th>Year</th><th>Age</th><th>Target Corpus</th><th>Progress</th><th>Allocation</th>
                    </tr>
                  </thead>
                  <tbody>
                    {result.milestones.map(m => (
                      <tr key={m.year}>
                        <td>Year {m.year}</td>
                        <td>{m.age}</td>
                        <td style={{ fontFamily: 'var(--font-mono)' }}>
                          {m.corpus_target >= 1e7 ? `₹${(m.corpus_target/1e7).toFixed(1)}Cr` : `₹${(m.corpus_target/1e5).toFixed(1)}L`}
                        </td>
                        <td>
                          <div style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                            <div className="progress-bar" style={{ width: 60, height: 4 }}>
                              <div className="progress-fill success" style={{ width: `${Math.min(100, m.progress_pct)}%` }} />
                            </div>
                            <span style={{ fontSize: '0.7rem', color: 'var(--text-muted)' }}>{m.progress_pct}%</span>
                          </div>
                        </td>
                        <td style={{ fontSize: '0.72rem' }}>
                          <span style={{ color: 'var(--green)' }}>{m.equity_allocation}% EQ</span>
                          {' / '}
                          <span style={{ color: 'var(--blue)' }}>{m.debt_allocation}% DT</span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Tax Estimator ──────────────────────────────────────────────
function TaxEstimator() {
  const [form, setForm] = useState({
    annual_gross_salary: 1200000,
    hra_received: 0, rent_paid: 0, metro_city: true,
    section_80c_investments: 0, section_80d_premium: 0,
    section_80ccd1b: 0, home_loan_interest: 0,
    lta_claimed: 0, other_deductions: 0,
  })
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)

  async function calculate() {
    setLoading(true)
    try {
      const { data } = await api.post('/insights/tax-estimator', form)
      setResult(data)
    } catch (e) {
      toast.error('Tax calculation failed')
    } finally {
      setLoading(false)
    }
  }

  const field = (label, key, type = 'number') => (
    <div>
      <label className="input-label">{label}</label>
      <input className="input" type={type} min={0} value={form[key]}
        onChange={e => setForm(f => ({ ...f, [key]: type === 'number' ? (parseFloat(e.target.value) || 0) : e.target.value }))}
        style={{ fontSize: '0.85rem', padding: '8px 12px' }} />
    </div>
  )

  return (
    <div className="card">
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 20 }}>
        <div style={{ width: 36, height: 36, background: 'rgba(59,130,246,0.15)', border: '1px solid rgba(59,130,246,0.3)', borderRadius: 10, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
          <Calculator size={18} color="var(--blue)" />
        </div>
        <div>
          <div className="section-title" style={{ marginBottom: 0 }}>Tax Estimator</div>
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Old vs new regime · Missing deductions · FY 2024-25</div>
        </div>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12, marginBottom: 16 }}>
        {field("Annual Gross Salary (₹)", "annual_gross_salary")}
        {field("HRA Received (₹/year)", "hra_received")}
        {field("Annual Rent Paid (₹)", "rent_paid")}
        {field("80C Investments (₹)", "section_80c_investments")}
        {field("80D Health Insurance (₹)", "section_80d_premium")}
        {field("NPS 80CCD(1B) (₹)", "section_80ccd1b")}
        {field("Home Loan Interest (₹)", "home_loan_interest")}
        {field("Other Deductions (₹)", "other_deductions")}
      </div>

      <button onClick={calculate} disabled={loading} className="btn btn-primary" style={{ width: '100%', justifyContent: 'center', marginBottom: result ? 20 : 0 }}>
        {loading ? <><div className="spinner" style={{ width: 16, height: 16 }} /> Calculating...</> : 'Compare Tax Regimes'}
      </button>

      {result && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 16 }}>
          {/* Regime comparison */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
            {[
              { label: 'Old Regime', tax: result.old_regime.tax_payable, taxable: result.old_regime.taxable_income, deductions: result.old_regime.total_deductions },
              { label: 'New Regime', tax: result.new_regime.tax_payable, taxable: result.new_regime.taxable_income, deductions: 75000 },
            ].map((r, i) => {
              const isBetter = result.recommendation.better_regime === (i === 0 ? 'old' : 'new')
              return (
                <div key={r.label} style={{
                  padding: '16px', borderRadius: 'var(--radius-md)',
                  background: isBetter ? 'var(--green-dim)' : 'var(--bg-elevated)',
                  border: `1px solid ${isBetter ? 'rgba(34,197,94,0.3)' : 'var(--bg-border)'}`,
                }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 10 }}>
                    <div style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--text-primary)' }}>{r.label}</div>
                    {isBetter && <span className="badge badge-green" style={{ fontSize: '0.65rem' }}>BETTER</span>}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Total Deductions: <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>₹{r.deductions.toLocaleString('en-IN')}</span></div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>Taxable Income: <span style={{ color: 'var(--text-primary)', fontFamily: 'var(--font-mono)' }}>₹{r.taxable.toLocaleString('en-IN')}</span></div>
                    <div style={{ fontSize: '1rem', fontFamily: 'var(--font-display)', fontWeight: 600, color: isBetter ? 'var(--green)' : 'var(--text-primary)', marginTop: 6 }}>
                      Tax: ₹{r.tax.toLocaleString('en-IN')}
                    </div>
                  </div>
                </div>
              )
            })}
          </div>

          {/* Saving */}
          <div style={{ padding: '12px 16px', background: 'var(--gold-muted)', border: '1px solid rgba(201,168,76,0.2)', borderRadius: 'var(--radius-md)', fontSize: '0.85rem', color: 'var(--gold)', fontWeight: 500 }}>
            💰 {result.recommendation.message}
            {result.potential_additional_savings > 0 && (
              <div style={{ fontSize: '0.8rem', color: 'var(--text-secondary)', fontWeight: 400, marginTop: 4 }}>
                + Additional ₹{result.potential_additional_savings.toLocaleString('en-IN')} possible by utilizing all deductions
              </div>
            )}
          </div>

          {/* Missing deductions */}
          {result.missing_deductions?.length > 0 && (
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Missing Deductions</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
                {result.missing_deductions.map(d => (
                  <div key={d.section} style={{ padding: '12px 14px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--bg-border)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 4 }}>
                      <span style={{ fontSize: '0.82rem', fontWeight: 600, color: 'var(--text-primary)' }}>Section {d.section}</span>
                      <span style={{ fontSize: '0.78rem', color: 'var(--green)', fontFamily: 'var(--font-mono)' }}>Save ₹{d.potential_tax_saving.toLocaleString('en-IN')}</span>
                    </div>
                    <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{d.description}</div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', marginTop: 4 }}>
                      Invested: ₹{d.invested.toLocaleString('en-IN')} / Limit: ₹{d.max_limit.toLocaleString('en-IN')} — Gap: ₹{d.gap.toLocaleString('en-IN')}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Investment suggestions */}
          {result.investment_suggestions?.length > 0 && (
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 500, color: 'var(--text-secondary)', marginBottom: 8, textTransform: 'uppercase', letterSpacing: '0.06em' }}>Recommended Investments</div>
              {result.investment_suggestions.map((s, i) => (
                <div key={i} style={{ padding: '10px 14px', background: 'var(--bg-elevated)', borderRadius: 'var(--radius-md)', border: '1px solid var(--bg-border)', marginBottom: 6 }}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 2 }}>
                    <span style={{ fontSize: '0.82rem', fontWeight: 500, color: 'var(--gold)' }}>{s.instrument}</span>
                    <span className="badge badge-blue" style={{ fontSize: '0.65rem' }}>{s.section}</span>
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>{s.reason}</div>
                  <div style={{ fontSize: '0.72rem', color: 'var(--text-secondary)', marginTop: 2 }}>Invest up to ₹{s.max_amount.toLocaleString('en-IN')}</div>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  )
}

// ── Main page ──────────────────────────────────────────────────
export default function InsightsPage() {
  const [activeTab, setActiveTab] = useState('health')

  const tabs = [
    { id: 'health', label: 'Health Score', icon: Shield },
    { id: 'fire', label: 'FIRE Calculator', icon: Target },
    { id: 'tax', label: 'Tax Estimator', icon: Calculator },
  ]

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 20 }}>
      <div className="animate-fadeUp">
        <h1 style={{ fontSize: '1.5rem', marginBottom: 4 }}>Financial Insights</h1>
        <p style={{ color: 'var(--text-muted)', fontSize: '0.875rem' }}>Health score · FIRE planner · Tax optimizer</p>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: 6, background: 'var(--bg-elevated)', padding: 4, borderRadius: 'var(--radius-lg)', border: '1px solid var(--bg-border)', width: 'fit-content' }}>
        {tabs.map(({ id, label, icon: Icon }) => (
          <button key={id} onClick={() => setActiveTab(id)} style={{
            display: 'flex', alignItems: 'center', gap: 6,
            padding: '8px 16px', borderRadius: 'var(--radius-md)',
            background: activeTab === id ? 'var(--bg-card)' : 'transparent',
            border: activeTab === id ? '1px solid var(--bg-border)' : '1px solid transparent',
            color: activeTab === id ? 'var(--text-primary)' : 'var(--text-muted)',
            fontSize: '0.85rem', cursor: 'pointer', transition: 'all 0.15s', fontWeight: activeTab === id ? 500 : 400,
          }}>
            <Icon size={15} />
            {label}
          </button>
        ))}
      </div>

      <div className="animate-fadeUp">
        {activeTab === 'health' && <HealthScorePanel />}
        {activeTab === 'fire' && <FIRECalculator />}
        {activeTab === 'tax' && <TaxEstimator />}
      </div>
    </div>
  )
}
