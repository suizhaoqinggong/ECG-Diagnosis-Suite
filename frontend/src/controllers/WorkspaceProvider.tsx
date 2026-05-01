import { createContext, useContext, type ReactNode } from 'react'
import { useWorkspaceController } from './useWorkspaceController'

type WorkspaceContextValue = ReturnType<typeof useWorkspaceController>

const WorkspaceContext = createContext<WorkspaceContextValue | null>(null)

export function WorkspaceProvider({ children }: { children: ReactNode }) {
  const controller = useWorkspaceController()
  return (
    <WorkspaceContext.Provider value={controller}>
      {children}
    </WorkspaceContext.Provider>
  )
}

/**
 * Access the shared workspace controller. Must be used inside <WorkspaceProvider>.
 *
 * Why a Context wrapper: the underlying useWorkspaceController() owns
 * useReducer state, hydration effects, and abort controller refs. If two
 * components both call the hook directly, they get two independent state
 * machines (HomePage's session list never reflects MyReportsPage's renames,
 * for example). Calling the hook once at the top level and propagating the
 * value via Context keeps every page rendered under the provider in sync.
 */
export function useWorkspace(): WorkspaceContextValue {
  const ctx = useContext(WorkspaceContext)
  if (ctx === null) {
    throw new Error('useWorkspace must be used inside <WorkspaceProvider>')
  }
  return ctx
}
