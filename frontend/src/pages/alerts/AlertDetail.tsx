import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, Button, Descriptions, Tag, Space, Typography, Modal, Input } from 'antd'
import { ArrowLeftOutlined } from '@ant-design/icons'
import { useState } from 'react'
import { api } from '../../api/client'
import { SeverityBadge } from '../../components/common/SeverityBadge'
import type { AlertItem, Severity } from '../../types'

export function AlertDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [escalateModal, setEscalateModal] = useState(false)
  const [caseTitle, setCaseTitle] = useState('')
  const [notes, setNotes] = useState('')

  const { data: alert } = useQuery<AlertItem>({
    queryKey: ['alert', id],
    queryFn: () => api.get(`/alerts/${id}`),
  })

  const escalate = useMutation({
    mutationFn: () => api.post(`/alerts/${id}/escalate`, { case_title: caseTitle, notes }),
    onSuccess: (data: any) => { qc.invalidateQueries({ queryKey: ['alert', id] }); navigate(`/cases/${data.case_id}`) },
  })

  const updateStatus = useMutation({
    mutationFn: (status: string) => api.patch(`/alerts/${id}/status`, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['alert', id] }),
  })

  if (!alert) return null
  const a = alert as AlertItem

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} type="text" onClick={() => navigate('/alerts')} style={{ marginBottom: 16 }}>
        Back to Alerts
      </Button>

      <Card>
        <Space style={{ marginBottom: 16 }} wrap>
          <SeverityBadge severity={a.severity as Severity} />
          <Tag color="default">{a.alert_type}</Tag>
          <Tag color={a.status === 'new' ? 'blue' : 'default'}>{a.status.toUpperCase()}</Tag>
          <span style={{ fontWeight: 700, fontSize: 20 }}>Score: {a.risk_score}</span>
        </Space>

        <Typography.Title level={4} style={{ margin: '0 0 16px' }}>{a.title}</Typography.Title>

        <Descriptions column={2} bordered size="small">
          <Descriptions.Item label="User">{a.user_display_name}</Descriptions.Item>
          <Descriptions.Item label="Email">{a.user_email}</Descriptions.Item>
          <Descriptions.Item label="Department">{a.department}</Descriptions.Item>
          <Descriptions.Item label="Event Time">{new Date(a.alert_timestamp).toLocaleString('en-SG')}</Descriptions.Item>
          <Descriptions.Item label="Detected">{new Date(a.detected_at).toLocaleString('en-SG')}</Descriptions.Item>
          <Descriptions.Item label="Case">{a.case_id
            ? <Button type="link" size="small" onClick={() => navigate(`/cases/${a.case_id}`)}>View Case</Button>
            : 'None'}</Descriptions.Item>
          {a.description && (
            <Descriptions.Item label="Description" span={2}>{a.description}</Descriptions.Item>
          )}
          {a.reviewed_by && (
            <Descriptions.Item label="Reviewed By">{a.reviewed_by} at {a.reviewed_at ? new Date(a.reviewed_at).toLocaleString('en-SG') : ''}</Descriptions.Item>
          )}
          {a.dismiss_reason && (
            <Descriptions.Item label="Dismiss Reason" span={2}>{a.dismiss_reason}</Descriptions.Item>
          )}
        </Descriptions>

        {(a.status === 'new' || a.status === 'reviewing') && (
          <Space style={{ marginTop: 20 }}>
            {a.status === 'new' && (
              <Button onClick={() => updateStatus.mutate('reviewing')}>Mark Reviewing</Button>
            )}
            <Button type="primary" danger onClick={() => setEscalateModal(true)}>
              Escalate to Case
            </Button>
          </Space>
        )}
      </Card>

      <Modal
        open={escalateModal}
        title="Escalate to Case"
        onOk={() => escalate.mutate()}
        onCancel={() => setEscalateModal(false)}
        confirmLoading={escalate.isPending}
      >
        <Space direction="vertical" style={{ width: '100%' }}>
          <Input
            placeholder="Case title (optional)"
            value={caseTitle}
            onChange={e => setCaseTitle(e.target.value)}
          />
          <Input.TextArea
            rows={3}
            placeholder="Initial investigation notes (optional)"
            value={notes}
            onChange={e => setNotes(e.target.value)}
          />
        </Space>
      </Modal>
    </div>
  )
}
