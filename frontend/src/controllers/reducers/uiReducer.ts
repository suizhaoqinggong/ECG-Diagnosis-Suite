import type { WorkspaceState, WorkspaceAction } from './types'

export function uiReducer(state: WorkspaceState, action: WorkspaceAction): WorkspaceState | null {
  switch (action.type) {
    case 'SET_DRAG_ACTIVE': {
      return {
        ...state,
        ui: { ...state.ui, isDragging: action.active },
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

    default:
      return null
  }
}
