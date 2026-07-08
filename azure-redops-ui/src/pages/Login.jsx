import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Shield, Lock, Mail, Eye, EyeOff } from 'lucide-react'
import { useToast } from '../components/Toast'
import ParticlesBackground from '../components/ParticlesBackground'

export default function Login() {
  const nav = useNavigate()
  const toast = useToast()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [show, setShow] = useState(false)
  const [loading, setLoading] = useState(false)

  const submit = async (e) => {
    e.preventDefault()
    if (!email || !password) return toast.error('Email and password required')
    setLoading(true)
    await new Promise((r) => setTimeout(r, 600))
    localStorage.setItem('azr_token', 'demo.' + Math.random().toString(36).slice(2))
    localStorage.setItem('azr_user', JSON.stringify({ name: 'Operator', email }))
    toast.success('Welcome back')
    setLoading(false)
    nav('/admin/dashboard')
  }

  return (
    <div className="min-h-screen flex items-center justify-center relative overflow-hidden bg-bg">
      <ParticlesBackground />
      <div className="absolute inset-0" style={{ background: 'radial-gradient(circle at 20% 30%, rgba(52,152,219,0.18), transparent 50%), radial-gradient(circle at 80% 70%, rgba(155,89,182,0.18), transparent 50%)' }} />
      <div className="relative w-full max-w-md mx-4 z-10">
        <div className="text-center mb-8 animate-fade-in">
          <div className="inline-flex w-16 h-16 rounded-2xl bg-gradient-to-br from-accent to-purple items-center justify-center shadow-glow mb-4">
            <Shield size={32} className="text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-1">AzureRedOps</h1>
          <p className="text-gray-400 text-sm">Operator console • secure access</p>
        </div>
        <form onSubmit={submit} className="glass-strong rounded-2xl p-7 shadow-glow animate-slide-up">
          <h2 className="text-xl font-semibold text-white mb-5">Sign in</h2>
          <label className="block text-xs text-gray-400 mb-1.5">Operator Email</label>
          <div className="relative mb-4">
            <Mail size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder="[email protected]" className="w-full pl-10" autoFocus />
          </div>
          <label className="block text-xs text-gray-400 mb-1.5">Password</label>
          <div className="relative mb-5">
            <Lock size={16} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input type={show ? 'text' : 'password'} value={password} onChange={(e) => setPassword(e.target.value)} placeholder="••••••••" className="w-full pl-10 pr-10" />
            <button type="button" onClick={() => setShow(!show)} className="absolute right-3 top-1/2 -translate-y-1/2 text-gray-400">
              {show ? <EyeOff size={16} /> : <Eye size={16} />}
            </button>
          </div>
          <div className="flex items-center justify-between mb-5 text-xs">
            <label className="flex items-center gap-2 text-gray-400 cursor-pointer">
              <input type="checkbox" className="w-4 h-4" style={{ accentColor: '#3498db' }} />Remember me
            </label>
            <a href="#" className="text-accent hover:underline">Forgot password?</a>
          </div>
          <button type="submit" disabled={loading} className="w-full py-3 rounded-xl bg-gradient-to-r from-accent to-purple text-white font-semibold shadow-glow hover:brightness-110 disabled:opacity-50 transition">
            {loading ? 'Signing in...' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
