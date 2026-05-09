import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Card, Button, Form, Input, Steps, Space, Alert, Typography, Tag } from 'antd'
import { ArrowLeftOutlined, SaveOutlined, CheckOutlined, ExportOutlined } from '@ant-design/icons'
import { api } from '../../api/client'

const SECTIONS = [
  { key: 'initial_assessment', label: 'Initial Assessment', rows: 4 },
  { key: 'key_indicators', label: 'Key Indicators', rows: 3 },
  { key: 'risk_analysis', label: 'Risk Analysis', rows: 5 },
  { key: 'evidence_summary', label: 'Evidence Summary', rows: 5 },
  { key: 'recommended_actions', label: 'Recommended Next Steps', rows: 4 },
  { key: 'final_summary', label: 'Final Case Summary', rows: 4 },
]

export function ReportGenerator() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const qc = useQueryClient()
  const [form] = Form.useForm()

  const { data: report } = useQuery<any>({
    queryKey: ['report', id],
    queryFn: () => api.get(`/reports/${id}`),
  })

  const create = useMutation({
    mutationFn: () => api.post(`/reports/${id}`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['report', id] }),
  })

  const save = useMutation({
    mutationFn: (vals: any) => api.patch(`/reports/${id}`, vals),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['report', id] }),
  })

  const submit = useMutation({
    mutationFn: () => api.post(`/reports/${id}/submit`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['report', id] }),
  })

  const approve = useMutation({
    mutationFn: () => api.post(`/reports/${id}/approve`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['report', id] }),
  })

  const r = report as any
  const status = r?.status ?? 'none'
  const stepIdx = { none: 0, draft: 1, pending_review: 2, approved: 3, exported: 4 }[status] ?? 0

  return (
    <div>
      <Button icon={<ArrowLeftOutlined />} type="text" onClick={() => navigate(`/cases/${id}`)} style={{ marginBottom: 12 }}>
        Back to Case
      </Button>

      <Typography.Title level={4} style={{ marginBottom: 16 }}>Investigation Report</Typography.Title>

      <Steps size="small" current={stepIdx} style={{ marginBottom: 20 }}
        items={[
          { title: 'No Report' },
          { title: 'Draft' },
          { title: 'Pending Review' },
          { title: 'Approved' },
          { title: 'Exported' },
        ]}
      />

      {!r && (
        <Button type="primary" onClick={() => create.mutate()} loading={create.isPending}>
          Auto-Generate Draft Report
        </Button>
      )}

      {r && (
        <>
          <div style={{ marginBottom: 12, display: 'flex', gap: 8, alignItems: 'center' }}>
            <Tag>v{r.version}</Tag>
            <Tag color={status === 'approved' ? 'green' : status === 'pending_review' ? 'orange' : 'blue'}>
              {status.replace(/_/g,' ').toUpperCase()}
            </Tag>
            {r.approved_by && <Typography.Text type="secondary" style={{ fontSize: 12 }}>Approved by {r.approved_by}</Typography.Text>}
          </div>

          {status === 'draft' && (
            <Alert type="info" showIcon message="Draft mode — edit freely, then submit for review." style={{ marginBottom: 12 }} />
          )}

          <Form
            form={form}
            layout="vertical"
            initialValues={r}
            onFinish={save.mutate}
          >
            {SECTIONS.map(s => (
              <Form.Item key={s.key} name={s.key} label={<strong>{s.label}</strong>}>
                <Input.TextArea
                  rows={s.rows}
                  disabled={status !== 'draft'}
                  style={{ fontFamily: 'monospace', fontSize: 13 }}
                />
              </Form.Item>
            ))}

            <Space>
              {status === 'draft' && (
                <>
                  <Button type="primary" htmlType="submit" icon={<SaveOutlined />} loading={save.isPending}>
                    Save Draft
                  </Button>
                  <Button icon={<CheckOutlined />} onClick={() => submit.mutate()} loading={submit.isPending}>
                    Submit for Review
                  </Button>
                </>
              )}
              {status === 'pending_review' && (
                <Button type="primary" icon={<CheckOutlined />} onClick={() => approve.mutate()} loading={approve.isPending}>
                  Approve Report
                </Button>
              )}
              {status === 'approved' && (
                <Button
                  type="primary"
                  icon={<ExportOutlined />}
                  onClick={() => window.open(`/api/v1/reports/${id}/export`, '_blank')}
                >
                  Export HTML Report
                </Button>
              )}
            </Space>
          </Form>
        </>
      )}
    </div>
  )
}
