import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Table, Select, Button, Space, Tag, Badge } from 'antd'
import { ReloadOutlined, PlusOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { api } from '../../api/client'
import { SeverityBadge } from '../../components/common/SeverityBadge'
import type { CaseItem, PaginatedResponse, Severity } from '../../types'

const STATUS_COLOR: Record<string, string> = {
  open: 'blue', investigating: 'processing', pending_review: 'warning',
  escalated: 'error', closed_confirmed: 'red', closed_cleared: 'success', closed_inconclusive: 'default',
}

export function CaseList() {
  const navigate = useNavigate()
  const [searchParams, setSearchParams] = useSearchParams()
  const [page, setPage] = useState(1)

  const filters = {
    status: searchParams.get('status') || undefined,
    severity: searchParams.get('severity') || undefined,
    department: searchParams.get('department') || undefined,
    page, page_size: 20,
  }

  const { data, isLoading, refetch } = useQuery<PaginatedResponse<CaseItem>>({
    queryKey: ['cases', filters],
    queryFn: () => api.get('/cases', { params: filters }),
  })

  const set = (key: string, val: string | undefined) => {
    setSearchParams(p => { val ? p.set(key, val) : p.delete(key); return p })
    setPage(1)
  }

  const columns: ColumnsType<CaseItem> = [
    { title: 'Case #', dataIndex: 'case_number', width: 140,
      render: (v: string) => <span style={{ fontFamily: 'monospace', fontSize: 12 }}>{v}</span> },
    { title: 'Severity', dataIndex: 'severity', width: 90,
      render: (v: Severity) => <SeverityBadge severity={v} /> },
    { title: 'Score', dataIndex: 'risk_score', width: 65, align: 'center' as const,
      render: (v: number) => <span style={{ fontWeight: 700 }}>{v.toFixed(0)}</span>,
      sorter: (a, b) => b.risk_score - a.risk_score },
    { title: 'Title', dataIndex: 'title', ellipsis: true },
    { title: 'Subject', key: 'subject',
      render: (_, r) => (
        <div>
          <a onClick={e => { e.stopPropagation(); navigate(`/users/${r.subject_user_email}`) }}>
            {r.subject_user_name}
          </a>
          <div style={{ fontSize: 11, color: '#888' }}>{r.department}</div>
        </div>
      ) },
    { title: 'Status', dataIndex: 'status', width: 150,
      render: (v: string) => <Tag color={STATUS_COLOR[v] || 'default'}>{v.replace(/_/g, ' ')}</Tag> },
    { title: 'Events', dataIndex: 'event_count', width: 75, align: 'center' as const,
      render: (v: number) => <Badge count={v} showZero color="#1677ff" /> },
    { title: 'Assigned', dataIndex: 'assigned_to', width: 160, ellipsis: true,
      render: (v: string | null) => v || <Tag color="default">Unassigned</Tag> },
    { title: 'Created', dataIndex: 'created_at', width: 110,
      render: (v: string) => new Date(v).toLocaleDateString('en-SG'),
      sorter: (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
      defaultSortOrder: 'ascend' as const },
  ]

  return (
    <div>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select placeholder="Status" allowClear style={{ width: 150 }}
          value={searchParams.get('status') || undefined}
          onChange={v => set('status', v)}
          options={['open','investigating','pending_review','escalated','closed_confirmed','closed_cleared'].map(v => ({ value: v, label: v.replace(/_/g,' ') }))} />
        <Select placeholder="Severity" allowClear style={{ width: 120 }}
          value={searchParams.get('severity') || undefined}
          onChange={v => set('severity', v)}
          options={['critical','high','medium','low'].map(v => ({ value: v, label: v }))} />
        <Button icon={<ReloadOutlined />} onClick={() => refetch()}>Refresh</Button>
      </Space>

      <Table
        loading={isLoading}
        dataSource={(data as any)?.items}
        rowKey="id"
        columns={columns}
        scroll={{ x: 1000 }}
        pagination={{ total: (data as any)?.total, current: page, pageSize: 20, onChange: setPage,
          showTotal: t => `${t} cases` }}
        onRow={r => ({ onClick: () => navigate(`/cases/${r.id}`), style: { cursor: 'pointer' } })}
      />
    </div>
  )
}
