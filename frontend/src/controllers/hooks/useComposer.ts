import { useCallback } from 'react'
import type { WorkspaceAction } from '../reducers/types'

interface ComposerDeps {
  dispatch: React.Dispatch<WorkspaceAction>
}

export function useComposer({ dispatch }: ComposerDeps) {
  const setDraft = useCallback(
    (value: string) => dispatch({ type: 'SET_DRAFT', value }),
    [dispatch],
  )

  const addFiles = useCallback(
    (files: File[] | null) => {
      if (files) dispatch({ type: 'ADD_FILES', files })
    },
    [dispatch],
  )

  const removeFile = useCallback(
    (id: string) => dispatch({ type: 'REMOVE_FILE', id }),
    [dispatch],
  )

  return { setDraft, addFiles, removeFile }
}
