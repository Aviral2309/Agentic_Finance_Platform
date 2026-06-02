import { create } from 'zustand'

const useStore = create((set, get) => ({
  // Auth
  user: JSON.parse(localStorage.getItem('wp_user') || 'null'),
  token: localStorage.getItem('wp_token') || null,

  setAuth: (user, token) => {
    localStorage.setItem('wp_token', token)
    localStorage.setItem('wp_user', JSON.stringify(user))
    set({ user, token })
  },
  logout: () => {
    localStorage.removeItem('wp_token')
    localStorage.removeItem('wp_user')
    set({ user: null, token: null })
  },

  // Portfolio
  portfolio: null,
  setPortfolio: (data) => set({ portfolio: data }),

  // Active parse jobs (for polling)
  activeJobs: [],
  addJob: (job) => set(s => ({ activeJobs: [...s.activeJobs, job] })),
  updateJob: (jobId, data) => set(s => ({
    activeJobs: s.activeJobs.map(j => j.job_id === jobId ? { ...j, ...data } : j)
  })),
  removeJob: (jobId) => set(s => ({
    activeJobs: s.activeJobs.filter(j => j.job_id !== jobId)
  })),

  // Sidebar
  sidebarOpen: true,
  toggleSidebar: () => set(s => ({ sidebarOpen: !s.sidebarOpen })),
}))

export default useStore
