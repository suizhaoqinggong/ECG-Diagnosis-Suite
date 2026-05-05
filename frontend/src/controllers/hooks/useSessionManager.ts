import { useCallback, useEffect, useRef } from 'react'
import toast from 'react-hot-toast'
import { extractErrorMessage } from '@/api/client'
import { chatApi } from '@/api/chat'
import type { ChatSession } from '@/types/chat'
import { StorageManager } from '@/utils/storage'
import {
  createEmptySession,
} from '../reducers/helpers'
import type { WorkspaceState, WorkspaceAction } from '../reducers/types'
import { mapLocalMessageToRemote, fetchAllSessionMessages, buildSessionFromRemote } from '../messageMappers'

interface AuthLike {
  isLoading: boolean
  user?: { id: number } | null
}

const storage = new StorageManager()

interface SessionManagerDeps {
  state: WorkspaceState
  dispatch: React.Dispatch<WorkspaceAction>
  auth: AuthLike
  persistedStateRef: React.MutableRefObject<WorkspaceState['persisted']>
}

function getErrorStatusCode(error: unknown): number | null {
  if (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof (error as { response?: { status?: unknown } }).response?.status === 'number'
  ) {
    return (error as { response: { status: number } }).response.status
  }
  return null
}

function hasMeaningfulSession(session: ChatSession): boolean {
  return session.messages.some((message) => message.type !== 'intro')
}

function getLocalMigrationSource(
  sessions: ChatSession[],
  activeSessionId: string,
): { sessions: ChatSession[]; activeSessionId: string } | null {
  const currentSessions = sessions.filter(hasMeaningfulSession)
  if (currentSessions.length > 0) {
    return {
      sessions: currentSessions,
      activeSessionId: currentSessions.some((session) => session.id === activeSessionId)
        ? activeSessionId
        : currentSessions[0].id,
    }
  }

  const persisted = storage.readPersisted()
  if (
    persisted &&
    persisted.persistenceEnabled &&
    Array.isArray(persisted.sessions)
  ) {
    const persistedSessions = (persisted.sessions as ChatSession[]).filter(hasMeaningfulSession)
    if (persistedSessions.length > 0) {
      return {
        sessions: persistedSessions,
        activeSessionId: persistedSessions.some((session) => session.id === persisted.activeSessionId)
          ? persisted.activeSessionId
          : persistedSessions[0].id,
      }
    }
  }

  return null
}

export function useSessionManager({ state, dispatch, auth, persistedStateRef }: SessionManagerDeps) {
  const remoteSessionIdsRef = useRef<Set<string>>(new Set())
  const hydratedUserIdRef = useRef<number | null>(null)

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
  }, [dispatch])

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
  }, [dispatch])

  const syncSessionToCloud = useCallback(async (session: ChatSession) => {
    try {
      await chatApi.createSession(session.id, session.title)
    } catch (error) {
      if (getErrorStatusCode(error) !== 409) {
        throw error
      }
      await chatApi.updateSession(session.id, session.title)
    }

    if (session.messages.length > 0) {
      await chatApi.createMessages(
        session.id,
        session.messages.map(mapLocalMessageToRemote),
      )
    }

    remoteSessionIdsRef.current.add(session.id)
  }, [])

  useEffect(() => {
    if (auth.isLoading) return

    if (auth.user?.id) {
      if (hydratedUserIdRef.current === auth.user.id) return
      hydratedUserIdRef.current = auth.user.id

      void (async () => {
        const migrationSource = getLocalMigrationSource(
          persistedStateRef.current.sessions,
          persistedStateRef.current.activeSessionId,
        )

        if (migrationSource) {
          const sessionCount = migrationSource.sessions.length
          const shouldSync = typeof window === 'undefined'
            ? true
            : window.confirm(
              `发现 ${sessionCount} 个本地对话，同步到云端？`,
            )

          if (shouldSync) {
            try {
              for (const session of migrationSource.sessions) {
                await syncSessionToCloud(session)
              }
              storage.clear()
            } catch (error) {
              toast.error(`本地历史同步失败：${extractErrorMessage(error)}`)
              if (!persistedStateRef.current.sessions.some(hasMeaningfulSession)) {
                dispatch({
                  type: 'HYDRATE',
                  sessions: migrationSource.sessions,
                  activeSessionId: migrationSource.activeSessionId,
                })
              }
              return
            }
          } else {
            storage.clear()
          }
        } else {
          storage.clear()
        }

        await loadRemoteSessions()
      })()
      return
    }

    hydratedUserIdRef.current = null
    remoteSessionIdsRef.current = new Set()
    loadGuestSessions()
  }, [
    auth.isLoading,
    auth.user?.id,
    loadGuestSessions,
    loadRemoteSessions,
    syncSessionToCloud,
    dispatch,
    persistedStateRef,
  ])

  useEffect(() => {
    if (auth.user || auth.isLoading) return

    if (!state.persisted.persistenceEnabled) {
      storage.clear()
      return
    }

    try {
      storage.writePersisted(state.persisted)
    } catch {
      toast.error('本地存储已满，无法保存历史记录')
    }
  }, [auth.isLoading, auth.user, state.persisted])

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
  }, [auth.user, dispatch, ensureRemoteSession])

  const switchSession = useCallback((id: string) => {
    dispatch({ type: 'SWITCH_SESSION', id })
  }, [dispatch])

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
  }, [auth.user, dispatch, ensureRemoteSession, loadRemoteSessions, state.persisted.sessions])

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
  }, [auth.user, dispatch, loadRemoteSessions])

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
  }, [auth.user, dispatch, loadRemoteSessions])

  const togglePersistence = useCallback(() => {
    const willEnable = !state.persisted.persistenceEnabled
    dispatch({ type: 'TOGGLE_PERSISTENCE' })
    if (!willEnable) {
      storage.clear()
    }
  }, [state.persisted.persistenceEnabled, dispatch])

  return {
    createSession,
    switchSession,
    renameSession,
    deleteSession,
    clearAllSessions,
    togglePersistence,
    ensureRemoteSession,
    remoteSessionIdsRef,
  }
}
