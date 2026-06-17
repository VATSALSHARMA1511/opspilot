import { Link, useNavigate, useLocation } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'
import { LayoutDashboard, Ticket, LogOut } from 'lucide-react'
import client from '../api/client'

export default function Layout({ children }) {
  const { logout } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const handleLogout = async () => {
    try { await client.post('/api/v1/auth/logout') } catch {}
    logout()
    navigate('/login')
  }

  const nav = [
    { label: 'Dashboard', href: '/', icon: LayoutDashboard },
    { label: 'Tickets', href: '/tickets', icon: Ticket },
  ]

  return (
    <div className="min-h-screen bg-zinc-950 flex">
      <aside className="w-56 border-r border-zinc-800 flex flex-col py-6 px-4">
        <span className="text-white font-semibold text-base mb-8 px-2">OpsPilot</span>
        <nav className="flex flex-col gap-1 flex-1">
          {nav.map(({ label, href, icon: Icon }) => (
            <Link
              key={href}
              to={href}
              className={`flex items-center gap-3 px-2 py-2 rounded-md text-sm transition-colors
                ${location.pathname === href
                  ? 'bg-zinc-800 text-white'
                  : 'text-zinc-400 hover:text-white hover:bg-zinc-900'}`}
            >
              <Icon size={16} />
              {label}
            </Link>
          ))}
        </nav>
        <button
          onClick={handleLogout}
          className="flex items-center gap-3 px-2 py-2 rounded-md text-sm text-zinc-400 hover:text-white hover:bg-zinc-900 transition-colors"
        >
          <LogOut size={16} />
          Logout
        </button>
      </aside>
      <main className="flex-1 p-8 overflow-y-auto">
        {children}
      </main>
    </div>
  )
}