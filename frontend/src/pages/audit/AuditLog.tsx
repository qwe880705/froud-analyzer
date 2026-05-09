import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Table, Tag, Typography, Button, Space, Alert } from 'antd'
import { CheckCircleOutlined, CloseCircleOutlined } from '@ant-design/icons'
import { api } from '../../api/client'

export function AuditLog() {
  const [page, setPage] = useState(1)

  const { data } = useQuery<any>({
    queryKey: ['audit', page],
    queryFn: () => api.get('/audit/logs', { params: { page, page_size: 50 } }),
  })

  const { data: verify } = useQuery<any>({
    queryKey: ['audit-verify'],
    queryFn: () => api.get('/audit/verify'),
  })

  return (
    <div>
      <Typography.Title level={4} style={{ marginBottom: 16 }}>Audit Log</Typography.Title>

      {verify && (
        <Alert
          style={{ marginBottom: 16 }}
          type={verify.chain_intact ? 'success' : 'error'}
          icon={verify.chain_intact ? <CheckCircleOutlined /> : <CloseCircleOutlined />}
          showIcon
          message={verify.chain_intact
            ? `Chain integrity verified · ${verify.total_entries} entries`
            : `⚠ Chain integrity BROKEN — ${verify.broken_entries?.length} anomalies detected`}
        />
      )}

      <Table
        size="small"
        dataSource={(data as any)?.items ?? []}
        rowKey="id"
        pagination={{ total: (data as any)?.total, current: page, pageSize: 50, onChange: setPage }}
        columns={[
          { title: 'Time', dataIndex: 'occurred_at', width: 160,
            render: (v: string) => new Date(v).toLocaleString('en-SG') },
          { title: 'Actor', dataIndex: 'actor', width: 180, ellipsis: true },
          { title: 'Action', dataIndex: 'action', width: 200,
            render: (v: string) => <Tag style={{ fontFamily: 'monospace', fontSize: 11 }}>{v}</Tag> },
          { title: 'Resource', key: 'resource',
            render: (_: any, r: any) => <span>{r.resource_type}{r.resource_id ? ` · ${r.resource_id.slice(0,8)}…` : ''}</span> },
          { title: 'Details', dataIndex: 'details', ellipsis: true,
            render: (v: string) => v ? <Typography.Text type="secondary" style={{ fontSize: 11 }}>{v}</Typography.Text> : null },
        ]}
      />
    </div>
  )
}
