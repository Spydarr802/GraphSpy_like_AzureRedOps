import { useEffect, useState } from 'react'
import { Key, Copy, RefreshCw } from 'lucide-react'
import Modal from './Modal'
import { useToast } from './Toast'
import { tokensApi, oauthApi } from '../lib/api'
import { copy } from '../lib/utils'

export default function JWTDecoder({ open, onClose, tokenName, rawToken }) {
  const toast = useToast()
  const [decoded, setDecoded] = useState(null)
  const [loading, setLoading] = useState(false)
  const [autoRefresh, setAutoRefresh] = useState(false)

  useEffect(() => {
    if (!open) return
    setLoading(true)
    setDecoded(null)
    if (rawToken) {
      tokensApi.decodeRaw(rawToken).then(setDecoded).finally(() => setLoading(false))
    } else if (tokenName) {
      tokensApi.decode(tokenName).then(setDecoded).finally(() => setLoading(false))
    } else {
      setLoading(false)
    }
  }, [open, tokenName, rawToken])

  return (
    <Modal open={open} onClose={onClose} title="JWT Decoder" size="lg"
      footer={<>
        <button onClick={onClose} className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm text-gray-300">Close</button>
        <button onClick={async () => { const ok = await copy(rawToken || (decoded && decoded.signature_present ? '' : '')); ok ? toast.success('Copied') : toast.error('Copy failed') }}
          className="px-4 py-2 rounded-lg bg-accent hover:brightness-110 text-sm text-white shadow-glow flex items-center gap-2">
          <Copy size={14} />Copy
        </button>
      </>}>
      {loading ? (
        <div className="text-center text-gray-400 py-12"><RefreshCw className="animate-spin inline" size={20} /> Decoding...</div>
      ) : !decoded ? (
        <div className="text-center text-gray-500 py-12">No token to decode</div>
      ) : (
        <div className="space-y-4">
          <div className="grid grid-cols-2 gap-3">
            <div className="p-3 rounded-lg bg-white/5 border border-white/10">
              <div className="text-xs text-gray-400 mb-1">Algorithm</div>
              <div className="text-sm text-accent font-mono">{decoded.header?.alg || '—'}</div>
            </div>
            <div className="p-3 rounded-lg bg-white/5 border border-white/10">
              <div className="text-xs text-gray-400 mb-1">Type</div>
              <div className="text-sm text-accent font-mono">{decoded.header?.typ || '—'}</div>
            </div>
            <div className="p-3 rounded-lg bg-white/5 border border-white/10">
              <div className="text-xs text-gray-400 mb-1">Signature</div>
              <div className="text-sm font-mono">{decoded.signature_present ? <span className="text-success">Present</span> : <span className="text-danger">Missing</span>}</div>
            </div>
            <div className="p-3 rounded-lg bg-white/5 border border-white/10">
              <div className="text-xs text-gray-400 mb-1">Expired</div>
              <div className="text-sm font-mono">{decoded.is_expired ? <span className="text-danger">Yes</span> : <span className="text-success">No</span>}</div>
            </div>
          </div>
          {decoded.expires_at_iso && (
            <div className="p-3 rounded-lg bg-white/5 border border-white/10">
              <div className="text-xs text-gray-400 mb-1">Expires at</div>
              <div className="text-sm text-white font-mono">{decoded.expires_at_iso}</div>
            </div>
          )}
          <div>
            <div className="text-xs text-gray-400 mb-1 flex items-center gap-2"><Key size={12} />Payload (claims)</div>
            <pre className="bg-black/40 p-4 rounded-lg text-xs text-green-300 overflow-auto max-h-72 font-mono">{JSON.stringify(decoded.payload, null, 2)}</pre>
          </div>
          <div>
            <div className="text-xs text-gray-400 mb-1">Header</div>
            <pre className="bg-black/40 p-4 rounded-lg text-xs text-purple-300 overflow-auto max-h-32 font-mono">{JSON.stringify(decoded.header, null, 2)}</pre>
          </div>
        </div>
      )}
    </Modal>
  )
}
