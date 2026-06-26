import { Outlet, NavLink, useNavigate } from 'react-router-dom'
import { useState } from 'react'
import {
  LayoutDashboard, CreditCard, TrendingUp,
  MessageSquare, LogOut, Menu, X,
  Wallet, Bell, ChevronRight, BarChart2
} from 'lucide-react'
import useStore from '../../store/useStore'
import toast from 'react-hot-toast'

const NAV = [
  { to: '/',          icon: LayoutDashboard, label: 'Dashboard'  },
  { to: '/dashboard/expenses',  icon: CreditCard,      label: 'Expenses'   },
  { to: '/dashboard/portfolio', icon: TrendingUp,      label: 'Portfolio'  },
  { to: '/dashboard/advisor',   icon: MessageSquare,   label: 'AI Advisor' },
  { to: '/dashboard/insights', icon: BarChart2, label: 'Insights' },
]

export default function Layout() {
  const [collapsed, setCollapsed] = useState(false)
  const { user, logout } = useStore()
  const navigate = useNavigate()

  function handleLogout() {
    logout()
    toast.success('Logged out')
    navigate('/login')
  }

  return (
    <div style={{ display: 'flex', height: '100vh', overflow: 'hidden' }}>

      {/* ── Sidebar ── */}
      <aside style={{
        width: collapsed ? 64 : 240,
        minWidth: collapsed ? 64 : 240,
        background: 'var(--bg-surface)',
        borderRight: '1px solid var(--bg-border)',
        display: 'flex',
        flexDirection: 'column',
        transition: 'width 0.25s cubic-bezier(0.4,0,0.2,1), min-width 0.25s cubic-bezier(0.4,0,0.2,1)',
        overflow: 'hidden',
        zIndex: 20,
      }}>

        {/* Logo */}
        <div style={{
          padding: collapsed ? '20px 16px' : '24px 20px',
          display: 'flex',
          alignItems: 'center',
          gap: 12,
          borderBottom: '1px solid var(--bg-border)',
          minHeight: 72,
        }}>
          <div style={{
            width: 32, height: 32, flexShrink: 0,
            background: 'linear-gradient(135deg, var(--gold), var(--gold-dim))',
            borderRadius: 8,
            display: 'flex', alignItems: 'center', justifyContent: 'center',
          }}>
            <Wallet size={16} color="#080c14" strokeWidth={2.5} />
          </div>
          {!collapsed && (
            <div>
              <div style={{ fontFamily: 'var(--font-display)', fontSize: '1rem', fontWeight: 600, color: 'var(--text-primary)', lineHeight: 1 }}>
                WealthPilot
              </div>
              <div style={{ fontSize: '0.65rem', color: 'var(--gold)', letterSpacing: '0.1em', textTransform: 'uppercase', marginTop: 2 }}>
                Finance Platform
              </div>
            </div>
          )}
        </div>

        {/* Nav */}
        <nav style={{ flex: 1, padding: '12px 8px', display: 'flex', flexDirection: 'column', gap: 2 }}>
          {NAV.map(({ to, icon: Icon, label }) => (
            <NavLink
              key={to}
              to={to}
              end={to === '/'}
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: 12,
                padding: collapsed ? '10px 16px' : '10px 12px',
                borderRadius: 'var(--radius-md)',
                color: isActive ? 'var(--gold)' : 'var(--text-secondary)',
                background: isActive ? 'var(--gold-muted)' : 'transparent',
                border: isActive ? '1px solid rgba(201,168,76,0.2)' : '1px solid transparent',
                transition: 'all 0.15s',
                textDecoration: 'none',
                fontSize: '0.875rem',
                fontWeight: isActive ? 600 : 400,
                whiteSpace: 'nowrap',
                justifyContent: collapsed ? 'center' : 'flex-start',
              })}
            >
              <Icon size={18} strokeWidth={1.8} />
              {!collapsed && label}
            </NavLink>
          ))}
        </nav>

        {/* User + logout */}
        <div style={{
          padding: collapsed ? '12px 8px' : '12px',
          borderTop: '1px solid var(--bg-border)',
          display: 'flex',
          flexDirection: 'column',
          gap: 8,
        }}>
          {!collapsed && (
            <div style={{
              padding: '10px 12px',
              background: 'var(--bg-elevated)',
              borderRadius: 'var(--radius-md)',
              border: '1px solid var(--bg-border)',
            }}>
              <div style={{ fontSize: '0.8rem', fontWeight: 500, color: 'var(--text-primary)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user?.full_name || 'User'}
              </div>
              <div style={{ fontSize: '0.7rem', color: 'var(--text-muted)', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                {user?.email}
              </div>
            </div>
          )}
          <button
            onClick={handleLogout}
            style={{
              display: 'flex', alignItems: 'center',
              gap: 8, padding: '8px 12px',
              background: 'transparent',
              border: '1px solid transparent',
              borderRadius: 'var(--radius-md)',
              color: 'var(--text-muted)',
              cursor: 'pointer', fontSize: '0.8rem',
              transition: 'all 0.15s',
              justifyContent: collapsed ? 'center' : 'flex-start',
            }}
            onMouseEnter={e => { e.currentTarget.style.color = 'var(--red)'; e.currentTarget.style.background = 'var(--red-dim)'; }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.background = 'transparent'; }}
          >
            <LogOut size={15} />
            {!collapsed && 'Logout'}
          </button>
        </div>

        {/* Collapse toggle */}
        <button
          onClick={() => setCollapsed(c => !c)}
          style={{
            position: 'absolute',
            top: 22,
            right: collapsed ? -12 : -12,
            width: 24, height: 24,
            background: 'var(--bg-elevated)',
            border: '1px solid var(--bg-border)',
            borderRadius: '50%',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            cursor: 'pointer', color: 'var(--text-muted)',
            transition: 'all 0.2s',
            zIndex: 30,
          }}
        >
          {collapsed ? <ChevronRight size={12} /> : <X size={12} />}
        </button>
      </aside>

      {/* ── Main content ── */}
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflow: 'hidden', position: 'relative' }}>

        {/* Topbar */}
        <header style={{
          height: 64,
          background: 'var(--bg-surface)',
          borderBottom: '1px solid var(--bg-border)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          padding: '0 28px',
          flexShrink: 0,
        }}>
          <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
            {new Date().toLocaleDateString('en-IN', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
            <button style={{
              background: 'var(--bg-elevated)',
              border: '1px solid var(--bg-border)',
              borderRadius: 'var(--radius-md)',
              padding: '6px 8px',
              color: 'var(--text-secondary)',
              cursor: 'pointer',
              display: 'flex', alignItems: 'center',
            }}>
              <Bell size={15} />
            </button>
            <div style={{
              width: 32, height: 32,
              background: 'linear-gradient(135deg, var(--gold-dim), var(--gold))',
              borderRadius: '50%',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '0.8rem', fontWeight: 600, color: 'var(--bg-base)',
            }}>
              {(user?.full_name || user?.email || 'U')[0].toUpperCase()}
            </div>
          </div>
        </header>

        {/* Page content */}
        <main style={{ flex: 1, overflow: 'auto', padding: '28px' }}>
          <Outlet />
        </main>
      </div>
    </div>
  )
}
