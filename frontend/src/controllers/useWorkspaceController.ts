import { useReducer, useCallback, useRef, useEffect } from 'react'
import toast from 'react-hot-toast'
import type { ChatSession, ConversationMessage, AttachedFileSummary } from '@/types/chat'
import type { DiagnosisResultData } from '@/api'
import { diagnosisApi } from '@/api'
import { extractErrorMessage } from '@/api/client'

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
  | { type: 'SUBMIT_SUCCEEDED'; result: DiagnosisResultData }
  | { type: 'SUBMIT_FAILED'; error: string }
  | { type: 'SUBMIT_CANCEL' }
  | { type: 'SET_DRAG_ACTIVE'; active: boolean }
  | { type: 'SET_SIDEBAR_OPEN'; open: boolean }
  | { type: 'SET_RENAMING'; sessionId: string | null }
  | { type: 'SET_PRINTABLE_MESSAGE'; messageId: string | null }
  | { type: 'CREATE_SESSION' }
  | { type: 'SWITCH_SESSION'; id: string }
  | { type: 'RENAME_SESSION'; id: string; title: string }
  | { type: 'DELETE_SESSION'; id: string }
  | { type: 'CLEAR_ALL_SESSIONS' }
  | { type: 'TOGGLE_PERSISTENCE' }
  | { type: 'APPEND_MESSAGE'; sessionId: string; message: ConversationMessage }
  | { type: 'UPDATE_MESSAGE'; sessionId: string; messageId: string; updates: Partial<ConversationMessage> }
  | { type: 'CLEAR_REPL_FILES' }

// ===== Helpers =====

function createId(): string {
  return `${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
}

function detectCategory(file: File): AttachedFileSummary['category'] | null {
  const lowerName = file.name.toLowerCase()
  if (file.type.startsWith('image/') || /\.(png|jpe?g)$/i.test(lowerName)) return 'image'
  if (lowerName.endsWith('.dat')) return 'dat'
  if (lowerName.endsWith('.hea')) return 'hea'
  return null
}

function createEmptySession(): ChatSession {
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
    }],
  }
}

function calculatePairStatus(attachments: PendingAttachment[]): WorkspaceState['composer']['pairStatus'] {
  const hasImage = attachments.some(a => a.summary.category === 'image')
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

function validateAttachments(attachments: PendingAttachment[]): string[] {
  const errors: string[] = []
  const hasImage = attachments.some(a => a.summary.category === 'image')
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

function sortSessions(sessions: ChatSession[]): ChatSession[] {
  return [...sessions].sort(
    (left, right) => Date.parse(right.updatedAt) - Date.parse(left.updatedAt),
  )
}

// ===== Initial State =====

function createInitialState(): WorkspaceState {
  const initialSession = createEmptySession()
  return {
    persisted: {
      sessions: [initialSession],
      activeSessionId: initialSession.id,
      persistenceEnabled: true,
      storageVersion: 1,
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

function workspaceReducer(state: WorkspaceState, action: WorkspaceAction): WorkspaceState {
  switch (action.type) {
    case 'HYDRATE': {
      const sessions = action.sessions.length > 0 ? action.sessions : [createEmptySession()]
      const activeExists = sessions.some(s => s.id === action.activeSessionId)
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
        if (!category) {
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

      // Merge with existing: for dat/hea, replace by category; images replace all
      const existingNonImage = state.composer.attachments.filter(a => a.summary.category !== 'image')
      const hasNewImage = newAttachments.some(a => a.summary.category === 'image')

      let merged: PendingAttachment[]
      const replacedNames: string[] = []
      if (hasNewImage) {
        // New image replaces everything — note any replaced files
        const existingNames = state.composer.attachments.map(a => a.summary.name)
        if (existingNames.length > 0) replacedNames.push(...existingNames)
        const imageAttachment = newAttachments.find(a => a.summary.category === 'image')!
        merged = [imageAttachment]
      } else {
        // Merge dat/hea by category
        const byCategory = new Map(
          existingNonImage.map(a => [a.summary.category, a] as const),
        )
        for (const att of newAttachments) {
          const existing = byCategory.get(att.summary.category)
          if (existing && existing.id !== att.id) replacedNames.push(existing.summary.name)
          byCategory.set(att.summary.category, att)
        }
        merged = Array.from(byCategory.values())
      }

      const pairStatus = calculatePairStatus(merged)
      const validationErrors = [...errors, ...validateAttachments(merged)]

      // Stash replaced names so the hook can toast after dispatch
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
      const pairStatus = calculatePairStatus(attachments)
      const validationErrors = validateAttachments(attachments)
      return {
        ...state,
        composer: { ...state.composer, attachments, pairStatus, validationErrors },
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
      const newSession = createEmptySession()
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
          sessions: state.persisted.sessions.map(s =>
            s.id === action.id ? { ...s, title: action.title, updatedAt: new Date().toISOString() } : s,
          ),
        },
      }
    }

    case 'DELETE_SESSION': {
      const remaining = state.persisted.sessions.filter(s => s.id !== action.id)
      if (remaining.length === 0) {
        const newSession = createEmptySession()
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
      const nextActiveId = isActive
        ? (remaining[0]?.id ?? remaining[0].id)
        : state.persisted.activeSessionId

      return {
        ...state,
        persisted: {
          ...state.persisted,
          sessions: remaining,
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
      const freshSession = createEmptySession()
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
          sessions: state.persisted.sessions.map(s =>
            s.id === action.sessionId
              ? {
                  ...s,
                  messages: [...s.messages, action.message],
                  updatedAt: action.message.createdAt,
                  preview: action.message.content,
                }
              : s,
          ),
        },
      }
    }

    case 'UPDATE_MESSAGE': {
      return {
        ...state,
        persisted: {
          ...state.persisted,
          sessions: state.persisted.sessions.map(s =>
            s.id === action.sessionId
              ? {
                  ...s,
                  messages: s.messages.map(m =>
                    m.id === action.messageId ? { ...m, ...action.updates } : m,
                  ),
                }
              : s,
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

// ===== Hook =====

export function useWorkspaceController() {
  const [state, dispatch] = useReducer(workspaceReducer, null, createInitialState)
  const lastFilesRef = useRef<File[] | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)

  // Hydration
  useEffect(() => {
    try {
      const raw = localStorage.getItem('ecg-persisted')
      if (raw) {
        const parsed = JSON.parse(raw)
        if (parsed.storageVersion === 1 && Array.isArray(parsed.sessions)) {
          dispatch({ type: 'HYDRATE', sessions: parsed.sessions, activeSessionId: parsed.activeSessionId })
        }
      }
    } catch { /* ignore corrupt data */ }
  }, [])

  // Persistence
  useEffect(() => {
    if (state.persisted.persistenceEnabled) {
      try {
        localStorage.setItem('ecg-persisted', JSON.stringify(state.persisted))
      } catch {
        dispatch({ type: 'SET_SIDEBAR_OPEN', open: true })
      }
    }
  }, [state.persisted])

  // Notify when attachments are replaced
  useEffect(() => {
    const names = state.composer.replacedFileNames
    if (names.length > 0) {
      toast(`Replaced: ${names.join(', ')}`, { icon: '🔄' })
      dispatch({ type: 'CLEAR_REPL_FILES' })
    }
  }, [state.composer.replacedFileNames])

  // Derived
  const activeSession = state.persisted.sessions.find(s => s.id === state.persisted.activeSessionId) ?? null
  const isSubmitting = state.submission.phase === 'uploading' || state.submission.phase === 'processing'

  // Submit
  const submit = useCallback(async () => {
    if (!activeSession || isSubmitting) return
    const hasDraft = state.composer.draft.trim().length > 0
    const hasAttachments = state.composer.attachments.length > 0
    if (!hasDraft && !hasAttachments) { toast.error('Add a note or attach an ECG study to continue.'); return }

    // Text-only notes: add guidance message, no API call
    if (!hasAttachments && hasDraft) {
      const userMessage: ConversationMessage = {
        id: createId(),
        role: 'user',
        type: 'prompt',
        title: 'Clinical note',
        content: state.composer.draft.trim(),
        createdAt: new Date().toISOString(),
      }
      const guidanceMessage: ConversationMessage = {
        id: createId(),
        role: 'assistant',
        type: 'guidance',
        content: 'I can keep notes and findings in this workspace, but diagnosis still starts with an ECG upload. Attach a PNG/JPG image or a matched .dat + .hea pair when you are ready.',
        createdAt: new Date().toISOString(),
      }
      dispatch({ type: 'APPEND_MESSAGE', sessionId: activeSession.id, message: userMessage })
      dispatch({ type: 'APPEND_MESSAGE', sessionId: activeSession.id, message: guidanceMessage })
      dispatch({ type: 'CLEAR_COMPOSER' })
      return
    }

    // Validate file combination before submitting
    if (state.composer.validationErrors.length > 0) {
      toast.error(state.composer.validationErrors[0])
      return
    }

    // Add user message FIRST
    const userMessage: ConversationMessage = {
      id: createId(),
      role: 'user',
      type: 'prompt',
      title: state.composer.attachments.length > 0 ? 'Submitted ECG for review' : 'Clinical note',
      content: state.composer.draft.trim() || 'Please analyze the attached ECG study.',
      createdAt: new Date().toISOString(),
      attachments: state.composer.attachments.map(a => a.summary),
    }
    dispatch({ type: 'APPEND_MESSAGE', sessionId: activeSession.id, message: userMessage })

    // Add pending message AFTER user message
    const pendingMessageId = createId()
    const pendingMessage: ConversationMessage = {
      id: pendingMessageId,
      role: 'assistant',
      type: 'diagnosis',
      content: 'Analyzing...',
      createdAt: new Date().toISOString(),
      status: 'pending',
    }
    dispatch({ type: 'APPEND_MESSAGE', sessionId: activeSession.id, message: pendingMessage })
    dispatch({ type: 'SUBMIT_STARTED', messageId: pendingMessageId })

    lastFilesRef.current = state.composer.attachments.map(a => a.file)
    abortControllerRef.current = new AbortController()
    const currentAbortController = abortControllerRef.current

    try {
      const imageFile = state.composer.attachments.find(a => a.summary.category === 'image')?.file
      const datFile = state.composer.attachments.find(a => a.summary.category === 'dat')?.file
      const heaFile = state.composer.attachments.find(a => a.summary.category === 'hea')?.file

      let result: DiagnosisResultData
      if (imageFile) {
        result = await diagnosisApi.diagnoseImage(imageFile, (p) => {
          if (!currentAbortController.signal.aborted) {
            dispatch({ type: 'SUBMIT_UPLOAD_PROGRESS', progress: p })
          }
        }, currentAbortController.signal)
      } else if (datFile && heaFile) {
        result = await diagnosisApi.diagnoseDatPair(datFile, heaFile, (p) => {
          if (!currentAbortController.signal.aborted) {
            dispatch({ type: 'SUBMIT_UPLOAD_PROGRESS', progress: p })
          }
        }, currentAbortController.signal)
      } else {
        throw new Error('Invalid file combination')
      }

      // Upload complete, now processing
      if (!currentAbortController.signal.aborted) {
        dispatch({ type: 'SUBMIT_PROCESSING' })
        dispatch({ type: 'UPDATE_MESSAGE', sessionId: activeSession.id, messageId: pendingMessageId, updates: { status: 'completed', content: 'Analysis complete', result } })
        dispatch({ type: 'SUBMIT_SUCCEEDED', result })
        dispatch({ type: 'CLEAR_COMPOSER' })
        toast.success('Diagnosis complete.')
      }
    } catch (error: unknown) {
      if (currentAbortController.signal.aborted) return // Cancelled, don't show error
      const errorMessage = extractErrorMessage(error)
      dispatch({ type: 'UPDATE_MESSAGE', sessionId: activeSession.id, messageId: pendingMessageId, updates: { status: 'error', errorDetail: errorMessage } })
      dispatch({ type: 'SUBMIT_FAILED', error: errorMessage })
      toast.error(errorMessage)
    }
  }, [activeSession, isSubmitting, state.composer])

  const cancelSubmission = useCallback(() => {
    if (abortControllerRef.current) { abortControllerRef.current.abort(); abortControllerRef.current = null }
    if (state.submission.activeMessageId && activeSession) {
      dispatch({ type: 'UPDATE_MESSAGE', sessionId: activeSession.id, messageId: state.submission.activeMessageId, updates: { status: 'error', errorDetail: 'Analysis cancelled' } })
    }
    dispatch({ type: 'SUBMIT_CANCEL' })
  }, [state.submission.activeMessageId, activeSession])

  const retry = useCallback(async () => {
    if (!lastFilesRef.current || !activeSession) { toast.error('Please re-select files and try again.'); return }
    dispatch({ type: 'ADD_FILES', files: lastFilesRef.current })
    // Re-submit with the stashed files after a tick (let state update first)
    await new Promise(r => setTimeout(r, 0))
    submit()
  }, [activeSession, submit])

  return { state, dispatch, activeSession, isSubmitting, submit, retry, cancelSubmission }
}

export type UseWorkspaceControllerReturn = ReturnType<typeof useWorkspaceController>

// Export helpers for testing
export { createId, detectCategory, createEmptySession, calculatePairStatus, workspaceReducer, createInitialState }
