export const STORAGE_VERSION = 1

const PERSISTED_KEY = 'ecg-persisted'

interface PersistedState {
  sessions: unknown[]
  activeSessionId: string
  persistenceEnabled: boolean
  storageVersion: number
}

export class StorageManager {
  writePersisted(state: PersistedState): void {
    try {
      localStorage.setItem(PERSISTED_KEY, JSON.stringify(state))
    } catch (error) {
      if (error instanceof Error && error.name === 'QuotaExceededError') {
        throw new Error('QUOTA_EXCEEDED')
      }
      throw error
    }
  }

  readPersisted(): PersistedState | null {
    try {
      const raw = localStorage.getItem(PERSISTED_KEY)
      if (!raw) return null

      const parsed = JSON.parse(raw) as PersistedState

      if (parsed.storageVersion !== STORAGE_VERSION) {
        return null
      }

      return parsed
    } catch {
      return null
    }
  }

  clear(): void {
    localStorage.removeItem(PERSISTED_KEY)
  }

  getSize(): number {
    const raw = localStorage.getItem(PERSISTED_KEY)
    return raw ? new Blob([raw]).size : 0
  }
}
