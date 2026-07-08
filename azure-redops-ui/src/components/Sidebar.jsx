import { NavLink, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Users, Send, Settings, Terminal, LogOut, Shield } from 'lucide-react'

const items = [
  { to: '/admin/dashboard', label: 'Dashboard', Icon: LayoutDashboard },
  { to: '/admin/leads', label: 'Leads', Icon: Users },
  { to: '/admin/sender', label: 'Sender', Icon: Send },
  { to: '/admin/settings', label: 'Settings', Icon: Settings },
  { to: '/admin/advanced', label: 'Advanced Tools', Icon: Terminal }
]

export default function Sidebar() {
  const nav = useNavigate()
  const user = JSON.parse(localStorage.getItem('azr_user') || '{}')
  const logout = () => {
    localStorage.removeItem('azr_token')
    localStorage.removeItem('azr_user')
    nav('/login')
  }
  return (
    <aside className="w-64 h-screen flex-shrink-0 bg-[#16161e] border-r border-white/5 flex flex-col">
      <div className="px-6 py-6 flex items-center gap-3 border-b border-white/5">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-accent to-purple flex items-center justify-center shadow-glow">
          <Shield size={20} className="text-white" />
        </div>
        <div>
          <div className="font-bold text-white">AzureRedOps</div>
          <div className="text-xs text-gray-400">Operator Console</div>
        </div>
      </div>
      <nav className="flex-1 px-3 py-4 space-y-1">
        {items.map((item) => (
          <NavLink key={item.to} to={item.to} className={({ isActive }) =>
            `flex items-center gap-3 px-4 py-3 rounded-xl text-sm transition-all ${isActive ? 'bg-gradient-to-r from-accent/20 to-purple/10 text-white border border-accent/30 shadow-glow' : 'text-gray-400 hover:text-white hover:bg-white/5'}`
          }>
            <item.Icon size={18} /><span>{item.label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="p-4 border-t border-white/5">
        <div className="flex items-center gap-3 mb-3 px-2">
          <div className="w-9 h-9 rounded-full bg-gradient-to-br from-success to-accent flex items-center justify-center text-sm font-bold">
            {(user.name || 'O')[0].toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-sm font-medium text-white truncate">{user.name || 'Operator'}</div>
            <div className="text-xs text-gray-400 truncate">{user.email || '[email protected]'}</div>
          </div>
        </div>
        <button onClick={logout} className="w-full flex items-center justify-center gap-2 px-3 py-2 rounded-lg bg-white/5 hover:bg-danger/20 hover:text-danger text-gray-400 text-sm transition">
          <LogOut size={16} />Logout
        </button>
      </div>
    </aside>
  )
}
