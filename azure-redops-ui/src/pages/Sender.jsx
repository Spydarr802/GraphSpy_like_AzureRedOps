import { useState } from 'react'
import { Send, Upload, Plus, X, FileText, Briefcase } from 'lucide-react'
import Modal from '../components/Modal'
import { useToast } from '../components/Toast'

const PLACEHOLDERS = ['[[user]]', '[[full_name]]', '[[random_string]]', '[[email]]', '[[company]]']

export default function Sender() {
  const [open, setOpen] = useState(false)
  const [recipients, setRecipients] = useState('')
  const [subject, setSubject] = useState('')
  const [body, setBody] = useState('Hello [[full_name]], please review the attached document.')
  const [template, setTemplate] = useState('OneDrive')
  const [attachments, setAttachments] = useState([])
  const toast = useToast()
  const insertPlaceholder = (p) => setBody((b) => b + ' ' + p)
  const files = (e) => setAttachments((a) => [...a, ...Array.from(e.target.files).map((f) => f.name)])
  const send = () => {
    if (!recipients || !subject) return toast.error('Recipients and subject required')
    toast.success(`Campaign queued for ${recipients.split('\n').length} recipient(s)`)
    setOpen(false)
  }
  const pull = (provider) => toast.info(`Pulling contacts from ${provider}…`)

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-xl font-semibold text-white">Campaign Sender</h2>
          <p className="text-sm text-gray-400 mt-1">Send phishing campaigns with placeholders and attachments</p>
        </div>
        <button onClick={() => setOpen(true)}
          className="px-5 py-2.5 rounded-xl bg-gradient-to-r from-accent to-purple text-white font-medium shadow-glow flex items-center gap-2 hover:brightness-110">
          <Plus size={16} />New Campaign
        </button>
      </div>
      <div className="glass rounded-2xl p-6 border border-white/10">
        <h3 className="text-lg font-semibold text-white mb-4">Quick Actions</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          <button onClick={() => pull('Office 365')} className="p-4 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-left transition">
            <Briefcase className="text-accent mb-2" size={20} />
            <div className="text-white font-medium">Pull from Office 365</div>
            <div className="text-xs text-gray-400 mt-1">Sync contacts from Microsoft 365</div>
          </button>
          <button onClick={() => pull('GSuite')} className="p-4 rounded-xl bg-white/5 hover:bg-white/10 border border-white/10 text-left transition">
            <FileText className="text-success mb-2" size={20} />
            <div className="text-white font-medium">Pull from GSuite</div>
            <div className="text-xs text-gray-400 mt-1">Sync contacts from Google Workspace</div>
          </button>
        </div>
      </div>
      <Modal open={open} onClose={() => setOpen(false)} title="New Phishing Campaign" size="xl"
        footer={<>
          <button onClick={() => setOpen(false)} className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm text-gray-300">Cancel</button>
          <button onClick={send} className="px-4 py-2 rounded-lg bg-gradient-to-r from-accent to-purple text-sm text-white shadow-glow flex items-center gap-2">
            <Send size={14} />Send Campaign
          </button>
        </>}>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Choose Template</label>
            <select value={template} onChange={(e) => setTemplate(e.target.value)}>
              <option>OneDrive</option><option>SharePoint</option><option>Excel Online</option>
              <option>Adobe Sign</option><option>DocuSign</option><option>Microsoft 365</option>
            </select>
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Subject</label>
            <input value={subject} onChange={(e) => setSubject(e.target.value)} placeholder="Important document shared with you" />
          </div>
        </div>
        <div className="mt-4">
          <label className="block text-xs text-gray-400 mb-1">Recipients (one per line)</label>
          <textarea value={recipients} onChange={(e) => setRecipients(e.target.value)} rows={4} placeholder="[email protected]\n[email protected]" />
        </div>
        <div className="mt-4">
          <div className="flex items-center justify-between mb-1">
            <label className="block text-xs text-gray-400">Body (HTML supported)</label>
            <div className="flex gap-1 flex-wrap">
              {PLACEHOLDERS.map((p) => (
                <button key={p} type="button" onClick={() => insertPlaceholder(p)}
                  className="text-[10px] px-2 py-1 rounded bg-accent/15 text-accent hover:bg-accent/25">{p}</button>
              ))}
            </div>
          </div>
          <textarea value={body} onChange={(e) => setBody(e.target.value)} rows={6} className="font-mono text-xs" />
        </div>
        <div className="mt-4">
          <label className="block text-xs text-gray-400 mb-2">Attachments</label>
          <label className="flex items-center justify-center gap-2 p-4 rounded-xl border-2 border-dashed border-white/10 hover:border-accent/40 cursor-pointer transition">
            <Upload size={16} className="text-gray-400" />
            <span className="text-sm text-gray-300">Click to upload files</span>
            <input type="file" multiple onChange={files} className="hidden" />
          </label>
          {attachments.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {attachments.map((a, i) => (
                <div key={i} className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-white/5 text-xs text-gray-300">
                  <FileText size={12} />{a}
                  <button onClick={() => setAttachments((arr) => arr.filter((_, idx) => idx !== i))} className="text-danger hover:brightness-125"><X size={12} /></button>
                </div>
              ))}
            </div>
          )}
        </div>
      </Modal>
    </div>
  )
}
