import { Routes, Route, Navigate } from 'react-router-dom'
import { ToastProvider } from './components/Toast'
import Login from './pages/Login'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Leads from './pages/Leads'
import Sender from './pages/Sender'
import SettingsPage from './pages/Settings'
import Mailbox from './pages/Mailbox'
import AdvancedTools from './pages/AdvancedTools'

function RequireAuth({ children }) {
  const tok = (typeof window !== 'undefined') ? localStorage.getItem('azr_token') : null
  return tok ? children : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <ToastProvider>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/admin"
          element={
            <RequireAuth>
              <Layout />
            </RequireAuth>
          }
        >
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<Dashboard />} />
          <Route path="leads" element={<Leads />} />
          <Route path="sender" element={<Sender />} />
          <Route path="settings" element={<SettingsPage />} />
          <Route path="mailbox/:sessionId" element={<Mailbox />} />
          <Route path="advanced" element={<AdvancedTools />} />
        </Route>
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    </ToastProvider>
  )
}