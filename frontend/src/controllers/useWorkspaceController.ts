import { useReducer, useCallback, useRef, useEffect } from 'react'
import toast from 'react-hot-toast'
import { diagnosisApi } from '@/api'
import type { DiagnosisResultData } from '@/api'
import { extractErrorMessage } from '@/api/client'
import { chatApi, type MessageCreate, type MessageResponse, type SessionResponse } from '@/api/chat'
import { useAuth } from '@/auth/AuthProvider'
import type { ChatSession, ConversationMessage, AttachedFileSummary } from '@/types/chat'
import { STORAGE_VERSION, StorageManager } from '@/utils/storage'

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
  | { type: 'CREATE_SESSION'; session?: ChatSession }
  | { type: 'SWITCH_SESSION'; id: string }
  | { type: 'RENAME_SESSION'; id: string; title: string }
  | { type: 'DELETE_SESSION'; id: string }
  | { type: 'CLEAR_ALL_SESSIONS'; session?: ChatSession }
  | { type: 'TOGGLE_PERSISTENCE' }
  | { type: 'APPEND_MESSAGE'; sessionId: string; message: ConversationMessage }
  | { type: 'UPDATE_MESSAGE'; sessionId: string; messageId: string; updates: Partial<ConversationMessage> }
  | { type: 'CLEAR_REPL_FILES' }

const storage = new StorageManager()

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
  if (file.type.startsWith('image/') || /\.(png|jpe?g)$/i.test(lowerName)) return 'image'
  if (lowerName.endsWith('.dat')) return 'dat'
  if (lowerName.endsWith('.hea')) return 'hea'
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

function buildSessionPreview(messages: ConversationMessage[]): string {
  const candidate = [...messages]
    .reverse()
    .find(message => message.type !== 'intro' && message.content.trim().length > 0)

  if (candidate) {
    return candidate.title?.trim() || candidate.content.trim()
  }

  return 'Start with an ECG file or a clinical note.'
}

function normalizeMessageStatus(value?: string): ConversationMessage['status'] {
  if (value === 'pending' || value === 'completed' || value === 'error') return value
  return undefined
}

function mapRemoteMessage(message: MessageResponse): ConversationMessage {
  const content = message.content || ''
  const attachmentPayload = message.attachments as { items?: AttachedFileSummary[] } | null
  return {
    id: message.id,
    role: message.role === 'assistant' ? 'assistant' : 'user',
    type:
      message.type === 'intro' ||
      message.type === 'prompt' ||
      message.type === 'guidance' ||
      message.type === 'diagnosis'
        ? message.type
        : 'prompt',
    content,
    createdAt: message.created_at,
    attachments: Array.isArray(attachmentPayload?.items)
      ? attachmentPayload.items
      : undefined,
    result: (message.result as DiagnosisResultData | null) ?? undefined,
    status: normalizeMessageStatus(message.status) ?? 'completed',
  }
}

function buildSessionFromRemote(
  session: SessionResponse,
  messages: MessageResponse[],
): ChatSession {
  const mappedMessages = messages.map(mapRemoteMessage)
  const finalMessages = mappedMessages.length > 0 ? mappedMessages : createEmptySession().messages

  return {
    id: session.id,
    title: session.title,
    updatedAt: session.updated_at,
    messages: finalMessages,
    preview: buildSessionPreview(finalMessages),
  }
}

function mapLocalMessageToRemote(message: ConversationMessage): MessageCreate {
  return {
    id: message.id,
    role: message.role,
    type: message.type,
    content: message.content,
    attachments: message.attachments ? { items: message.attachments } : null,
    result: (message.result as Record<string, unknown> | null | undefined) ?? null,
    result_schema_version: message.result ? 1 : null,
    status: message.status ?? 'completed',
  }
}

async function fetchAllSessionMessages(sessionId: string): Promise<MessageResponse[]> {
  const messages: MessageResponse[] = []
  let cursor: string | undefined

  while (true) {
    const page = await chatApi.listMessages(sessionId, cursor, 100)
    messages.push(...page)
    if (page.length < 100) break
    const last = page[page.length - 1]
    cursor = `${last.created_at},${last.id}`
  }

  return messages
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

      const existingNonImage = state.composer.attachments.filter(a => a.summary.category !== 'image')
      const hasNewImage = newAttachments.some(a => a.summary.category === 'image')

      let merged: PendingAttachment[]
      const replacedNames: string[] = []
      if (hasNewImage) {
        const existingNames = state.composer.attachments.map(a => a.summary.name)
        if (existingNames.length > 0) replacedNames.push(...existingNames)
        const imageAttachment = newAttachments.find(a => a.summary.category === 'image')!
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

// ===== Hook =====

export function useWorkspaceController() {
  const auth = useAuth()
  const [state, dispatch] = useReducer(workspaceReducer, null, createInitialState)
  const lastFilesRef = useRef<File[] | null>(null)
  const abortControllerRef = useRef<AbortController | null>(null)
  const remoteSessionIdsRef = useRef<Set<string>>(new Set())

  const loadGuestSessions = useCallback(() => {
    const persisted = storage.readPersisted()
    if (persisted && Array.isArray(persisted.sessions)) {
      dispatch({
        type: 'HYDRATE',
        sessions: persisted.sessions as ChatSession[],
        activeSessionId: persisted.activeSessionId,
      })
      return
    }

    const fallback = cloneEmptySession()
    dispatch({ type: 'HYDRATE', sessions: [fallback], activeSessionId: fallback.id })
  }, [])

  const loadRemoteSessions = useCallback(async () => {
    try {
      const sessions = await chatApi.listSessions()
      const remoteSessions = await Promise.all(
        sessions.map(async (session) => {
          const messages = await fetchAllSessionMessages(session.id)
          return buildSessionFromRemote(session, messages)
        }),
      )

      remoteSessionIdsRef.current = new Set(sessions.map(session => session.id))

      if (remoteSessions.length === 0) {
        const fallback = cloneEmptySession()
        dispatch({ type: 'HYDRATE', sessions: [fallback], activeSessionId: fallback.id })
        return
      }

      dispatch({
        type: 'HYDRATE',
        sessions: remoteSessions,
        activeSessionId: remoteSessions[0].id,
      })
    } catch (error) {
      remoteSessionIdsRef.current = new Set()
      toast.error(extractErrorMessage(error))
      const fallback = cloneEmptySession()
      dispatch({ type: 'HYDRATE', sessions: [fallback], activeSessionId: fallback.id })
    }
  }, [])

  useEffect(() => {
    if (auth.isLoading) return
    if (auth.user) {
      void loadRemoteSessions()
      return
    }
    remoteSessionIdsRef.current = new Set()
    loadGuestSessions()
  }, [auth.isLoading, auth.user, loadGuestSessions, loadRemoteSessions])

  useEffect(() => {
    if (auth.user || auth.isLoading) return

    if (!state.persisted.persistenceEnabled) {
      storage.clear()
      return
    }

    try {
      storage.writePersisted(state.persisted)
    } catch {
      dispatch({ type: 'SET_SIDEBAR_OPEN', open: true })
    }
  }, [auth.isLoading, auth.user, state.persisted])

  useEffect(() => {
    const names = state.composer.replacedFileNames
    if (names.length > 0) {
      toast(`Replaced: ${names.join(', ')}`, { icon: '🔄' })
      dispatch({ type: 'CLEAR_REPL_FILES' })
    }
  }, [state.composer.replacedFileNames])

  const activeSession = state.persisted.sessions.find(
    session => session.id === state.persisted.activeSessionId,
  ) ?? null
  const isSubmitting = state.submission.phase === 'uploading' || state.submission.phase === 'processing'

  const ensureRemoteSession = useCallback(async (session: ChatSession) => {
    if (!auth.user || remoteSessionIdsRef.current.has(session.id)) return

    await chatApi.createSession(session.id, session.title)
    if (session.messages.length > 0) {
      await chatApi.createMessages(
        session.id,
        session.messages.map(mapLocalMessageToRemote),
      )
    }
    remoteSessionIdsRef.current.add(session.id)
  }, [auth.user])

  const createSession = useCallback(async () => {
    const newSession = cloneEmptySession()
    dispatch({ type: 'CREATE_SESSION', session: newSession })

    if (!auth.user) return

    try {
      await ensureRemoteSession(newSession)
    } catch (error) {
      toast.error(extractErrorMessage(error))
    }
  }, [auth.user, ensureRemoteSession])

  const switchSession = useCallback((id: string) => {
    dispatch({ type: 'SWITCH_SESSION', id })
  }, [])

  const renameSession = useCallback(async (id: string, title: string) => {
    dispatch({ type: 'RENAME_SESSION', id, title })

    if (!auth.user) return

    try {
      if (!remoteSessionIdsRef.current.has(id)) {
        const session = state.persisted.sessions.find(item => item.id === id)
        if (session) {
          await ensureRemoteSession({ ...session, title })
          return
        }
      }
      await chatApi.updateSession(id, title)
    } catch (error) {
      toast.error(extractErrorMessage(error))
      void loadRemoteSessions()
    }
  }, [auth.user, ensureRemoteSession, loadRemoteSessions, state.persisted.sessions])

  const deleteSession = useCallback(async (id: string) => {
    dispatch({ type: 'DELETE_SESSION', id })

    if (!auth.user || !remoteSessionIdsRef.current.has(id)) return

    try {
      await chatApi.deleteSession(id)
      remoteSessionIdsRef.current.delete(id)
    } catch (error) {
      toast.error(extractErrorMessage(error))
      void loadRemoteSessions()
    }
  }, [auth.user, loadRemoteSessions])

  const clearAllSessions = useCallback(async () => {
    const freshSession = cloneEmptySession()
    dispatch({ type: 'CLEAR_ALL_SESSIONS', session: freshSession })

    if (!auth.user) return

    try {
      await chatApi.deleteAllSessions()
      remoteSessionIdsRef.current = new Set()
    } catch (error) {
      toast.error(extractErrorMessage(error))
      void loadRemoteSessions()
    }
  }, [auth.user, loadRemoteSessions])

  const togglePersistence = useCallback(() => {
    const willEnable = !state.persisted.persistenceEnabled
    dispatch({ type: 'TOGGLE_PERSISTENCE' })
    if (!willEnable) {
      storage.clear()
    }
  }, [state.persisted.persistenceEnabled])

  const submit = useCallback(async () => {
    if (!activeSession || isSubmitting) return
    const hasDraft = state.composer.draft.trim().length > 0
    const hasAttachments = state.composer.attachments.length > 0
    if (!hasDraft && !hasAttachments) {
      toast.error('Add a note or attach an ECG study to continue.')
      return
    }

    if (!hasAttachments && hasDraft) {
      const userMessage: ConversationMessage = {
        id: createId(),
        role: 'user',
        type: 'prompt',
        title: 'Clinical note',
        content: state.composer.draft.trim(),
        createdAt: new Date().toISOString(),
        status: 'completed',
      }
      const guidanceMessage: ConversationMessage = {
        id: createId(),
        role: 'assistant',
        type: 'guidance',
        content: 'I can keep notes and findings in this workspace, but diagnosis still starts with an ECG upload. Attach a PNG/JPG image or a matched .dat + .hea pair when you are ready.',
        createdAt: new Date().toISOString(),
        status: 'completed',
      }
      dispatch({ type: 'APPEND_MESSAGE', sessionId: activeSession.id, message: userMessage })
      dispatch({ type: 'APPEND_MESSAGE', sessionId: activeSession.id, message: guidanceMessage })
      dispatch({ type: 'CLEAR_COMPOSER' })

      if (auth.user) {
        try {
          await ensureRemoteSession(activeSession)
          await chatApi.createMessages(activeSession.id, [
            mapLocalMessageToRemote(userMessage),
            mapLocalMessageToRemote(guidanceMessage),
          ])
        } catch (error) {
          toast.error(extractErrorMessage(error))
        }
      }
      return
    }

    if (state.composer.validationErrors.length > 0) {
      toast.error(state.composer.validationErrors[0])
      return
    }

    const userMessage: ConversationMessage = {
      id: createId(),
      role: 'user',
      type: 'prompt',
      title: state.composer.attachments.length > 0 ? 'Submitted ECG for review' : 'Clinical note',
      content: state.composer.draft.trim() || 'Please analyze the attached ECG study.',
      createdAt: new Date().toISOString(),
      attachments: state.composer.attachments.map(attachment => attachment.summary),
      status: 'completed',
    }
    dispatch({ type: 'APPEND_MESSAGE', sessionId: activeSession.id, message: userMessage })

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

    lastFilesRef.current = state.composer.attachments.map(attachment => attachment.file)
    abortControllerRef.current = new AbortController()
    const currentAbortController = abortControllerRef.current

    try {
      if (auth.user) {
        await ensureRemoteSession(activeSession)
        await chatApi.createMessages(activeSession.id, [mapLocalMessageToRemote(userMessage)])
      }

      const imageFile = state.composer.attachments.find(attachment => attachment.summary.category === 'image')?.file
      const datFile = state.composer.attachments.find(attachment => attachment.summary.category === 'dat')?.file
      const heaFile = state.composer.attachments.find(attachment => attachment.summary.category === 'hea')?.file

      let result: DiagnosisResultData
      if (imageFile) {
        result = await diagnosisApi.diagnoseImage(
          imageFile,
          progress => {
            if (!currentAbortController.signal.aborted) {
              dispatch({ type: 'SUBMIT_UPLOAD_PROGRESS', progress })
            }
          },
          currentAbortController.signal,
        )
      } else if (datFile && heaFile) {
        result = await diagnosisApi.diagnoseDatPair(
          datFile,
          heaFile,
          progress => {
            if (!currentAbortController.signal.aborted) {
              dispatch({ type: 'SUBMIT_UPLOAD_PROGRESS', progress })
            }
          },
          currentAbortController.signal,
        )
      } else {
        throw new Error('Invalid file combination')
      }

      if (!currentAbortController.signal.aborted) {
        const completedMessage: Partial<ConversationMessage> = {
          status: 'completed',
          content: 'Analysis complete',
          result,
        }
        dispatch({ type: 'SUBMIT_PROCESSING' })
        dispatch({
          type: 'UPDATE_MESSAGE',
          sessionId: activeSession.id,
          messageId: pendingMessageId,
          updates: completedMessage,
        })
        dispatch({ type: 'SUBMIT_SUCCEEDED', result })
        dispatch({ type: 'CLEAR_COMPOSER' })

        if (auth.user) {
          const remoteDiagnosisMessage: ConversationMessage = {
            ...pendingMessage,
            ...completedMessage,
            status: 'completed',
            result,
          }
          await chatApi.createMessages(
            activeSession.id,
            [mapLocalMessageToRemote(remoteDiagnosisMessage)],
          )
        }

        toast.success('Diagnosis complete.')
      }
    } catch (error: unknown) {
      if (currentAbortController.signal.aborted) return
      const errorMessage = extractErrorMessage(error)
      dispatch({
        type: 'UPDATE_MESSAGE',
        sessionId: activeSession.id,
        messageId: pendingMessageId,
        updates: { status: 'error', errorDetail: errorMessage, content: 'Analysis failed' },
      })
      dispatch({ type: 'SUBMIT_FAILED', error: errorMessage })

      if (auth.user) {
        try {
          const remoteErrorMessage: ConversationMessage = {
            ...pendingMessage,
            content: 'Analysis failed',
            status: 'error',
            errorDetail: errorMessage,
          }
          await chatApi.createMessages(
            activeSession.id,
            [mapLocalMessageToRemote(remoteErrorMessage)],
          )
        } catch {
          // Keep the original diagnosis error as the user-facing message.
        }
      }

      toast.error(errorMessage)
    }
  }, [activeSession, auth.user, ensureRemoteSession, isSubmitting, state.composer])

  const cancelSubmission = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
    }
    if (state.submission.activeMessageId && activeSession) {
      dispatch({
        type: 'UPDATE_MESSAGE',
        sessionId: activeSession.id,
        messageId: state.submission.activeMessageId,
        updates: { status: 'error', errorDetail: 'Analysis cancelled', content: 'Analysis cancelled' },
      })
    }
    dispatch({ type: 'SUBMIT_CANCEL' })
  }, [activeSession, state.submission.activeMessageId])

  const retry = useCallback(async () => {
    if (!lastFilesRef.current || !activeSession) {
      toast.error('Please re-select files and try again.')
      return
    }
    dispatch({ type: 'ADD_FILES', files: lastFilesRef.current })
    await new Promise(resolve => setTimeout(resolve, 0))
    await submit()
  }, [activeSession, submit])

  return {
    state,
    dispatch,
    activeSession,
    isSubmitting,
    submit,
    retry,
    cancelSubmission,
    createSession,
    switchSession,
    renameSession,
    deleteSession,
    clearAllSessions,
    togglePersistence,
  }
}
