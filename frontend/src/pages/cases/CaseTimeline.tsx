import { useQuery } from '@tanstack/react-query'
import { Timeline, Tag, Typography, Spin, Empty, Tooltip } from 'antd'
import {
  CloudUploadOutlined, MailOutlined, UsbOutlined, LoginOutlined,
  GlobalOutlined, FileOutlined, WarningOutlined,
} from '@ant-design/icons'
import { api } from '../../api/client'
import type { TimelineEvent } from '../../types'

const CAT: Record<string, { icon: React.ReactNode; color: string }> = {
  cloud_upload:       { icon: <CloudUploadOutlined />, color: '#ea580c' },
  email_send:         { icon: <MailOutlined />,        color: '#7c3aed' },
  email_forward:      { icon: <MailOutlined />,        color: '#dc2626' },
  usb_transfer:       { icon: <UsbOutlined />,         color: '#dc2626' },
  login:              { icon: <LoginOutlined />,       color: '#1677ff' },
  web_browsing:       { icon: <GlobalOutlined />,      color: '#16a34a' },
  file_download:      { icon: <FileOutlined />,        color: '#ca8a04' },
  file_access:        { icon: <FileOutlined />,        color: '#888' },
  policy_violation:   { icon: <WarningOutlined />,     color: '#dc2626' },
  data_exfiltration:  { icon: <WarningOutlined />,     color: '#dc2626' },
}

const RELEVANCE_STYLE: Record<string, React.CSSProperties> = {
  primary:     { border: '2px solid #dc2626', background: '#fff5f5', borderRadius: 6, padding: '8px 12px' },
  supporting:  { border: '1px solid #e5e7eb', background: '#fff',    borderRadius: 6, padding: '8px 12px' },
  contextual:  { border: '1px dashed #d1d5db', background: '#fafafa', borderRadius: 6, padding: '8px 12px' },
  exculpatory: { border: '1px solid #16a34a', background: '#f0fdf4', borderRadius: 6, padding: '8px 12px' },
}

export function CaseTimeline({ caseId }: { caseId: string }) {
  const { data: events, isLoading } = useQuery<TimelineEvent[]>({
    queryKey: ['case-timeline', caseId],
    queryFn: () => api.get(`/cases/${caseId}/timeline`),
  })

  if (isLoading) return <Spin />
  if (!events?.length) return <Empty description="No events linked to this case" />

  return (
    <div>
      <div style={{ marginBottom: 10, display: 'flex', gap: 8 }}>
        {Object.entries(RELEVANCE_STYLE).map(([rel, s]) => (
          <span key={rel} style={{ ...s, padding: '1px 8px', fontSize: 11 }}>{rel}</span>
        ))}
      </div>
      <Timeline
        mode="left"
        items={events.map(ev => {
          const cfg = CAT[ev.event_category] ?? { icon: <FileOutlined />, color: '#888' }
          const style = RELEVANCE_STYLE[ev.relevance] ?? RELEVANCE_STYLE.supporting
          return {
            dot: <span style={{ fontSize: 15, color: cfg.color }}>{cfg.icon}</span>,
            children: (
              <div style={style}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div>
                    <Typography.Text strong style={{ fontSize: 13 }}>{ev.summary}</Typography.Text>
                    {ev.relevance === 'primary' && <Tag color="red" style={{ marginLeft: 6, fontSize: 10 }}>PRIMARY</Tag>}
                    {ev.relevance === 'exculpatory' && <Tag color="green" style={{ marginLeft: 6, fontSize: 10 }}>EXCULPATORY</Tag>}
                  </div>
                  <Typography.Text type="secondary" style={{ fontSize: 11, minWidth: 140, textAlign: 'right' }}>
                    {new Date(ev.event_timestamp).toLocaleString('en-SG')}
                  </Typography.Text>
                </div>
                <div style={{ marginTop: 5, display: 'flex', gap: 6, flexWrap: 'wrap' }}>
                  <Tag color="blue" style={{ fontSize: 10 }}>{ev.source}</Tag>
                  <Tag style={{ fontSize: 10 }}>{ev.event_type}</Tag>
                  {ev.action_result && (
                    <Tag color={ev.action_result.toLowerCase() === 'blocked' ? 'red' : 'green'} style={{ fontSize: 10 }}>
                      {ev.action_result}
                    </Tag>
                  )}
                  {ev.object_name && (
                    <Tooltip title={ev.object_name}>
                      <Tag style={{ fontSize: 10, maxWidth: 180, overflow: 'hidden', textOverflow: 'ellipsis' }}>
                        📄 {ev.object_name}
                      </Tag>
                    </Tooltip>
                  )}
                  {ev.destination_detail && (
                    <Tag color="orange" style={{ fontSize: 10 }}>→ {ev.destination_detail}</Tag>
                  )}
                </div>
              </div>
            ),
          }
        })}
      />
    </div>
  )
}
