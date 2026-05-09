import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, Col, Row, Descriptions, Progress, Button, Table, Tag, Typography, Space, Alert } from 'antd'
import { ThunderboltOutlined, ArrowLeftOutlined } from '@ant-design/icons'
import { api } from '../../api/client'
import { SeverityBadge } from '../../components/common/SeverityBadge'
import type { Severity } from '../../types'

const DIM: Record<string, { label: string; color: string; max: number }> = {
  score_data_exfil:     { label: 'Data Exfiltration',    color: '#dc2626', max: 30 },
  score_access_anomaly: { label: 'Access Anomaly',       color: '#ea580c', max: 25 },
  score_behavior_dev:   { label: 'Behavioral Deviation', color: '#ca8a04', max: 20 },
  score_hr_context:     { label: 'HR Context',           color: '#7c3aed', max: 15 },
  score_temporal:       { label: 'Temporal Pattern',     color: '#1677ff', max: 10 },
}

export function UserRiskProfile() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { data: user } = useQuery({ queryKey: ['user', id], queryFn: () => api.get(`/users/${id}`) })
  const { data: scores } = useQuery<any[]>({ queryKey: ['scores', id], queryFn: () => api.get(`/risk/scores/${id}`) })
  const { data: cases } = useQuery<any>({ queryKey: ['user-cases', id], queryFn: () => api.get(`/users/${id}/cases`) })

  const rescore = useMutation({
    mutationFn: () => api.post(`/risk/score/${id}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['scores', id] }),
  })

  const u = user as any
  const latest = (scores as any[])?.[0]

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} type="text" onClick={() => navigate('/users')} style={{ marginBottom: 12 }}>
        Back to Users
      </Button>

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={8}>
          <Card size="small" title="Employee Profile">
            {u && (
              <>
                {(u.is_pending_resign || u.is_on_pip) && (
                  <Alert type="warning" showIcon style={{ marginBottom: 10 }} message={
                    <Space direction="vertical" size={0}>
                      {u.is_pending_resign && <span>⚠ Pending Resignation — Last day: {u.termination_date}</span>}
                      {u.is_on_pip && <span>⚠ On Performance Improvement Plan</span>}
                    </Space>
                  } />
                )}
                <Descriptions column={1} size="small">
                  <Descriptions.Item label="Name">{u.display_name}</Descriptions.Item>
                  <Descriptions.Item label="Email">{u.email}</Descriptions.Item>
                  <Descriptions.Item label="Dept">{u.department}</Descriptions.Item>
                  <Descriptions.Item label="Title">{u.job_title}</Descriptions.Item>
                  <Descriptions.Item label="Location">{u.location}</Descriptions.Item>
                  <Descriptions.Item label="Status">
                    <Tag color={u.employment_status === 'active' ? 'green' : 'red'}>{u.employment_status}</Tag>
                  </Descriptions.Item>
                  {u.termination_date && (
                    <Descriptions.Item label="Last Day"><Tag color="red">{u.termination_date}</Tag></Descriptions.Item>
                  )}
                </Descriptions>
              </>
            )}
          </Card>
        </Col>

        <Col span={10}>
          <Card size="small" title="Risk Score"
            extra={<Button size="small" icon={<ThunderboltOutlined />} loading={rescore.isPending} onClick={() => rescore.mutate()}>Recalculate</Button>}>
            {latest ? (
              <>
                <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 14 }}>
                  <Progress type="circle" percent={Math.round(latest.total_score)} size={70}
                    strokeColor={latest.total_score >= 80 ? '#dc2626' : latest.total_score >= 60 ? '#ea580c' : latest.total_score >= 40 ? '#ca8a04' : '#16a34a'}
                    format={p => <span style={{ fontSize: 16, fontWeight: 700 }}>{p}</span>} />
                  <div>
                    <SeverityBadge severity={latest.severity as Severity} />
                    <div style={{ fontSize: 11, color: '#888', marginTop: 4 }}>{latest.event_count} events</div>
                    <div style={{ fontSize: 11, color: '#888' }}>{new Date(latest.calculated_at).toLocaleString('en-SG')}</div>
                  </div>
                </div>
                <Space direction="vertical" style={{ width: '100%' }}>
                  {Object.entries(DIM).map(([key, cfg]) => {
                    const score = latest[key] as number
                    return (
                      <div key={key}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 12 }}>
                          <span>{cfg.label}</span>
                          <span style={{ color: cfg.color }}>{score.toFixed(1)} / {cfg.max}</span>
                        </div>
                        <Progress percent={(score / cfg.max) * 100} showInfo={false}
                          strokeColor={cfg.color} size="small" style={{ margin: '2px 0 4px' }} />
                      </div>
                    )
                  })}
                </Space>
              </>
            ) : (
              <Typography.Text type="secondary">No score calculated. Click Recalculate.</Typography.Text>
            )}
          </Card>
        </Col>

        <Col span={6}>
          <Card size="small" title="Score History">
            <Space direction="vertical" style={{ width: '100%' }}>
              {(scores as any[] || []).slice(0, 6).map((s: any) => (
                <div key={s.id} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
                  <span style={{ fontSize: 11, color: '#888', width: 85 }}>
                    {new Date(s.calculated_at).toLocaleDateString('en-SG')}
                  </span>
                  <Progress percent={s.total_score} showInfo={false}
                    strokeColor={s.total_score >= 60 ? '#ea580c' : '#16a34a'}
                    size="small" style={{ flex: 1 }} />
                  <span style={{ fontSize: 12, width: 28, textAlign: 'right' }}>{s.total_score}</span>
                </div>
              ))}
            </Space>
          </Card>
        </Col>
      </Row>

      <Card title={`Cases (${(cases as any[] || []).length})`}>
        <Table
          size="small" dataSource={cases as any[] || []} rowKey="id" pagination={false}
          onRow={r => ({ onClick: () => navigate(`/cases/${r.id}`), style: { cursor: 'pointer' } })}
          columns={[
            { title: 'Case #', dataIndex: 'case_number', width: 130 },
            { title: 'Title', dataIndex: 'title', ellipsis: true },
            { title: 'Severity', dataIndex: 'severity', width: 90,
              render: (v: Severity) => <SeverityBadge severity={v} /> },
            { title: 'Status', dataIndex: 'status', width: 150,
              render: (v: string) => <Tag>{v.replace(/_/g,' ')}</Tag> },
            { title: 'Created', dataIndex: 'created_at', width: 110,
              render: (v: string) => new Date(v).toLocaleDateString('en-SG') },
          ]}
        />
      </Card>
    </div>
  )
}
