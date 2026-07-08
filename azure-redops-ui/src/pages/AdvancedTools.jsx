import { useEffect, useState } from 'react'
import { Terminal, Play, Trash2, Key, Plus, RefreshCw, Search } from 'lucide-react'
import RunActivityModal from '../components/RunActivityModal'
import { useToast } from '../components/Toast'
import { tokensApi, sessionsApi } from '../lib/api'
import Modal from '../components/Modal'
import JWTDecoder from '../components/JWTDecoder'
import { formatDate, truncate } from '../lib/utils'

const initialForm = {
  name: '',
  access_token: '',
  refresh_token: '',
  scope: '',
  client_id: '',
  account: '',
  tenant_id: 'common',
  expires_in: 3600
}

export default function AdvancedTools() {
  const toast = useToast()
  const [runOpen, setRunOpen] = useState(false)
  const [tokens, setTokens] = useState([])
  const [sessions, setSessions] = useState([])
  const [search, setSearch] = useState('')
  const [decoderState, setDecoderState] = useState({ open: false, name: null, raw: null })
  const [addOpen, setAddOpen] = useState(false)
  const [form, setForm] = useState(initialForm)
  const [loading, setLoading] = useState(true)

  const filtered = (tokens || []).filter((t) => {
    if (!search.trim()) return true
    const q = search.toLowerCase()
    return [t.name, t.account, t.scope, t.client_id].filter(Boolean).join(' ').toLowerCase().includes(q)
  })

  const refresh = async () => {
    setLoading(true)
    try {
      const [t, s] = await Promise.all([
        tokensApi.list().catch(() => []),
        sessionsApi.list().catch(() => [])
      ])
      setTokens(Array.isArray(t) ? t : [])
      setSessions(Array.isArray(s) ? s : [])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { refresh() }, [])

  const deleteToken = async (n) => {
    try {
      await tokensApi.remove(n)
      setTokens((arr) => arr.filter((t) => t.name !== n))
      toast.success(`${n} deleted`)
    } catch {
      toast.error(`Failed to delete ${n}`)
    }
  }

  const save = async () => {
    if (!form.name || !form.access_token) {
      return toast.error('Name and access_token are required')
    }
    try {
      await tokensApi.save(form)
      setAddOpen(false)
      setForm(initialForm)
      await refresh()
      toast.success(`Token '${form.name}' saved`)
    } catch {
      toast.error('Save failed')
    }
  }

  const openDecoder = (token) => {
    if (!token || !token.name) {
      toast.error('Cannot decode: invalid token row')
      return
    }
    setDecoderState({ open: true, name: token.name, raw: null })
  }

  const refreshToken = async (name) => {
    if (!name) return toast.error('No token name to refresh')
    try {
      const r = await tokensApi.refresh(name)
      toast.success(r?.capture ? `Refreshed ${name}` : `Refresh submitted for ${name}`)
      await refresh()
    } catch {
      toast.error(`Refresh failed for ${name}`)
    }
  }

  return (
    <div className="space-y-6">
      <div className="glass rounded-2xl p-6 border border-white/10">
        <div className="flex items-center justify-between mb-4">
          <div>
            <h2 className="text-xl font-semibold text-white flex items-center gap-2">
              <Terminal size={18} className="text-accent" />Advanced CLI Runner
            </h2>
            <p className="text-sm text-gray-400 mt-1">
              Execute every activity from AzureRedOps with full flag control via the backend.
            </p>
          </div>
          <button onClick={() => setRunOpen(true)}
            className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-accent to-purple text-white font-medium shadow-glow flex items-center gap-2">
            <Play size={16} />Run Activity
          </button>
        </div>
      </div>

      <div className="glass rounded-2xl p-6 border border-white/10">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Key size={18} />Persistent Token Store
            <span className="text-xs text-gray-400 bg-white/5 px-2 py-1 rounded-full">{tokens.length} saved</span>
          </h3>
          <div className="flex items-center gap-3">
            <div className="relative">
              <Search size={12} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                placeholder="Search tokens…"
                className="pl-8 pr-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-sm w-48"
              />
            </div>
            <button onClick={refresh} className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 text-xs flex items-center gap-1">
              <RefreshCw size={12} />Refresh
            </button>
            <button onClick={() => setAddOpen(true)} className="px-3 py-1.5 rounded-lg bg-accent/15 text-accent text-xs flex items-center gap-1">
              <Plus size={12} />Add
            </button>
          </div>
        </div>

        {loading ? (
          <div className="text-center text-gray-500 py-6 text-sm flex items-center justify-center gap-2">
            <RefreshCw size={14} className="animate-spin" />Loading tokens from backend…
          </div>
        ) : filtered.length === 0 ? (
          <div className="text-center text-gray-500 py-6 text-sm">
            {tokens.length === 0
              ? 'No tokens yet — run an activity with -s/-n flags, or click Add.'
              : `No tokens match "${search}".`}
          </div>
        ) : (
          <div className="space-y-2">
            {filtered.map((t) => (
              <div key={t.name} className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10">
                <div className="min-w-0 flex-1">
                  <div className="text-white font-medium truncate">{t.name}</div>
                  <div className="text-xs text-gray-400 mt-0.5 truncate">
                    {truncate(t.account, 36) || '—'} • scope: {truncate(t.scope, 30) || '—'} • created {formatDate(t.created_at)}
                  </div>
                </div>
                <div className="flex gap-2 flex-shrink-0">
                  <button onClick={() => openDecoder(t)} className="px-3 py-1.5 rounded-lg bg-accent/15 text-accent text-xs hover:bg-accent/25">Decode</button>
                  <button onClick={() => refreshToken(t.name)} className="px-3 py-1.5 rounded-lg bg-success/15 text-success text-xs hover:bg-success/25">Refresh</button>
                  <button onClick={() => deleteToken(t.name)} className="px-3 py-1.5 rounded-lg bg-danger/15 text-danger text-xs hover:bg-danger/25 flex items-center gap-1">
                    <Trash2 size={12} />Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="glass rounded-2xl p-6 border border-white/10">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold text-white flex items-center gap-2">
            <Key size={18} className="text-purple" />Saved Sessions
            <span className="text-xs text-gray-400 bg-white/5 px-2 py-1 rounded-full">{sessions.length} captured</span>
          </h3>
          <button onClick={refresh} className="px-3 py-1.5 rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 text-xs flex items-center gap-1">
            <RefreshCw size={12} />Refresh
          </button>
        </div>
        {sessions.length === 0 ? (
          <div className="text-center text-gray-500 py-6 text-sm">No captured sessions yet — start a phish flow.</div>
        ) : (
          <div className="space-y-2">
            {sessions.slice(0, 20).map((s) => (
              <div key={s.id} className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10">
                <div className="min-w-0 flex-1">
                  <div className="text-white font-medium truncate">{s.email || s.name || 'unknown'}</div>
                  <div className="text-xs text-gray-400 mt-0.5 truncate">
                    {s.country || 'UNK'} • {s.status || 'Active'} • captured {formatDate(s.captured)}
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      <RunActivityModal open={runOpen} onClose={() => setRunOpen(false)} />
      <Modal open={addOpen} onClose={() => setAddOpen(false)} title="Save Token" size="md"
        footer={<>
          <button onClick={() => setAddOpen(false)} className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm text-gray-300">Cancel</button>
          <button onClick={save} className="px-4 py-2 rounded-lg bg-accent hover:brightness-110 text-sm text-white shadow-glow">Save</button>
        </>}>
        <div className="space-y-3">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Name</label>
            <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="my_token" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Access Token</label>
            <input value={form.access_token} onChange={(e) => setForm({ ...form, access_token: e.target.value })} placeholder="eyJ…" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Refresh Token</label>
            <input value={form.refresh_token} onChange={(e) => setForm({ ...form, refresh_token: e.target.value })} />
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-xs text-gray-400 mb-1">Account</label>
              <input value={form.account} onChange={(e) => setForm({ ...form, account: e.target.value })} placeholder="[email protected]" />
            </div>
            <div>
              <label className="block text-xs text-gray-400 mb-1">Scope</label>
              <input value={form.scope} onChange={(e) => setForm({ ...form, scope: e.target.value })} />
            </div>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Client ID</label>
            <input value={form.client_id} onChange={(e) => setForm({ ...form, client_id: e.target.value })} />
          </div>
        </div>
      </Modal>

      {decoderState.open && decoderState.name && (
        <JWTDecoder
          open
          onClose={() => setDecoderState({ open: false, name: null, raw: null })}
          tokenName={decoderState.name}
          rawToken={decoderState.raw}
        />
      )}
    </div>
  )
}