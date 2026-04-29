import type { ChatSession, ConversationMessage, AttachedFileSummary } from '@/types/chat'
import type { DiagnosisResultData } from '@/api'
import type { HealthAnalysisResult } from '@/types/health'
import { STORAGE_VERSION } from '@/utils/storage'

// ===== Types =====

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
    isSidebarOpen: boolean
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
  | { type: 'SET_SIDEBAR_OPEN'; open: boolean }
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

// ===== Helpers =====

export function createId(): string {
  if (typeof crypto !== 'undefined' && typeof crypto.randomUUID === 'function') {
    return crypto.randomUUID()
  }

  if (typeof crypto !== 'undefined' && typeof crypto.getRandomValues === 'function') {
    const bytes = new Uint8Array(16)
    crypto.getRandomValues(bytes)
    bytes[6] = (bytes[6] & 0x0f) | 0x40
    bytes[8] = (bytes[8] & 0x3f) | 0x80
    const hex = Array.from(bytes, byte => byte.toString(16).padStart(2, '0')).join('')
    return [
      hex.slice(0, 8),
      hex.slice(8, 12),
      hex.slice(12, 16),
      hex.slice(16, 20),
      hex.slice(20),
    ].join('-')
  }

  return '00000000-0000-4000-8000-000000000000'
}

export function detectCategory(file: File): AttachedFileSummary['category'] | null {
  const lowerName = file.name.toLowerCase()
  if (lowerName.endsWith('.pdf')) return 'report_pdf'
  if (lowerName.endsWith('.dat')) return 'dat'
  if (lowerName.endsWith('.hea')) return 'hea'
  if (file.type.startsWith('image/') || /\.(png|jpe?g)$/i.test(lowerName)) {
    return 'report_image'
  }
  return null
}

export function createEmptySession(): ChatSession {
  const timestamp = new Date().toISOString()
  return {
    id: createId(),
    title: 'New analysis',
    preview: 'Start with an ECG file or a clinical note.',
    updatedAt: timestamp,
    messages: [{
      id: createId(),
      role: 'assistant',
      type: 'intro',
      title: 'A calmer space for ECG review',
      content: 'Upload an ECG image or a matched .dat + .hea pair and the workspace will keep the full interpretation in a readable, document-like flow.\n\nUse the note area to add context before submission. Your diagnosis history stays in the left sidebar so each review feels like opening a draft, not scanning a message thread.',
      createdAt: timestamp,
      status: 'completed',
    }],
  }
}

export function calculatePairStatus(
  attachments: PendingAttachment[],
): WorkspaceState['composer']['pairStatus'] {
  const hasImage = attachments.some(a => a.summary.category === 'report_image')
  const hasDat = attachments.some(a => a.summary.category === 'dat')
  const hasHea = attachments.some(a => a.summary.category === 'hea')
  if (hasImage) return 'image'
  if (hasDat && hasHea) {
    const datName = attachments.find(a => a.summary.category === 'dat')!.file.name.replace(/\.dat$/i, '')
    const heaName = attachments.find(a => a.summary.category === 'hea')!.file.name.replace(/\.hea$/i, '')
    return datName === heaName ? 'matched' : 'mismatch'
  }
  if (hasDat || hasHea) return 'partial'
  return 'empty'
}

export function validateAttachments(attachments: PendingAttachment[]): string[] {
  const errors: string[] = []
  const hasImage = attachments.some(a => a.summary.category === 'report_image')
  const hasDat = attachments.some(a => a.summary.category === 'dat')
  const hasHea = attachments.some(a => a.summary.category === 'hea')

  if (hasImage && (hasDat || hasHea)) {
    errors.push('Image analysis accepts a single ECG image. Remove the data files.')
  }
  if (hasImage && attachments.length > 1) {
    errors.push('Image analysis accepts a single ECG image. Remove the extra attachments.')
  }
  if (!hasImage && (hasDat || hasHea) && !(hasDat && hasHea)) {
    errors.push('Signal analysis needs both files in the pair. Attach one .dat file and the matching .hea header.')
  }
  if (hasDat && hasHea) {
    const datName = attachments.find(a => a.summary.category === 'dat')!.file.name.replace(/\.dat$/i, '')
    const heaName = attachments.find(a => a.summary.category === 'hea')!.file.name.replace(/\.hea$/i, '')
    if (datName !== heaName) {
      errors.push('The .dat and .hea filenames need to match exactly before upload.')
    }
  }
  return errors
}

export function sortSessions(sessions: ChatSession[]): ChatSession[] {
  return [...sessions].sort(
    (left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt),
  )
}

export function buildSessionPreview(messages: ConversationMessage[]): string {
  const candidate = [...messages]
    .reverse()
    .find(message => message.type !== 'intro' && message.content.trim().length > 0)

  if (candidate) {
    return candidate.title?.trim() || candidate.content.trim()
  }

  return 'Start with an ECG file or a clinical note.'
}

function cloneEmptySession(): ChatSession {
  return createEmptySession()
}

// ===== Initial State =====

export function createInitialState(): WorkspaceState {
  const initialSession = cloneEmptySession()
  return {
    persisted: {
      sessions: [initialSession],
      activeSessionId: initialSession.id,
      persistenceEnabled: true,
      storageVersion: STORAGE_VERSION,
    },
    composer: {
      draft: '',
      attachments: [],
      pairStatus: 'empty',
      validationErrors: [],
      replacedFileNames: [],
    },
    submission: {
      activeMessageId: null,
      phase: 'idle',
      progress: null,
      error: null,
      canRetry: false,
    },
    ui: {
      isDragging: false,
      isSidebarOpen: false,
      renamingSessionId: null,
      printableMessageId: null,
      storageWarning: null,
    },
  }
}

// ===== Reducer =====

export function workspaceReducer(state: WorkspaceState, action: WorkspaceAction): WorkspaceState {
  switch (action.type) {
    case 'HYDRATE': {
      const sessions = action.sessions.length > 0 ? sortSessions(action.sessions) : [cloneEmptySession()]
      const activeExists = sessions.some(session => session.id === action.activeSessionId)
      return {
        ...state,
        persisted: {
          ...state.persisted,
          sessions,
          activeSessionId: activeExists ? action.activeSessionId : sessions[0].id,
        },
      }
    }

    case 'SET_DRAFT': {
      return {
        ...state,
        composer: { ...state.composer, draft: action.value },
      }
    }

    case 'ADD_FILES': {
      const fileArray = Array.from(action.files)
      const newAttachments: PendingAttachment[] = []
      const errors: string[] = []

      for (const file of fileArray) {
        if (file.size > 10 * 1024 * 1024) {
          errors.push(`${file.name} exceeds the 10MB limit.`)
          continue
        }
        const category = detectCategory(file)
        if (category === null) {
          errors.push(`Unsupported file type: ${file.name}`)
          continue
        }
        const id = createId()
        newAttachments.push({
          id,
          file,
          summary: { id, name: file.name, size: file.size, category },
        })
      }

      const existingNonImage = state.composer.attachments.filter(a => a.summary.category !== 'report_image')
      const hasNewImage = newAttachments.some(a => a.summary.category === 'report_image')

      let merged: PendingAttachment[]
      const replacedNames: string[] = []
      if (hasNewImage) {
        const existingNames = state.composer.attachments.map(a => a.summary.name)
        if (existingNames.length > 0) replacedNames.push(...existingNames)
        const imageAttachment = newAttachments.find(a => a.summary.category === 'report_image')!
        merged = [imageAttachment]
      } else {
        const byCategory = new Map(
          existingNonImage.map(a => [a.summary.category, a] as const),
        )
        for (const attachment of newAttachments) {
          const existing = byCategory.get(attachment.summary.category)
          if (existing && existing.id !== attachment.id) replacedNames.push(existing.summary.name)
          byCategory.set(attachment.summary.category, attachment)
        }
        merged = Array.from(byCategory.values())
      }

      const pairStatus = calculatePairStatus(merged)
      const validationErrors = [...errors, ...validateAttachments(merged)]

      return {
        ...state,
        composer: {
          ...state.composer,
          attachments: merged,
          pairStatus,
          validationErrors,
          replacedFileNames: replacedNames,
        },
      }
    }

    case 'REMOVE_FILE': {
      const attachments = state.composer.attachments.filter(a => a.id !== action.id)
      return {
        ...state,
        composer: {
          ...state.composer,
          attachments,
          pairStatus: calculatePairStatus(attachments),
          validationErrors: validateAttachments(attachments),
        },
      }
    }

    case 'CLEAR_COMPOSER': {
      return {
        ...state,
        composer: {
          draft: '',
          attachments: [],
          pairStatus: 'empty',
          validationErrors: [],
          replacedFileNames: [],
        },
      }
    }

    case 'SUBMIT_STARTED': {
      return {
        ...state,
        submission: {
          activeMessageId: action.messageId,
          phase: 'uploading',
          progress: null,
          error: null,
          canRetry: false,
        },
      }
    }

    case 'SUBMIT_UPLOAD_PROGRESS': {
      return {
        ...state,
        submission: { ...state.submission, progress: action.progress },
      }
    }

    case 'SUBMIT_PROCESSING': {
      return {
        ...state,
        submission: { ...state.submission, phase: 'processing', progress: null },
      }
    }

    case 'SUBMIT_SUCCEEDED': {
      return {
        ...state,
        submission: {
          activeMessageId: null,
          phase: 'succeeded',
          progress: null,
          error: null,
          canRetry: false,
        },
      }
    }

    case 'SUBMIT_FAILED': {
      return {
        ...state,
        submission: {
          activeMessageId: null,
          phase: 'failed',
          progress: null,
          error: action.error,
          canRetry: true,
        },
      }
    }

    case 'SUBMIT_CANCEL': {
      return {
        ...state,
        submission: {
          activeMessageId: null,
          phase: 'idle',
          progress: null,
          error: null,
          canRetry: false,
        },
      }
    }

    case 'SET_DRAG_ACTIVE': {
      return {
        ...state,
        ui: { ...state.ui, isDragging: action.active },
      }
    }

    case 'SET_SIDEBAR_OPEN': {
      return {
        ...state,
        ui: { ...state.ui, isSidebarOpen: action.open },
      }
    }

    case 'SET_RENAMING': {
      return {
        ...state,
        ui: { ...state.ui, renamingSessionId: action.sessionId },
      }
    }

    case 'SET_PRINTABLE_MESSAGE': {
      return {
        ...state,
        ui: { ...state.ui, printableMessageId: action.messageId },
      }
    }

    case 'CREATE_SESSION': {
      const newSession = action.session ?? cloneEmptySession()
      return {
        ...state,
        persisted: {
          ...state.persisted,
          sessions: sortSessions([newSession, ...state.persisted.sessions]),
          activeSessionId: newSession.id,
        },
        composer: {
          draft: '',
          attachments: [],
          pairStatus: 'empty',
          validationErrors: [],
          replacedFileNames: [],
        },
        submission: {
          activeMessageId: null,
          phase: 'idle',
          progress: null,
          error: null,
          canRetry: false,
        },
      }
    }

    case 'SWITCH_SESSION': {
      return {
        ...state,
        persisted: {
          ...state.persisted,
          activeSessionId: action.id,
        },
        composer: {
          draft: '',
          attachments: [],
          pairStatus: 'empty',
          validationErrors: [],
          replacedFileNames: [],
        },
        submission: {
          activeMessageId: null,
          phase: 'idle',
          progress: null,
          error: null,
          canRetry: false,
        },
      }
    }

    case 'RENAME_SESSION': {
      return {
        ...state,
        persisted: {
          ...state.persisted,
          sessions: state.persisted.sessions.map(session =>
            session.id === action.id
              ? {
                  ...session,
                  title: action.title,
                  updatedAt: new Date().toISOString(),
                }
              : session,
          ),
        },
      }
    }

    case 'DELETE_SESSION': {
      const remaining = state.persisted.sessions.filter(session => session.id !== action.id)
      if (remaining.length === 0) {
        const newSession = cloneEmptySession()
        return {
          ...state,
          persisted: {
            ...state.persisted,
            sessions: [newSession],
            activeSessionId: newSession.id,
          },
          composer: {
            draft: '',
            attachments: [],
            pairStatus: 'empty',
            validationErrors: [],
            replacedFileNames: [],
          },
          submission: {
            activeMessageId: null,
            phase: 'idle',
            progress: null,
            error: null,
            canRetry: false,
          },
        }
      }

      const isActive = action.id === state.persisted.activeSessionId
      const nextActiveId = isActive ? remaining[0].id : state.persisted.activeSessionId

      return {
        ...state,
        persisted: {
          ...state.persisted,
          sessions: sortSessions(remaining),
          activeSessionId: nextActiveId,
        },
        composer: isActive
          ? {
              draft: '',
              attachments: [],
              pairStatus: 'empty',
              validationErrors: [],
              replacedFileNames: [],
            }
          : state.composer,
        submission: isActive
          ? {
              activeMessageId: null,
              phase: 'idle',
              progress: null,
              error: null,
              canRetry: false,
            }
          : state.submission,
      }
    }

    case 'CLEAR_ALL_SESSIONS': {
      const freshSession = action.session ?? cloneEmptySession()
      return {
        ...state,
        persisted: {
          ...state.persisted,
          sessions: [freshSession],
          activeSessionId: freshSession.id,
        },
        composer: {
          draft: '',
          attachments: [],
          pairStatus: 'empty',
          validationErrors: [],
          replacedFileNames: [],
        },
        submission: {
          activeMessageId: null,
          phase: 'idle',
          progress: null,
          error: null,
          canRetry: false,
        },
      }
    }

    case 'TOGGLE_PERSISTENCE': {
      return {
        ...state,
        persisted: {
          ...state.persisted,
          persistenceEnabled: !state.persisted.persistenceEnabled,
        },
      }
    }

    case 'APPEND_MESSAGE': {
      return {
        ...state,
        persisted: {
          ...state.persisted,
          sessions: sortSessions(state.persisted.sessions.map(session =>
            session.id === action.sessionId
              ? {
                  ...session,
                  messages: [...session.messages, action.message],
                  updatedAt: action.message.createdAt,
                  preview: buildSessionPreview([...session.messages, action.message]),
                }
              : session,
          )),
        },
      }
    }

    case 'UPDATE_MESSAGE': {
      return {
        ...state,
        persisted: {
          ...state.persisted,
          sessions: state.persisted.sessions.map(session =>
            session.id === action.sessionId
              ? (() => {
                  const messages = session.messages.map(message =>
                    message.id === action.messageId ? { ...message, ...action.updates } : message,
                  )
                  return {
                    ...session,
                    messages,
                    preview: buildSessionPreview(messages),
                  }
                })()
              : session,
          ),
        },
      }
    }

    case 'CLEAR_REPL_FILES': {
      return {
        ...state,
        composer: { ...state.composer, replacedFileNames: [] },
      }
    }

    default:
      return state
  }
}
