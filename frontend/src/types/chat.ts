import type { DiagnosisResultData } from '../api'
import type { HealthAnalysisResult } from './health'

export interface AttachedFileSummary {
  id: string
  name: string
  size: number
  category: 'report_pdf' | 'report_image' | 'ecg_image' | 'dat' | 'hea'
}

export interface ConversationMessage {
  id: string
  role: 'assistant' | 'user'
  type: 'intro' | 'prompt' | 'guidance' | 'diagnosis' | 'health_report'
  title?: string
  content: string
  createdAt: string
  attachments?: AttachedFileSummary[]
  result?: DiagnosisResultData | HealthAnalysisResult
  status?: 'pending' | 'completed' | 'error'
  errorDetail?: string
}

export interface PerLeadQC {
  lead_index: number
  quality: 'good' | 'warn' | 'poor' | 'fail'
  flatness: number
  coverage: number
}

export interface ChatSession {
  id: string
  title: string
  preview: string
  updatedAt: string
  messages: ConversationMessage[]
}
