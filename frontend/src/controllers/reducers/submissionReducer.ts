import type { WorkspaceState, WorkspaceAction } from './types'

export function submissionReducer(state: WorkspaceState, action: WorkspaceAction): WorkspaceState | null {
  switch (action.type) {
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

    default:
      return null
  }
}
