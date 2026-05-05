import type { WorkspaceState, WorkspaceAction } from './types'
import { sessionReducer } from './sessionReducer'
import { composerReducer } from './composerReducer'
import { submissionReducer } from './submissionReducer'
import { uiReducer } from './uiReducer'

export { createInitialState } from './helpers'

export function workspaceReducer(state: WorkspaceState, action: WorkspaceAction): WorkspaceState {
  const result =
    sessionReducer(state, action) ??
    composerReducer(state, action) ??
    submissionReducer(state, action) ??
    uiReducer(state, action)

  if (result !== null) return result
  return state
}
