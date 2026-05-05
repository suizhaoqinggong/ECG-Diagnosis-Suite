import type { WorkspaceState, WorkspaceAction } from './types'
import type { PendingAttachment } from './types'
import { createId, detectCategory, calculatePairStatus, validateAttachments } from './helpers'

export function composerReducer(state: WorkspaceState, action: WorkspaceAction): WorkspaceState | null {
  switch (action.type) {
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
        if (category === null) {
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

      const merged = [...state.composer.attachments]
      const replacedNames: string[] = []
      for (const attachment of newAttachments) {
        const category = attachment.summary.category
        const replaceByCategory = category === 'dat' || category === 'hea' || category === 'ecg_image'

        if (replaceByCategory) {
          const existingIndex = merged.findIndex(item => item.summary.category === category)
          if (existingIndex >= 0) {
            replacedNames.push(merged[existingIndex].summary.name)
            merged.splice(existingIndex, 1, attachment)
          } else {
            merged.push(attachment)
          }
          continue
        }

        const existingIndex = merged.findIndex(
          item =>
            item.summary.category === category &&
            item.summary.name === attachment.summary.name,
        )
        if (existingIndex >= 0) {
          replacedNames.push(merged[existingIndex].summary.name)
          merged.splice(existingIndex, 1, attachment)
        } else {
          merged.push(attachment)
        }
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

    case 'CLEAR_REPL_FILES': {
      return {
        ...state,
        composer: { ...state.composer, replacedFileNames: [] },
      }
    }

    default:
      return null
  }
}
