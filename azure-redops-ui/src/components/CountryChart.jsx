import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

export default function CountryChart({ data }) {
  const colors = ['#3498db', '#9b59b6', '#2ecc71', '#e74c3c', '#f1c40f', '#e67e22', '#1abc9c']
  return (
    <div className="glass rounded-2xl p-5 border border-white/10">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-semibold text-white">Captures by Country</h3>
        <div className="text-xs text-gray-400">Last 7 days</div>
      </div>
      <ResponsiveContainer width="100%" height={280}>
        <BarChart data={data} layout="vertical" margin={{ left: 24, right: 16, top: 8, bottom: 8 }}>
          <XAxis type="number" stroke="#777" />
          <YAxis dataKey="country" type="category" stroke="#ccc" width={120} tick={{ fontSize: 12 }} />
          <Tooltip contentStyle={{ background: '#1e1e2e', border: '1px solid #444', borderRadius: 10, color: '#fff' }} cursor={{ fill: 'rgba(255,255,255,0.05)' }} />
          <Bar dataKey="captures" radius={[0, 6, 6, 0]}>
            {data.map((_, i) => <Cell key={i} fill={colors[i % colors.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}
