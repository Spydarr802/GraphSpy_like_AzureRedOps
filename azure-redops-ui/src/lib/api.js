import axios from 'axios'

const api = axios.create({ baseURL: 'http://localhost:8000', timeout: 30000 })

api.interceptors.response.use(
  (r) => r,
  (err) => {
    if (!err.response) {
      console.warn('AzureRedOps API: backend unreachable at', api.defaults.baseURL)
    }
    return Promise.reject(err)
  }
)

export const activitiesApi = {
  list: () => api.get('/activities').then((r) => r.data),
  run: (data) => api.post('/activities/run', data).then((r) => r.data),
  interactive: (data) => api.post('/activities/interactive', data).then((r) => r.data),
  jobs: () => api.get('/activities/jobs').then((r) => r.data),
  job: (pid) => api.get(`/activities/job/${encodeURIComponent(pid)}`).then((r) => r.data),
  jobLog: (pid) => api.get(`/activities/job/${encodeURIComponent(pid)}/log`).then((r) => r.data),
  kill: (pid) => api.delete(`/activities/job/${encodeURIComponent(pid)}`).then((r) => r.data)
}

export const tokensApi = {
  list: () => api.get('/tokens/').then((r) => r.data.tokens || []),
  save: (d) => api.post('/tokens/save', d).then((r) => r.data),
  remove: (n) => api.delete(`/tokens/${encodeURIComponent(n)}`).then((r) => r.data),
  raw: (n) => api.get(`/tokens/${encodeURIComponent(n)}/raw`).then((r) => r.data),
  access: (n) => api.get(`/tokens/${encodeURIComponent(n)}/access`).then((r) => r.data),
  decode: (n) => api.get(`/tokens/${encodeURIComponent(n)}/decode`).then((r) => r.data),
  decodeRaw: (token) => api.post('/tokens/decode-raw', { token }).then((r) => r.data),
  refresh: (name) => api.post(`/tokens/${encodeURIComponent(name)}/refresh`, { name }).then((r) => r.data)
}

export const authApi = {
  ropc: (p) => api.post('/auth/ropc', null, { params: p }).then((r) => r.data),
  deviceStart: (tid) =>
    api.post('/auth/device/start', null, { params: tid ? { tid } : {} }).then((r) => r.data),
  deviceCapture: (c) => api.post('/auth/device/capture', null, { params: { user_code: c } }).then((r) => r.data)
}

export const sessionsApi = {
  list: () => api.get('/sessions/').then((r) => r.data.sessions || []),
  detail: (id) => api.get(`/sessions/${encodeURIComponent(id)}`).then((r) => r.data),
  cookies: (id) => api.get(`/sessions/${encodeURIComponent(id)}/cookies`).then((r) => r.data),
  mailToken: (id) => api.get(`/sessions/${encodeURIComponent(id)}/mail-token`).then((r) => r.data),
  webmail: (id, folder = 'Inbox', limit = 25) =>
    api.get(`/sessions/${encodeURIComponent(id)}/webmail`, { params: { folder, limit } }).then((r) => r.data),
  remove: (id) => api.delete(`/sessions/${encodeURIComponent(id)}`).then((r) => r.data)
}

export const oauthApi = {
  start: (data) => api.post('/oauth/device/start', data).then((r) => r.data),
  list: () => api.get('/oauth/device').then((r) => r.data),
  get: (deviceCode) => api.get(`/oauth/device/${encodeURIComponent(deviceCode)}`).then((r) => r.data),
  submit: (data) => api.post('/oauth/device/submit', data).then((r) => r.data),
  callback: (data) => api.post('/oauth/callback', data).then((r) => r.data)
}

export const phishApi = {
  apps: (source = 'apps.json') => api.get('/phish/apps', { params: { source } }).then((r) => r.data),
  templates: () => api.get('/phish/templates').then((r) => r.data.apps || []),
  generateLure: (data) => api.post('/phish/lure/generate', data).then((r) => r.data),
  serverStatus: () => api.get('/phish/server/status').then((r) => r.data),
  serverStart: (data = {}) => api.post('/phish/server/start', data).then((r) => r.data),
  serverStop: () => api.post('/phish/server/stop').then((r) => r.data),
  reloadCerts: () => api.post('/phish/server/reload-certs').then((r) => r.data)
}

export const sprayApi = {
  list: () => api.get('/spray/list').then((r) => r.data),
  run: (data) => api.post('/spray/', data).then((r) => r.data),
  runFile: (timeout = 300) => api.post('/spray/file', null, { params: { timeout } }).then((r) => r.data)
}

export const mailboxApi = {
  add: (data) => api.post('/mailbox/sessions', data).then((r) => r.data),
  sessions: () => api.get('/mailbox/sessions').then((r) => r.data).then((d) => d.sessions || []),
  remove: (name) => api.delete(`/mailbox/sessions/${encodeURIComponent(name)}`).then((r) => r.data),
  folders: (name) => api.get(`/mailbox/proxy/${encodeURIComponent(name)}/folders`).then((r) => r.data),
  messages: (name, folder, limit = 25, offset = 0) =>
    api.get(`/mailbox/proxy/${encodeURIComponent(name)}/messages`, { params: { folder, limit, offset } }).then((r) => r.data),
  message: (name, msgId, folder = 'INBOX') =>
    api.get(`/mailbox/proxy/${encodeURIComponent(name)}/message/${encodeURIComponent(msgId)}`, { params: { folder } }).then((r) => r.data),
  delete: (name, msgId, folder = 'INBOX') =>
    api.post(`/mailbox/proxy/${encodeURIComponent(name)}/delete/${encodeURIComponent(msgId)}`, null, { params: { folder } }).then((r) => r.data),
  flag: (name, msgId, flag, folder = 'INBOX', value = true) =>
    api.post(`/mailbox/proxy/${encodeURIComponent(name)}/flag/${encodeURIComponent(msgId)}/${encodeURIComponent(flag)}`, null, { params: { folder, value } }).then((r) => r.data),
  forward: (name, data) => api.post(`/mailbox/proxy/${encodeURIComponent(name)}/forward`, data).then((r) => r.data)
}

export default api
