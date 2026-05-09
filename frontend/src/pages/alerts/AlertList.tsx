import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { Table, Select, Button, Space, Tag, Tooltip, Modal, Input } from 'antd'
import { ReloadOutlined } from '@ant-design/icons'
import type { ColumnsType } from 'antd/es/table'
import { api } from '../../api/client'
import { SeverityBadge } from '../../components/common/SeverityBadge'
import type { AlertItem, PaginatedResponse, Severity } from '../../types'

const STATUS_COLOR: Record<string, string> = {
  new: 'blue', reviewing: 'processing', escalated: 'orange', dismissed: 'default',
}

export function AlertList() {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [searchParams, setSearchParams] = useSearchParams()
  const [page, setPage] = useState(1)
  const [dismissModal, setDismissModal] = useState<{ id: string } | null>(null)
  const [dismissReason, setDismissReason] = useState('')

  const filters = {
    status: searchParams.get('status') || undefined,
    severity: searchParams.get('severity') || undefined,
    department: searchParams.get('department') || undefined,
    page, page_size: 25,
  }

  const { data, isLoading, refetch } = useQuery<PaginatedResponse<AlertItem>>({
    queryKey: ['alerts', filters],
    queryFn: () => api.get('/alerts', { params: filters }),
  })

  const dismissMutation = useMutation({
    mutationFn: ({ id, reason }: { id: string; reason: string }) =>
      api.patch(`/alerts/${id}/status`, { status: 'dismissed', dismiss_reason: reason }),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['alerts'] }); setDismissModal(null) },
  })

  const set = (key: string, val: string | undefined) => {
    setSearchParams(p => { val ? p.set(key, val) : p.delete(key); return p })
    setPage(1)
  }

  const columns: ColumnsType<AlertItem> = [
    { title: 'Sev', dataIndex: 'severity', width: 90,
      render: (v: Severity) => <SeverityBadge severity={v} /> },
    { title: 'Score', dataIndex: 'risk_score', width: 65, align: 'center' as const,
      render: (v: number) => <span style={{ fontWeight: 700, color: v >= 60 ? '#ea580c' : v >= 40 ? '#ca8a04' : '#888' }}>{v}</span>,
      sorter: (a, b) => b.risk_score - a.risk_score },
    { title: 'Alert', dataIndex: 'title',
      render: (t, r) => (
        <div>
          <div style={{ fontWeight: 500 }}>{t}</div>
          <div style={{ fontSize: 11, color: '#888' }}>{r.alert_type}</div>
        </div>
      ) },
    { title: 'User', key: 'user',
      render: (_, r) => (
        <div>
          <a style={{ fontWeight: 500 }} onClick={e => { e.stopPropagation(); navigate(`/users/${r.user_email}`) }}>
            {r.user_display_name}
          </a>
          <div style={{ fontSize: 11, color: '#888' }}>{r.department}</div>
        </div>
      ) },
    { title: 'Status', dataIndex: 'status', width: 105,
      render: (v: string) => <Tag color={STATUS_COLOR[v] || 'default'}>{v.toUpperCase()}</Tag> },
    { title: 'Time', dataIndex: 'alert_timestamp', width: 145,
      render: (v: string) => <Tooltip title={v}>{new Date(v).toLocaleString('en-SG', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' })}</Tooltip>,
      sorter: (a, b) => new Date(b.alert_timestamp).getTime() - new Date(a.alert_timestamp).getTime(),
      defaultSortOrder: 'ascend' as const },
    { title: 'Case', dataIndex: 'case_id', width: 75,
      render: (v: string | null) => v
        ? <Button size="small" type="link" onClick={e => { e.stopPropagation(); navigate(`/cases/${v}`) }}>View</Button>
        : <Tag>None</Tag> },
    { title: 'Actions', key: 'actions', width: 100,
      render: (_, r) => r.status === 'new' || r.status === 'reviewing' ? (
        <Button size="small" danger onClick={e => { e.stopPropagation(); setDismissModal({ id: r.id }) }}>
          Dismiss
        </Button>
      ) : null },
  ]

  return (
    <div>
      <Space wrap style={{ marginBottom: 16 }}>
        {[
          { key: 'status', placeholder: 'Status', opts: ['new','reviewing','escalated','dismissed'], w: 130 },
          { key: 'severity', placeholder: 'Severity', opts: ['critical','high','medium','low'], w: 120 },
          { key: 'department', placeholder: 'Department', opts: ['Finance','Sales','IT','HR'], w: 150 },
        ].map(f => (
          <Select key={f.key} placeholder={f.placeholder} allowClear style={{ width: f.w }}
            value={searchParams.get(f.key) || undefined}
            onChange={v => set(f.key, v)}
            options={f.opts.map(v => ({ value: v, label: v }))} />
        ))}
        <Button icon={<ReloadOutlined />} onClick={() => refetch()}>Refresh</Button>
      </Space>

      <Table
        loading={isLoading}
        dataSource={(data as any)?.items}
        rowKey="id"
        columns={columns}
        scroll={{ x: 900 }}
        pagination={{ total: (data as any)?.total, current: page, pageSize: 25, onChange: setPage,
          showTotal: t => `${t} alerts` }}
        onRow={r => ({ onClick: () => navigate(`/alerts/${r.id}`), style: { cursor: 'pointer' } })}
      />

      <Modal
        open={!!dismissModal}
        title="Dismiss Alert"
        onOk={() => dismissMutation.mutate({ id: dismissModal!.id, reason: dismissReason })}
        onCancel={() => setDismissModal(null)}
        confirmLoading={dismissMutation.isPending}
      >
        <Input.TextArea
          rows={3}
          placeholder="Reason for dismissal (false positive, expected behaviour, etc.)"
          value={dismissReason}
          onChange={e => setDismissReason(e.target.value)}
        />
      </Modal>
    </div>
  )
}
