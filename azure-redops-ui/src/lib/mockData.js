// Mock fixtures used only by SettingsPage (phishing template gallery) and
// Sender page (placeholder templates until /phish/templates endpoint wired).
// Removed: MOCK_TOKENS, MOCK_COUNTRY, MOCK_LEADS — those came from hardcoded
// lists and broke Dashboard / Leads. Everything that used them now hits
// sessionsApi.list() and tokensApi.list() instead.

export const MOCK_LURES = [
  { id: 1, name: 'OneDrive', description: 'Microsoft OneDrive shared document', icon: 'Cloud', color: '#3498db' },
  { id: 2, name: 'SharePoint', description: 'SharePoint Online document portal', icon: 'FileText', color: '#9b59b6' },
  { id: 3, name: 'Excel Online', description: 'Excel spreadsheet invitation', icon: 'BarChart', color: '#2ecc71' },
  { id: 4, name: 'Microsoft 365', description: 'Office 365 sign-in', icon: 'Briefcase', color: '#e74c3c' },
  { id: 5, name: 'Adobe Sign', description: 'Adobe document signing', icon: 'Pen', color: '#e67e22' },
  { id: 6, name: 'DocuSign', description: 'DocuSign secure envelope', icon: 'FileSignature', color: '#f1c40f' },
  { id: 7, name: 'Google Drive', description: 'Google Drive shared file', icon: 'Folder', color: '#1abc9c' },
  { id: 8, name: 'Custom', description: 'Build your own template', icon: 'Plus', color: '#95a5a6' }
]