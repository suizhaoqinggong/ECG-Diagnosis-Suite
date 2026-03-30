import type { DiagnosisResultData } from '../api'

export interface AttachedFileSummary {
  id: string
  name: string
  size: number
  category: 'image' | 'dat' | 'hea'
}

export interface ConversationMessage {
  id: string
  role: 'assistant' | 'user'
  type: 'intro' | 'prompt' | 'guidance' | 'diagnosis'
  title?: string
  content: string
  createdAt: string
  attachments?: AttachedFileSummary[]
  result?: DiagnosisResultData

  // New fields for pending state management
  status?: 'pending' | 'completed' | 'error'
  errorDetail?: string
}

export interface ChatSession {
  id: string
  title: string
  preview: string
  updatedAt: string
  messages: ConversationMessage[]
}
