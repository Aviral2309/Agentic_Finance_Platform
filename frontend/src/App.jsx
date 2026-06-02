import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'react-hot-toast'
import useStore from './store/useStore'
import Layout from './components/layout/Layout'
import LoginPage from './pages/LoginPage'
import RegisterPage from './pages/RegisterPage'
import DashboardPage from './pages/DashboardPage'
import ExpensesPage from './pages/ExpensesPage'
import PortfolioPage from './pages/PortfolioPage'
import AdvisorPage from './pages/AdvisorPage'

function ProtectedRoute({ children }) {
  const token = useStore(s => s.token)
  return token ? children : <Navigate to="/login" replace />
}

function PublicRoute({ children }) {
  const token = useStore(s => s.token)
  return !token ? children : <Navigate to="/" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Toaster
        position="top-right"
        toastOptions={{
          style: {
            background: '#141e2e',
            color: '#f0f4f8',
            border: '1px solid #1e2d42',
            fontFamily: "'DM Sans', sans-serif",
            fontSize: '0.875rem',
          },
          success: { iconTheme: { primary: '#c9a84c', secondary: '#080c14' } },
          error:   { iconTheme: { primary: '#ef4444', secondary: '#080c14' } },
        }}
      />
      <Routes>
        <Route path="/login" element={<PublicRoute><LoginPage /></PublicRoute>} />
        <Route path="/register" element={<PublicRoute><RegisterPage /></PublicRoute>} />
        <Route path="/" element={<ProtectedRoute><Layout /></ProtectedRoute>}>
          <Route index element={<DashboardPage />} />
          <Route path="expenses" element={<ExpensesPage />} />
          <Route path="portfolio" element={<PortfolioPage />} />
          <Route path="advisor" element={<AdvisorPage />} />
        </Route>
      </Routes>
    </BrowserRouter>
  )
}
