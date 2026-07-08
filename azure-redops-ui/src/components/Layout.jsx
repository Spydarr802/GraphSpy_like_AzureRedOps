import { Outlet, useLocation } from 'react-router-dom'
import Sidebar from './Sidebar'
import { Search, Bell } from 'lucide-react'

const titles = {
  '/admin/dashboard': 'Dashboard',
  '/admin/leads': 'Leads Extraction',
  '/admin/sender': 'Campaign Sender',
  '/admin/settings': 'Settings',
  '/admin/advanced': 'Advanced Tools'
}

export default function Layout() {
  const loc = useLocation()
  const title = titles[loc.pathname] || 'AzureRedOps'
  return (
    <div className="flex h-screen overflow-hidden bg-bg">
      <Sidebar />
      <main className="flex-1 flex flex-col overflow-hidden">
        <header className="h-16 flex items-center justify-between px-6 border-b border-white/5 bg-[#16161e] flex-shrink-0">
          <h1 className="text-xl font-semibold text-white">{title}</h1>
          <div className="flex items-center gap-4">
            <div className="relative">
              <Search size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input placeholder="Search..." className="pl-9 pr-4 py-2 w-64 text-sm bg-white/5 border border-white/10 rounded-lg" />
            </div>
            <button className="relative w-10 h-10 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center text-gray-400">
              <Bell size={18} />
              <span className="absolute top-2 right-2 w-2 h-2 bg-danger rounded-full" />
            </button>
          </div>
        </header>
        <div className="flex-1 overflow-y-auto p-6 animate-fade-in"><Outlet /></div>
      </main>
    </div>
  )
}
