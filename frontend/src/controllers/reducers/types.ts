import type { ChatSession, ConversationMessage, AttachedFileSummary } from '@/types/chat'
import type { DiagnosisResultData } from '@/api'
import type { HealthAnalysisResult } from '@/types/health'

export interface PendingAttachment {
  id: string
  file: File
  summary: AttachedFileSummary
}

export interface WorkspaceState {
  persisted: {
    sessions: ChatSession[]
    activeSessionId: string
    persistenceEnabled: boolean
    storageVersion: number
  }
  composer: {
    draft: string
    attachments: PendingAttachment[]
    pairStatus: 'empty' | 'partial' | 'matched' | 'mismatch' | 'image'
    validationErrors: string[]
    replacedFileNames: string[]
  }
  submission: {
    activeMessageId: string | null
    phase: 'idle' | 'uploading' | 'processing' | 'succeeded' | 'failed'
    progress: number | null
    error: string | null
    canRetry: boolean
  }
  ui: {
    isDragging: boolean
    renamingSessionId: string | null
    printableMessageId: string | null
    storageWarning: string | null
  }
}

export type WorkspaceAction =
  | { type: 'HYDRATE'; sessions: ChatSession[]; activeSessionId: string }
  | { type: 'SET_DRAFT'; value: string }
  | { type: 'ADD_FILES'; files: FileList | File[] }
  | { type: 'REMOVE_FILE'; id: string }
  | { type: 'CLEAR_COMPOSER' }
  | { type: 'SUBMIT_STARTED'; messageId: string }
  | { type: 'SUBMIT_UPLOAD_PROGRESS'; progress: number }
  | { type: 'SUBMIT_PROCESSING' }
  | { type: 'SUBMIT_SUCCEEDED'; result: DiagnosisResultData | HealthAnalysisResult }
  | { type: 'SUBMIT_FAILED'; error: string }
  | { type: 'SUBMIT_CANCEL' }
  | { type: 'SET_DRAG_ACTIVE'; active: boolean }
  | { type: 'SET_RENAMING'; sessionId: string | null }
  | { type: 'SET_PRINTABLE_MESSAGE'; messageId: string | null }
  | { type: 'CREATE_SESSION'; session?: ChatSession }
  | { type: 'SWITCH_SESSION'; id: string }
  | { type: 'RENAME_SESSION'; id: string; title: string }
  | { type: 'DELETE_SESSION'; id: string }
  | { type: 'CLEAR_ALL_SESSIONS'; session?: ChatSession }
  | { type: 'TOGGLE_PERSISTENCE' }
  | { type: 'APPEND_MESSAGE'; sessionId: string; message: ConversationMessage }
  | { type: 'UPDATE_MESSAGE'; sessionId: string; messageId: string; updates: Partial<ConversationMessage> }
  | { type: 'CLEAR_REPL_FILES' }
