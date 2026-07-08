import { createContext, useContext, useState, useCallback } from 'react'
import { CheckCircle, AlertCircle, Info, X } from 'lucide-react'

const Ctx = createContext(null)
export const useToast = () => useContext(Ctx)

export function ToastProvider({ children }) {
  const [items, setItems] = useState([])
  const push = useCallback((msg, type = 'info') => {
    const id = Math.random().toString(36).slice(2)
    setItems((a) => [...a, { id, msg, type }])
    setTimeout(() => setItems((a) => a.filter((t) => t.id !== id)), 4000)
  }, [])
  const api = { success: (m) => push(m, 'success'), error: (m) => push(m, 'error'), info: (m) => push(m, 'info') }
  return (
    <Ctx.Provider value={api}>
      {children}
      <div className="fixed bottom-6 right-6 z-50 flex flex-col gap-2 pointer-events-none">
        {items.map((t) => (
          <div key={t.id} className="glass-strong pointer-events-auto rounded-xl px-4 py-3 flex items-center gap-3 shadow-glow min-w-[280px] animate-slide-up">
            {t.type === 'success' && <CheckCircle size={20} className="text-success flex-shrink-0" />}
            {t.type === 'error' && <AlertCircle size={20} className="text-danger flex-shrink-0" />}
            {t.type === 'info' && <Info size={20} className="text-accent flex-shrink-0" />}
            <span className="flex-1 text-sm">{t.msg}</span>
            <button onClick={() => setItems((a) => a.filter((x) => x.id !== t.id))} className="text-gray-400 hover:text-white"><X size={16} /></button>
          </div>
        ))}
      </div>
    </Ctx.Provider>
  )
}
