import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { AppLayout } from './components/layout/AppLayout'
import { Dashboard } from './pages/Dashboard'
import { AlertList } from './pages/alerts/AlertList'
import { AlertDetail } from './pages/alerts/AlertDetail'
import { CaseList } from './pages/cases/CaseList'
import { CaseDetail } from './pages/cases/CaseDetail'
import { UserList } from './pages/users/UserList'
import { UserRiskProfile } from './pages/users/UserRiskProfile'
import { ReportGenerator } from './pages/reports/ReportGenerator'
import { DataImport } from './pages/ingest/DataImport'
import { AuditLog } from './pages/audit/AuditLog'

const qc = new QueryClient({
  defaultOptions: { queries: { staleTime: 30_000, retry: 1 } },
})

export default function App() {
  return (
    <QueryClientProvider client={qc}>
      <BrowserRouter>
        <Routes>
          <Route path="/" element={<AppLayout />}>
            <Route index element={<Dashboard />} />
            <Route path="alerts" element={<AlertList />} />
            <Route path="alerts/:id" element={<AlertDetail />} />
            <Route path="cases" element={<CaseList />} />
            <Route path="cases/:id" element={<CaseDetail />} />
            <Route path="cases/:id/report" element={<ReportGenerator />} />
            <Route path="users" element={<UserList />} />
            <Route path="users/:id" element={<UserRiskProfile />} />
            <Route path="import" element={<DataImport />} />
            <Route path="audit" element={<AuditLog />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
