import { useReducer, useCallback, useRef, useEffect } from 'react'
import toast from 'react-hot-toast'
import { diagnosisApi } from '@/api'
import type { DiagnosisResultData } from '@/api'
import { extractErrorMessage } from '@/api/client'
import { chatApi } from '@/api/chat'
import { useAuth } from '@/auth/AuthProvider'
import type { ChatSession, ConversationMessage } from '@/types/chat'
import { StorageManager } from '@/utils/storage'

// Re-export everything that consumers and tests import
export {
  workspaceReducer,
  createInitialState,
  createEmptySession,
  createId,
  detectCategory,
  calculatePairStatus,
  validateAttachments,
  sortSessions,
  buildSessionPreview,
} from './workspaceReducer'
export type { PendingAttachment, WorkspaceState, WorkspaceAction } from './workspaceReducer'

export {
  normalizeMessageStatus,
  mapRemoteMessage,
  mapLocalMessageToRemote,
  buildSessionFromRemote,
} from './messageMappers'

import { createId, createEmptySession, workspaceReducer, createInitialState } from './workspaceReducer'
import { mapLocalMessageToRemote, fetchAllSessionMessages, buildSessionFromRemote } from './messageMappers'

const storage = new StorageManager()

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

    const fallback = createEmptySession()
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
        const fallback = createEmptySession()
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
      const fallback = createEmptySession()
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
    const newSession = createEmptySession()
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
    const freshSession = createEmptySession()
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
