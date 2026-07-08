import { ArrowDownRight, ArrowUpRight } from 'lucide-react'

const accentClasses = {
  accent: 'text-accent bg-accent/15 border-accent/25',
  purple: 'text-purple bg-purple/15 border-purple/25',
  success: 'text-success bg-success/15 border-success/25',
  danger: 'text-danger bg-danger/15 border-danger/25',
}

export default function StatCard({ icon: Icon, label, value, accent = 'accent', change }) {
  const tone = accentClasses[accent] || accentClasses.accent
  const positive = Number(change) >= 0
  const ChangeIcon = positive ? ArrowUpRight : ArrowDownRight

  return (
    <div className="glass rounded-2xl border border-white/10 p-4">
      <div className="flex items-start justify-between gap-3">
        <div className={`w-10 h-10 rounded-xl border flex items-center justify-center ${tone}`}>
          {Icon && <Icon size={20} />}
        </div>
        {change !== undefined && (
          <div className={`flex items-center gap-1 text-xs ${positive ? 'text-success' : 'text-danger'}`}>
            <ChangeIcon size={13} />
            <span>{Math.abs(change)}%</span>
          </div>
        )}
      </div>
      <div className="mt-4">
        <div className="text-2xl font-semibold text-white leading-tight">{value}</div>
        <div className="mt-1 text-sm text-gray-400">{label}</div>
      </div>
    </div>
  )
}
