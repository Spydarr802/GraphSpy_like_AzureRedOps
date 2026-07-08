import { useEffect, useRef, useState } from 'react'
import Modal from './Modal'
import { useToast } from './Toast'
import { activitiesApi } from '../lib/api'
import { Play, Terminal, Square } from 'lucide-react'

const ACTIVITY_META = {
  'self':           { label: 'Who am I? (-a self)',            tokens: true,  flags: [] },
  'list-users':     { label: 'List Users',                       tokens: true,  flags: ['beta','json','fields'] },
  'list-applications':{ label: 'List Applications',              tokens: true,  flags: ['beta','json','fields'] },
  'register-app':   { label: 'Register Application',             tokens: true,  flags: ['name'] },
  'add-group':      { label: 'Assign Global Admin (add-group)',  tokens: true,  flags: ['uid'] },
  'push-file':      { label: 'Upload File to OneDrive',          tokens: true,  flags: ['fp','name'] },
  'gather-all':     { label: 'Gather All',                        tokens: true,  flags: ['json'] },
  'raw-url':        { label: 'Raw Graph URL',                    tokens: true,  flags: ['url','json','fields'] },
  'invite':         { label: 'Invite External User',             tokens: true,  flags: ['name','url'] },
  'magic-app':      { label: 'Hunt magic-app',                   tokens: true,  flags: [] },
  'spray':          { label: 'Password Spray',                    tokens: false, flags: ['u','p','tid','check_privs'] },
  'spray-refresh':  { label: 'Refresh Spray',                     tokens: true,  flags: ['v'] },
  'knownids':       { label: 'Known App IDs',                     tokens: false, flags: ['fields'] },
  'list-interest':  { label: 'List Interest',                     tokens: false, flags: [] },
  'interest':       { label: 'Interesting Apps',                  tokens: true,  flags: ['i','ty'] },
  'auth':           { label: 'ROPC Authentication',               tokens: false, flags: ['u','p','sc'], interactive: true },
  'phish-start':    { label: 'Device Code — Start',               tokens: false, flags: ['tid','name'], interactive: true },
  'phish-capture':  { label: 'Device Code — Capture',             tokens: false, flags: ['code','name'], interactive: true },
  'auth-app':       { label: 'Auth App (PKCE)',                   tokens: false, flags: ['name'], interactive: true },
  'list':           { label: 'List Tokens',                        tokens: false, flags: [] },
  'save':           { label: 'Save Token',                        tokens: false, flags: ['name','token'] },
  'load':           { label: 'Load Token',                        tokens: false, flags: ['name'] },
  'delete':         { label: 'Delete Token',                      tokens: false, flags: ['name'] },
  'add-roles':      { label: 'Add Roles (Graph consent)',          tokens: true,  flags: [] }
}

const INTERACTIVE_LABELS = {
  'auth':          'login prompt',
  'auth-app':      'browser auth',
  'phish-start':   'device-code flow',
  'phish-capture': 'waiting for token'
}

export default function RunActivityModal({ open, onClose }) {
  const toast = useToast()
  const [activity, setActivity] = useState('self')
  const [tokenName, setTokenName] = useState('')
  const [flags, setFlags] = useState({})
  const [out, setOut] = useState('')
  const [running, setRunning] = useState(false)
  const [saveToken, setSaveToken] = useState(false)
  const [backendActivities, setBackendActivities] = useState([])
  const [testMode, setTestMode] = useState(false)
  const [jobId, setJobId] = useState(null)
  const pollRef = useRef(null)

  const meta = ACTIVITY_META[activity] || { label: activity, flags: [], tokens: false }
  const isInteractive = meta.interactive === true

  useEffect(() => {
    if (!open) {
      if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
      setJobId(null)
      return
    }
    activitiesApi.list()
      .then((d) => {
        if (Array.isArray(d.activities)) setBackendActivities(d.activities)
        setTestMode(!!d.test_mode)
      })
      .catch(() => {})
  }, [open])

  useEffect(() => () => { if (pollRef.current) clearInterval(pollRef.current) }, [])

  const stopPolling = () => {
    if (pollRef.current) { clearInterval(pollRef.current); pollRef.current = null }
  }

  const pollLog = async (pid) => {
    if (!pid) return
    try {
      const data = await activitiesApi.jobLog(pid)
      const text = data?.content || ''
      if (text) {
        const suffix = data.running ? '' : `\n\n[process exited with code ${data.exit_code}]`
        setOut(`${text}${suffix}`)
      } else if (!data.running) {
        setOut((prev) => `${prev}\n\n[process exited with code ${data.exit_code}; log is empty]`)
      }
      if (!data.running) {
        stopPolling()
        setJobId(null)
      }
    } catch {}
  }

  const run = async () => {
    setRunning(true)
    setOut('')
    try {
      const payload = {
        activity,
        token_name: meta.tokens ? tokenName || null : null,
        flags: {
          ...flags,
          ...(saveToken && meta.tokens ? { save: true, name: flags.name || `session_${Date.now()}` } : {})
        }
      }

      if (isInteractive) {
        const data = await activitiesApi.interactive(payload)
        setJobId(data.pid || data.job_id || null)
        setOut(
          `[interactive] ${INTERACTIVE_LABELS[activity] || 'running'}…\n` +
          `job_id: ${data.job_id}\npid: ${data.pid}\n` +
          (data.log ? `log: ${data.log}\n` : '') +
          `\nTip: ${activity} runs in the background. Click "Refresh Output" to see stdout/stderr.`
        )
        toast.info(`Started ${activity} as job ${data.job_id}`)
        if (data.pid) {
          pollRef.current = setInterval(() => pollLog(data.pid), 2000)
        }
      } else {
        const res = await activitiesApi.run(payload)
        if (res?.ok === false) {
          setOut(
            `[activity returned non-zero]\n` +
            `exit_code: ${res.exit_code}\n` +
            `test_mode: ${res.test_mode}\n\n` +
            `--- stderr ---\n${res.stderr || '(empty)'}\n` +
            `--- stdout ---\n${res.stdout || '(empty)'}`
          )
          toast.error(`Activity ${activity} exited with code ${res.exit_code}`)
        } else {
          setOut(res?.stdout || res?.stderr || JSON.stringify(res, null, 2))
          toast.success(`Activity ${activity} finished`)
        }
      }
    } catch (e) {
      const status = e?.response?.status
      const body = e?.response?.data
      let detail = body?.stderr || body?.detail || body?.summary || e?.message || 'unknown error'
      if (e?.code === 'ECONNABORTED' || /timeout/i.test(e?.message || '')) {
        detail = `request timed out after ${e?.config?.timeout || 30000}ms — ${activity} ${isInteractive ? 'launched as a background job but the response stalled' : 'is taking longer than the frontend timeout'}`
      }
      setOut(
        `[error from backend]  HTTP ${status || '???'}\n${detail}\n\n` +
        `request:\n  activity: ${activity}\n  flags: ${JSON.stringify(flags, null, 2)}\n  token: ${tokenName || '—'}\n` +
        (testMode ? `\nNOTE: backend is in TEST_MODE (AzureRedOps.py not found). The mock response should not have failed.\n` : '') +
        `\nhint: install missing python modules with:\n  .venv\\Scripts\\python.exe -m pip install pyjwt msal requests cryptography`
      )
      toast.error(`Activity ${activity} failed`)
    } finally {
      setRunning(false)
    }
  }

  const kill = async () => {
    if (!jobId) return
    try {
      await activitiesApi.kill(jobId)
      stopPolling()
      setOut((prev) => prev + `\n\n[killed job ${jobId}]`)
      toast.info(`Killed job ${jobId}`)
      setJobId(null)
    } catch (e) {
      toast.error(`Failed to kill: ${e?.message || 'unknown'}`)
    }
  }

  const dropdownItems = backendActivities.length
    ? backendActivities
    : Object.keys(ACTIVITY_META)

  return (
    <Modal open={open} onClose={onClose} title="Run CLI Activity" size="xl"
      footer={<>
        <button onClick={onClose} className="px-4 py-2 rounded-lg bg-white/5 hover:bg-white/10 text-sm text-gray-300">Close</button>
        {jobId && (
          <button onClick={kill}
            className="px-4 py-2 rounded-lg bg-danger/15 hover:bg-danger/25 text-danger text-sm flex items-center gap-2">
            <Square size={14} />Kill Job
          </button>
        )}
        <button onClick={run} disabled={running}
          className="px-4 py-2 rounded-lg bg-accent hover:brightness-110 text-sm text-white shadow-glow flex items-center gap-2 disabled:opacity-50">
          <Play size={14} />{running ? 'Running…' : (isInteractive ? 'Start Job' : 'Run Activity')}
        </button>
      </>}>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        <div>
          <label className="block text-xs text-gray-400 mb-1">
            Activity (-a) — {dropdownItems.length} available
            {testMode && <span className="ml-2 text-warning">(test mode)</span>}
          </label>
          <select
            value={activity}
            onChange={(e) => { setActivity(e.target.value); setFlags({}); stopPolling(); setJobId(null) }}
            className="dark-select"
          >
            {dropdownItems.map((id) => (
              <option key={id} value={id}>
                {ACTIVITY_META[id]?.label || id}{ACTIVITY_META[id]?.interactive ? '  • interactive' : ''}
              </option>
            ))}
          </select>
        </div>
        {meta.tokens && (
          <div>
            <label className="block text-xs text-gray-400 mb-1">Token Name (-l)</label>
            <input value={tokenName} onChange={(e) => setTokenName(e.target.value)} placeholder="e.g. mytoken" />
          </div>
        )}
      </div>

      {isInteractive && (
        <div className="mb-4 p-3 rounded-lg bg-accent/10 border border-accent/30 text-xs text-gray-300">
          <strong className="text-accent">Interactive activity.</strong> This runs as a background job (Popen),
          not a blocking subprocess. Output is polled from the log file every 2s. Use the Kill Job button to terminate.
        </div>
      )}

      {(meta.flags || []).length > 0 && (
        <>
          <div className="flex items-center justify-between mb-2">
            <div className="text-xs text-gray-400 uppercase tracking-wider">Flags</div>
            {meta.tokens && (
              <label className="flex items-center gap-2 text-xs text-gray-400 cursor-pointer">
                <input
                  type="checkbox"
                  checked={saveToken}
                  onChange={(e) => setSaveToken(e.target.checked)}
                  style={{ accentColor: '#3498db' }}
                />
                Save token after run (-s)
              </label>
            )}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-3 gap-3 mb-4">
            {meta.flags.map((f) => (
              <div key={f}>
                <label className="block text-xs text-gray-400 mb-1">--{f}</label>
                <input
                  value={flags[f] || ''}
                  onChange={(e) => setFlags({ ...flags, [f]: e.target.value })}
                  placeholder={`value for ${f}`}
                />
              </div>
            ))}
          </div>
        </>
      )}

      <div className="text-xs text-gray-400 uppercase tracking-wider mb-2 flex items-center gap-2">
        <Terminal size={14} />Output
        {jobId && <span className="text-accent ml-2">• polling job {jobId}</span>}
      </div>
      <pre className="bg-black/40 p-4 rounded-lg text-xs text-green-300 overflow-auto max-h-72 font-mono whitespace-pre-wrap">
        {out || 'Output will appear here after running.'}
      </pre>
    </Modal>
  )
}
