import { Tag } from 'antd'
import type { Severity } from '../../types'

const CFG: Record<Severity, { color: string; label: string }> = {
  critical: { color: 'red',    label: 'Critical' },
  high:     { color: 'orange', label: 'High'     },
  medium:   { color: 'gold',   label: 'Medium'   },
  low:      { color: 'green',  label: 'Low'       },
}

export function SeverityBadge({ severity }: { severity: Severity }) {
  const cfg = CFG[severity] ?? CFG.low
  return <Tag color={cfg.color}>{cfg.label}</Tag>
}
