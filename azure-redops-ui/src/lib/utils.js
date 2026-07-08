export const formatDate = (iso) => iso ? new Date(iso).toLocaleString() : '—'
export const flag = (c) => !c ? '🌐' : String.fromCodePoint(...[...c.toUpperCase()].map(x => 127397 + x.charCodeAt(0)))
export const truncate = (s, n = 40) => s && s.length > n ? s.slice(0, n) + '…' : s || ''
export const copy = async (t) => { try { await navigator.clipboard.writeText(t); return true } catch { return false } }
export const downloadFile = (content, filename, type = 'application/json') => {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a'); a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}
