import type { DiagnosisResultData } from '@/api'

export type HealthRiskLevel = 'low' | 'medium' | 'high' | 'urgent'

export interface ClinicalFindingView {
  id: string
  sourceType: 'lab' | 'health_check_summary' | 'ct_report' | 'mri_report' | 'ultrasound_report' | 'ecg_ai'
  title: string
  summary: string
  severity: HealthRiskLevel
  actionHint: 'observe' | 'recheck' | 'clinic_visit' | 'urgent_visit'
  evidence: string[]
}

export interface HealthAnalysisResult {
  jobId: string
  status: 'completed'
  summary: string
  overallRisk: HealthRiskLevel
  findings: ClinicalFindingView[]
  nextSteps: string[]
  limitations: string[]
  disclaimer: string
  ecgResult?: DiagnosisResultData | null
}

export interface HealthJobResponse {
  id: string
  status: 'queued' | 'processing' | 'completed' | 'failed'
  message: string
  result?: HealthAnalysisResult | null
  error?: string | null
}
