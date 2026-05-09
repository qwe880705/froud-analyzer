import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import {
  Card, Col, Row, Tabs, Button, Select, Form, Input,
  Descriptions, Tag, Space, Modal, Typography, Alert, Badge,
} from 'antd'
import { ArrowLeftOutlined, FileTextOutlined, ExclamationCircleOutlined } from '@ant-design/icons'
import { api } from '../../api/client'
import { SeverityBadge } from '../../components/common/SeverityBadge'
import { CaseTimeline } from './CaseTimeline'
import type { CaseItem, Severity } from '../../types'

const TRANSITIONS: Record<string, string[]> = {
  open:           ['investigating', 'closed_cleared'],
  investigating:  ['pending_review', 'escalated', 'closed_confirmed', 'closed_cleared', 'closed_inconclusive'],
  pending_review: ['investigating', 'escalated', 'closed_confirmed', 'closed_cleared', 'closed_inconclusive'],
  escalated:      ['closed_confirmed', 'closed_inconclusive'],
}

export function CaseDetail() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [noteForm] = Form.useForm()
  const [addingNote, setAddingNote] = useState(false)

  const { data } = useQuery<CaseItem>({
    queryKey: ['case', id],
    queryFn: () => api.get(`/cases/${id}`),
  })

  const { data: notes } = useQuery<any[]>({
    queryKey: ['case-notes', id],
    queryFn: () => api.get(`/cases/${id}/notes`),
  })

  const updateStatus = useMutation({
    mutationFn: (status: string) => api.patch(`/cases/${id}/status`, { status }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['case', id] }),
  })

  const addNote = useMutation({
    mutationFn: (vals: any) => api.post(`/cases/${id}/notes`, vals),
    onSuccess: () => { qc.invalidateQueries({ queryKey: ['case-notes', id] }); noteForm.resetFields(); setAddingNote(false) },
  })

  if (!data) return null
  const c = data as CaseItem
  const allowed = TRANSITIONS[c.status] ?? []

  const handleStatus = (s: string) => {
    if (s.startsWith('closed')) {
      Modal.confirm({
        title: `Close case as "${s.replace(/closed_|_/g, ' ').trim()}"?`,
        icon: <ExclamationCircleOutlined />,
        onOk: () => updateStatus.mutate(s),
      })
    } else {
      updateStatus.mutate(s)
    }
  }

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} type="text" onClick={() => navigate('/cases')} style={{ marginBottom: 12 }}>
        Back to Cases
      </Button>

      <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16, flexWrap: 'wrap' }}>
        <Tag style={{ fontFamily: 'monospace' }}>{c.case_number}</Tag>
        <Tag color={c.status === 'investigating' ? 'processing' : 'default'}>{c.status.replace(/_/g,' ')}</Tag>
        <SeverityBadge severity={c.severity as Severity} />
        <span style={{ fontWeight: 700, fontSize: 18 }}>Score: {c.risk_score.toFixed(1)}</span>
        <Typography.Title level={4} style={{ margin: 0, flex: 1 }}>{c.title}</Typography.Title>
        {allowed.length > 0 && (
          <Select placeholder="Change Status →" style={{ width: 200 }}
            loading={updateStatus.isPending} onChange={handleStatus}
            options={allowed.map(s => ({ value: s, label: s.replace(/_/g,' ') }))} />
        )}
        <Button type="primary" icon={<FileTextOutlined />} onClick={() => navigate(`/cases/${id}/report`)}>
          Report
        </Button>
      </div>

      {(c.severity === 'critical' || c.severity === 'high') && (
        <Alert type="warning" showIcon style={{ marginBottom: 12 }}
          message={`${c.subject_user_name} · High-risk investigation active`}
          description={c.auto_created ? `Auto-created: score exceeded threshold` : ''} />
      )}

      <Row gutter={16} style={{ marginBottom: 16 }}>
        <Col span={10}>
          <Card size="small" title="Subject">
            <Descriptions column={1} size="small">
              <Descriptions.Item label="Name">{c.subject_user_name}</Descriptions.Item>
              <Descriptions.Item label="Email">{c.subject_user_email}</Descriptions.Item>
              <Descriptions.Item label="Dept">{c.department}</Descriptions.Item>
              <Descriptions.Item label="Assigned">{c.assigned_to || 'Unassigned'}</Descriptions.Item>
              <Descriptions.Item label="Events"><Badge count={c.event_count} showZero color="#1677ff" /></Descriptions.Item>
            </Descriptions>
          </Card>
        </Col>
        <Col span={14}>
          <Card size="small" title="Key Indicators">
            <Space wrap>
              {c.key_indicators.length
                ? c.key_indicators.map((ki, i) => <Tag key={i} color="orange">{ki}</Tag>)
                : <Typography.Text type="secondary">No indicators yet</Typography.Text>}
            </Space>
          </Card>
        </Col>
      </Row>

      <Tabs type="card" items={[
        {
          key: 'timeline', label: `Timeline (${c.event_count})`,
          children: <CaseTimeline caseId={id!} />,
        },
        {
          key: 'notes', label: `Notes (${c.note_count})`,
          children: (
            <div>
              <Button type="dashed" onClick={() => setAddingNote(true)} style={{ marginBottom: 12 }}>
                + Add Note
              </Button>
              {addingNote && (
                <Card size="small" style={{ marginBottom: 12 }}>
                  <Form form={noteForm} layout="vertical" onFinish={addNote.mutate}>
                    <Form.Item name="note_type" label="Type" initialValue="general">
                      <Select options={[
                        { value: 'general', label: 'General' },
                        { value: 'evidence_analysis', label: 'Evidence Analysis' },
                        { value: 'interview_note', label: 'Interview Note' },
                        { value: 'escalation_note', label: 'Escalation Note' },
                        { value: 'closure_note', label: 'Closure Note' },
                      ]} style={{ width: 200 }} />
                    </Form.Item>
                    <Form.Item name="content" label="Note" rules={[{ required: true }]}>
                      <Input.TextArea rows={4} placeholder="Investigation notes..." />
                    </Form.Item>
                    <Space>
                      <Button type="primary" htmlType="submit" loading={addNote.isPending}>Save</Button>
                      <Button onClick={() => setAddingNote(false)}>Cancel</Button>
                    </Space>
                  </Form>
                </Card>
              )}
              <Space direction="vertical" style={{ width: '100%' }}>
                {(notes as any[] || []).map((n: any) => (
                  <Card key={n.id} size="small" style={{ background: '#fafafa' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 6 }}>
                      <Space>
                        <Tag>{n.note_type.replace(/_/g,' ')}</Tag>
                        <span style={{ fontWeight: 500 }}>{n.created_by}</span>
                        {n.is_confidential && <Tag color="red">CONFIDENTIAL</Tag>}
                      </Space>
                      <Typography.Text type="secondary" style={{ fontSize: 11 }}>
                        {new Date(n.created_at).toLocaleString('en-SG')}
                      </Typography.Text>
                    </div>
                    <Typography.Paragraph style={{ margin: 0, whiteSpace: 'pre-wrap' }}>
                      {n.content}
                    </Typography.Paragraph>
                  </Card>
                ))}
              </Space>
            </div>
          ),
        },
      ]} />
    </div>
  )
}
