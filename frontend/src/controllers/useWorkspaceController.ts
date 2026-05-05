import { useReducer, useEffect, useRef } from 'react'
import toast from 'react-hot-toast'
import { useAuth } from '@/auth/AuthProvider'
import { workspaceReducer, createInitialState } from './reducers/index'
import { useSessionManager } from './hooks/useSessionManager'
import { useSubmissionFlow } from './hooks/useSubmissionFlow'
import { useComposer } from './hooks/useComposer'

export {
  workspaceReducer,
  createInitialState,
} from './reducers/index'
export {
  createEmptySession,
  createId,
  detectCategory,
  calculatePairStatus,
  validateAttachments,
  sortSessions,
  buildSessionPreview,
} from './reducers/helpers'
export type { PendingAttachment, WorkspaceState, WorkspaceAction } from './reducers/types'
export {
  normalizeMessageStatus,
  mapRemoteMessage,
  mapLocalMessageToRemote,
  buildSessionFromRemote,
} from './messageMappers'

export function useWorkspaceController() {
  const auth = useAuth()
  const [state, dispatch] = useReducer(workspaceReducer, null, createInitialState)
  const persistedStateRef = useRef(state.persisted)
  const composerRef = useRef(state.composer)

  persistedStateRef.current = state.persisted
  composerRef.current = state.composer

  const {
    createSession,
    switchSession,
    renameSession,
    deleteSession,
    clearAllSessions,
    togglePersistence,
    ensureRemoteSession,
  } = useSessionManager({ state, dispatch, auth, persistedStateRef })

  const activeSession = state.persisted.sessions.find(
    session => session.id === state.persisted.activeSessionId,
  ) ?? null

  const {
    submit,
    retry,
    cancelSubmission,
    isSubmitting,
  } = useSubmissionFlow({
    state,
    dispatch,
    auth,
    activeSession,
    composerRef,
    ensureRemoteSession,
  })

  useComposer({ dispatch })

  useEffect(() => {
    const names = state.composer.replacedFileNames
    if (names.length > 0) {
      toast(`Replaced: ${names.join(', ')}`, { icon: '🔄' })
      dispatch({ type: 'CLEAR_REPL_FILES' })
    }
  }, [state.composer.replacedFileNames])

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
