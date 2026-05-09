import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Card, Upload, Select, Button, Table, Tag, Typography, Alert, Form, Space } from 'antd'
import { InboxOutlined } from '@ant-design/icons'
import axios from 'axios'
import { api } from '../../api/client'

const SOURCES = [
  { value: 'hr_system',           label: 'HR System (Users)' },
  { value: 'purview_dlp',         label: 'Microsoft Purview DLP' },
  { value: 'entra_id',            label: 'Entra ID / Azure AD Login' },
  { value: 'cloud_upload',        label: 'Cloud Upload Log' },
  { value: 'email_log',           label: 'Email Log' },
  { value: 'usb_file_transfer',   label: 'USB / File Transfer' },
  { value: 'defender_endpoint',   label: 'Microsoft Defender Endpoint' },
  { value: 'proxy_web',           label: 'Proxy / Web Log' },
  { value: 'sentinel',            label: 'Microsoft Sentinel / SIEM' },
]

export function DataImport() {
  const qc = useQueryClient()
  const [sourceType, setSourceType] = useState<string>()
  const [file, setFile] = useState<File>()
  const [result, setResult] = useState<any>()

  const { data: batches } = useQuery<any>({
    queryKey: ['batches'],
    queryFn: () => api.get('/ingest/batches'),
  })

  const importMutation = useMutation({
    mutationFn: async () => {
      const fd = new FormData()
      fd.append('file', file!)
      fd.append('source_type', sourceType!)
      const res = await axios.post('/api/v1/ingest/csv', fd)
      return res.data.data
    },
    onSuccess: (data) => {
      setResult(data)
      qc.invalidateQueries({ queryKey: ['batches'] })
      qc.invalidateQueries({ queryKey: ['dashboard'] })
      qc.invalidateQueries({ queryKey: ['alerts'] })
    },
  })

  return (
    <div>
      <Typography.Title level={4} style={{ marginBottom: 20 }}>Import Data</Typography.Title>

      <Card title="Upload CSV" style={{ marginBottom: 24 }}>
        <Form layout="vertical">
          <Form.Item label="Data Source Type" required style={{ maxWidth: 400 }}>
            <Select placeholder="Select source type..." options={SOURCES}
              onChange={setSourceType} value={sourceType} />
          </Form.Item>
          <Form.Item label="CSV File">
            <Upload.Dragger
              accept=".csv" maxCount={1}
              beforeUpload={f => { setFile(f); return false }}
              onRemove={() => setFile(undefined)}
            >
              <p className="ant-upload-drag-icon"><InboxOutlined /></p>
              <p>Click or drag CSV file here</p>
              <p style={{ fontSize: 12, color: '#888' }}>Max 50MB · Must match selected source type</p>
            </Upload.Dragger>
          </Form.Item>
          <Button type="primary" size="large"
            disabled={!sourceType || !file}
            loading={importMutation.isPending}
            onClick={() => importMutation.mutate()}>
            Import CSV
          </Button>
        </Form>

        {result && (
          <Alert style={{ marginTop: 16 }}
            type={result.error_count > 0 ? 'warning' : 'success'} showIcon
            message={`Import complete: ${result.success_count} records`}
            description={
              <Space direction="vertical" size={2}>
                <span>Total: {result.record_count} · Success: {result.success_count} · Errors: {result.error_count}</span>
                {result.alerts_created > 0 && <span>🔔 Alerts created: {result.alerts_created}</span>}
                {result.cases_created > 0 && <span>📁 Cases auto-created: {result.cases_created}</span>}
                {result.errors?.length > 0 && (
                  <details><summary>Errors</summary>
                    <pre style={{ fontSize: 11 }}>{result.errors.join('\n')}</pre>
                  </details>
                )}
              </Space>
            }
          />
        )}
      </Card>

      <Card title="Import History">
        <Table
          size="small"
          dataSource={(batches as any)?.items ?? []}
          rowKey="id" pagination={{ pageSize: 10 }}
          columns={[
            { title: 'Source', dataIndex: 'data_source_type', width: 220 },
            { title: 'File', dataIndex: 'filename', ellipsis: true },
            { title: 'Status', dataIndex: 'status', width: 90,
              render: (v: string) => <Tag color={v === 'completed' ? 'green' : v === 'failed' ? 'red' : 'blue'}>{v}</Tag> },
            { title: 'Records', dataIndex: 'record_count', width: 80, align: 'right' as const },
            { title: 'Errors', dataIndex: 'error_count', width: 70, align: 'right' as const,
              render: (v: number) => v > 0 ? <span style={{ color: '#dc2626' }}>{v}</span> : v },
            { title: 'By', dataIndex: 'imported_by', width: 180, ellipsis: true },
            { title: 'Time', dataIndex: 'started_at', width: 155,
              render: (v: string) => new Date(v).toLocaleString('en-SG') },
          ]}
        />
      </Card>
    </div>
  )
}
