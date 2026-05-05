import type { WorkspaceState, WorkspaceAction } from './types'
import { sortSessions, createEmptySession, buildSessionPreview } from './helpers'

function cloneEmptySession() {
  return createEmptySession()
}

export function sessionReducer(state: WorkspaceState, action: WorkspaceAction): WorkspaceState | null {
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

    default:
      return null
  }
}
