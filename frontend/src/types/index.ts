export type Severity = 'low' | 'medium' | 'high' | 'critical'
export type AlertStatus = 'new' | 'reviewing' | 'escalated' | 'dismissed' | 'merged'
export type CaseStatus =
  | 'open' | 'investigating' | 'pending_review'
  | 'escalated' | 'closed_confirmed' | 'closed_cleared' | 'closed_inconclusive'

export interface User {
  id: string
  employee_id: string
  display_name: string
  email: string
  department: string | null
  job_title: string | null
  location: string | null
  employment_status: string
  hire_date: string | null
  termination_date: string | null
  is_on_pip: boolean
  is_pending_resign: boolean
  is_pending_transfer: boolean
  hr_risk_flag: string | null
}

export interface AlertItem {
  id: string
  user_email: string
  user_display_name: string
  department: string | null
  alert_type: string
  title: string
  description: string | null
  severity: Severity
  risk_score: number
  status: AlertStatus
  alert_timestamp: string
  detected_at: string
  case_id: string | null
  reviewed_by: string | null
  reviewed_at: string | null
  dismiss_reason: string | null
}

export interface CaseItem {
  id: string
  case_number: string
  title: string
  subject_user_email: string
  subject_user_name: string
  department: string | null
  severity: Severity
  risk_score: number
  status: CaseStatus
  assigned_to: string | null
  case_type: string
  key_indicators: string[]
  auto_created: boolean
  event_count: number
  note_count: number
  case_period_start: string | null
  case_period_end: string | null
  created_at: string
}

export interface TimelineEvent {
  event_id: string
  event_timestamp: string
  event_category: string
  event_type: string
  source: string
  summary: string
  severity_original: string | null
  relevance: 'primary' | 'supporting' | 'contextual' | 'exculpatory'
  object_name: string | null
  destination_detail: string | null
  action_result: string | null
}

export interface RiskScore {
  id: string
  total_score: number
  severity: Severity
  score_data_exfil: number
  score_access_anomaly: number
  score_behavior_dev: number
  score_hr_context: number
  score_temporal: number
  event_count: number
  calculated_at: string
  calculated_by: string
}

export interface PaginatedResponse<T> {
  items: T[]
  total: number
  page: number
  page_size: number
  has_next: boolean
}

export interface StandardResponse<T> {
  success: boolean
  data: T | null
  message: string | null
}
