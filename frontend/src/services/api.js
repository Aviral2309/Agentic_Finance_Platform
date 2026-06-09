import axios from 'axios'

const API_URL = 'http://127.0.0.1:8000'

const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: { 'Content-Type': 'application/json' },
})

// Attach token to every request
api.interceptors.request.use(config => {
  const token = localStorage.getItem('wp_token')
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

// Handle 401 globally
api.interceptors.response.use(
  res => res,
  err => {
    if (err.response?.status === 401) {
      localStorage.removeItem('wp_token')
      localStorage.removeItem('wp_user')
      window.location.href = '/login'
    }
    return Promise.reject(err)
  }
)

// ── Auth ───────────────────────────────────────────────────
export const authApi = {
  register: (data) => api.post('/auth/register', data),
  login: (data) => api.post('/auth/login', data),
  me: () => api.get('/auth/me'),
}

// ── Expenses ───────────────────────────────────────────────
export const expensesApi = {
  upload: (file) => {
    const form = new FormData()
    form.append('file', file)
    return api.post('/expenses/upload', form, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  jobStatus: (jobId) => api.get(`/expenses/jobs/${jobId}`),
  transactions: (params) => api.get('/expenses/transactions', { params }),
  updateTransaction: (id, data) => api.patch(`/expenses/transactions/${id}`, data),
  summary: (month) => api.get('/expenses/summary', { params: month ? { month } : {} }),
  trends: (months = 6) => api.get('/expenses/trends', { params: { months } }),
  budgets: () => api.get('/expenses/budgets/status'),
  createBudget: (data) => api.post('/expenses/budgets', data),
  hitlQueue: () => api.get('/expenses/hitl'),
  confirmHitl: (data) => api.post('/expenses/hitl/confirm', data),
}

// ── Portfolio ──────────────────────────────────────────────
export const portfolioApi = {
  summary: () => api.get('/portfolio/summary'),
  addHolding: (data) => api.post('/portfolio/holdings', data),
  deleteHolding: (id) => api.delete(`/portfolio/holdings/${id}`),
  forecast: (ticker) => api.get(`/portfolio/forecast/${ticker}`),
  trainModel: (ticker) => api.post(`/portfolio/forecast/${ticker}/train`),
  sentiment: (ticker) => api.get(`/portfolio/sentiment/${ticker}`),
}

// ── Advisor ────────────────────────────────────────────────
export const advisorApi = {
  // Returns a fetch Response for SSE streaming
  chat: async (message) => {
    const token = localStorage.getItem('wp_token')
    return fetch(`${API_URL}/api/advisor/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${token}`,
      },
      body: JSON.stringify({ message }),
    })
  },
}

export default api
