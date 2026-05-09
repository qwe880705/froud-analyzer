import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Table, Select, Space, Tag, Button } from 'antd'
import { WarningOutlined } from '@ant-design/icons'
import { api } from '../../api/client'
import type { User, PaginatedResponse } from '../../types'

export function UserList() {
  const navigate = useNavigate()
  const [page, setPage] = useState(1)
  const [dept, setDept] = useState<string>()
  const [status, setStatus] = useState<string>()

  const { data, isLoading } = useQuery<PaginatedResponse<User>>({
    queryKey: ['users', page, dept, status],
    queryFn: () => api.get('/users', { params: { page, page_size: 25, department: dept, employment_status: status } }),
  })

  return (
    <div>
      <Space wrap style={{ marginBottom: 16 }}>
        <Select placeholder="Department" allowClear style={{ width: 150 }}
          onChange={setDept}
          options={['Finance','Sales','IT','HR'].map(v => ({ value: v, label: v }))} />
        <Select placeholder="Status" allowClear style={{ width: 140 }}
          onChange={setStatus}
          options={['active','on_leave','terminated','resigned'].map(v => ({ value: v, label: v }))} />
      </Space>
      <Table
        loading={isLoading}
        dataSource={(data as any)?.items}
        rowKey="id"
        pagination={{ total: (data as any)?.total, current: page, pageSize: 25, onChange: setPage }}
        onRow={r => ({ onClick: () => navigate(`/users/${r.id}`), style: { cursor: 'pointer' } })}
        columns={[
          { title: 'Name', dataIndex: 'display_name',
            render: (v, r) => (
              <Space>
                {v}
                {(r.is_pending_resign || r.is_on_pip) && (
                  <WarningOutlined style={{ color: '#ea580c' }} />
                )}
              </Space>
            ) },
          { title: 'Email', dataIndex: 'email' },
          { title: 'Department', dataIndex: 'department', width: 120 },
          { title: 'Location', dataIndex: 'location', width: 120 },
          { title: 'Status', dataIndex: 'employment_status', width: 110,
            render: (v: string) => <Tag color={v === 'active' ? 'green' : 'red'}>{v}</Tag> },
          { title: 'Risk Flags', key: 'flags', width: 150,
            render: (_, r) => (
              <Space wrap>
                {r.is_pending_resign && <Tag color="red" style={{ fontSize: 10 }}>Resign</Tag>}
                {r.is_on_pip && <Tag color="orange" style={{ fontSize: 10 }}>PIP</Tag>}
                {r.is_pending_transfer && <Tag color="blue" style={{ fontSize: 10 }}>Transfer</Tag>}
              </Space>
            ) },
          { title: 'Profile', key: 'action', width: 80,
            render: (_, r) => <Button size="small" type="link" onClick={e => { e.stopPropagation(); navigate(`/users/${r.id}`) }}>View</Button> },
        ]}
      />
    </div>
  )
}
