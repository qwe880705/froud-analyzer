import { useQuery } from '@tanstack/react-query'
import { Card, Col, Row, Statistic, Table, Tag, Typography, Spin, List, Avatar, Space } from 'antd'
import { AlertOutlined, FolderOpenOutlined, UserOutlined, RiseOutlined } from '@ant-design/icons'
import { useNavigate } from 'react-router-dom'
import { api } from '../api/client'
import { SeverityBadge } from '../components/common/SeverityBadge'
import type { Severity } from '../types'

export function Dashboard() {
  const navigate = useNavigate()
  const { data, isLoading } = useQuery({
    queryKey: ['dashboard'],
    queryFn: () => api.get('/risk/dashboard'),
    refetchInterval: 60_000,
  })

  if (isLoading || !data) return <Spin size="large" style={{ display: 'block', marginTop: 80, textAlign: 'center' }} />

  const s = data as any

  return (
    <div>
      <Typography.Title level={4} style={{ marginBottom: 20 }}>Security Overview · APAC</Typography.Title>

      <Row gutter={16} style={{ marginBottom: 20 }}>
        {[
          { title: 'Open Alerts',    value: s.open_alerts,       icon: <AlertOutlined />,      color: '#1677ff', path: '/alerts?status=new' },
          { title: 'Critical Cases', value: s.critical_cases,    icon: <FolderOpenOutlined />, color: '#dc2626', path: '/cases?severity=critical' },
          { title: 'High Cases',     value: s.high_cases,        icon: <FolderOpenOutlined />, color: '#ea580c', path: '/cases?severity=high' },
          { title: 'Alerts Today',   value: s.alerts_today,      icon: <RiseOutlined />,       color: '#ca8a04', path: '/alerts' },
          { title: 'Active Users',   value: s.total_users_active,icon: <UserOutlined />,       color: '#16a34a', path: '/users' },
          { title: 'Avg Risk Score', value: s.avg_risk_score,    icon: null,                   color: s.avg_risk_score >= 60 ? '#ea580c' : '#16a34a', path: '/users' },
        ].map((k) => (
          <Col span={4} key={k.title}>
            <Card hoverable onClick={() => navigate(k.path)} bodyStyle={{ padding: '16px' }}>
              <Statistic
                title={<span style={{ fontSize: 12 }}>{k.title}</span>}
                value={k.value}
                precision={k.title === 'Avg Risk Score' ? 1 : 0}
                suffix={k.title === 'Avg Risk Score' ? '/100' : undefined}
                prefix={k.icon ? <span style={{ color: k.color }}>{k.icon}</span> : undefined}
                valueStyle={{ color: k.color, fontSize: 26 }}
              />
            </Card>
          </Col>
        ))}
      </Row>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={9}>
          <Card title="Top Risk Users" extra={<a onClick={() => navigate('/users')}>All</a>} style={{ height: 300 }}>
            <List
              size="small"
              dataSource={s.top_risky_users || []}
              renderItem={(u: any) => (
                <List.Item
                  style={{ cursor: 'pointer', padding: '6px 0' }}
                  onClick={() => navigate(`/users/${u.user_id}`)}
                  actions={[<SeverityBadge severity={u.severity as Severity} />, <Tag>{u.score}</Tag>]}
                >
                  <List.Item.Meta
                    avatar={<Avatar size="small" style={{ background: '#1677ff' }}>{u.display_name?.[0]}</Avatar>}
                    title={<span style={{ fontSize: 13 }}>{u.display_name}</span>}
                    description={<span style={{ fontSize: 11, color: '#888' }}>{u.email}</span>}
                  />
                </List.Item>
              )}
            />
          </Card>
        </Col>
        <Col span={15}>
          <Card title="Recent Alerts" extra={<a onClick={() => navigate('/alerts')}>All</a>} style={{ height: 300 }}>
            <Table
              size="small" pagination={false} scroll={{ y: 210 }}
              dataSource={s.recent_alerts || []} rowKey="id"
              onRow={(r: any) => ({ onClick: () => navigate(`/alerts/${r.id}`) })}
              columns={[
                { title: 'Title', dataIndex: 'title', ellipsis: true },
                { title: 'Severity', dataIndex: 'severity', width: 90,
                  render: (v: Severity) => <SeverityBadge severity={v} /> },
                { title: 'Detected', dataIndex: 'detected_at', width: 150,
                  render: (v: string) => new Date(v).toLocaleString('en-SG', { month: 'short', day: '2-digit', hour: '2-digit', minute: '2-digit' }) },
              ]}
            />
          </Card>
        </Col>
      </Row>

      <Row gutter={16}>
        <Col span={12}>
          <Card title="Alerts by Severity">
            <Row gutter={8}>
              {(['critical','high','medium','low'] as Severity[]).map((sev) => (
                <Col span={6} key={sev}>
                  <Card size="small" hoverable onClick={() => navigate(`/alerts?severity=${sev}`)} style={{ textAlign: 'center' }}>
                    <SeverityBadge severity={sev} />
                    <div style={{ fontSize: 28, fontWeight: 700, marginTop: 4 }}>{s.alerts_by_severity?.[sev] ?? 0}</div>
                  </Card>
                </Col>
              ))}
            </Row>
          </Card>
        </Col>
        <Col span={12}>
          <Card title="Cases by Status">
            <Space wrap>
              {Object.entries(s.cases_by_status || {}).map(([st, cnt]: any) => (
                <Card key={st} size="small" hoverable onClick={() => navigate(`/cases?status=${st}`)} style={{ textAlign: 'center', minWidth: 100 }}>
                  <Tag>{st.replace(/_/g, ' ')}</Tag>
                  <div style={{ fontSize: 24, fontWeight: 700, marginTop: 4 }}>{cnt}</div>
                </Card>
              ))}
            </Space>
          </Card>
        </Col>
      </Row>
    </div>
  )
}
