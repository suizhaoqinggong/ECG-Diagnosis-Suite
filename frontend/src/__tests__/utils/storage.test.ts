import { describe, it, expect, beforeEach, vi } from 'vitest'
import { StorageManager, STORAGE_VERSION } from '@/utils/storage'

class LocalStorageMock {
  private store: Map<string, string> = new Map()

  getItem(key: string): string | null {
    return this.store.get(key) ?? null
  }

  setItem(key: string, value: string): void {
    this.store.set(key, value)
  }

  removeItem(key: string): void {
    this.store.delete(key)
  }

  clear(): void {
    this.store.clear()
  }

  get length(): number {
    return this.store.size
  }

  key(_index: number): string | null {
    return null
  }
}

describe('StorageManager', () => {
  let storage: StorageManager
  let mockLocalStorage: LocalStorageMock

  beforeEach(() => {
    mockLocalStorage = new LocalStorageMock()
    vi.stubGlobal('localStorage', mockLocalStorage)
    storage = new StorageManager()
  })

  it('writes and reads persisted state', () => {
    const state = {
      sessions: [],
      activeSessionId: 'test-id',
      persistenceEnabled: true,
      storageVersion: STORAGE_VERSION,
    }
    storage.writePersisted(state)
    expect(storage.readPersisted()).toEqual(state)
  })

  it('returns null when version mismatch', () => {
    mockLocalStorage.setItem('ecg-persisted', JSON.stringify({
      sessions: [],
      activeSessionId: 'test',
      persistenceEnabled: true,
      storageVersion: 0,
    }))
    expect(storage.readPersisted()).toBeNull()
  })

  it('handles QuotaExceededError', () => {
    const originalSetItem = mockLocalStorage.setItem.bind(mockLocalStorage)
    mockLocalStorage.setItem = () => {
      const error = new Error('Quota exceeded')
      error.name = 'QuotaExceededError'
      throw error
    }

    const state = {
      sessions: [],
      activeSessionId: 'test',
      persistenceEnabled: true,
      storageVersion: STORAGE_VERSION,
    }

    expect(() => storage.writePersisted(state)).toThrow('QUOTA_EXCEEDED')

    mockLocalStorage.setItem = originalSetItem
  })

  it('calculates storage size', () => {
    const state = {
      sessions: [{ id: 'test', title: 'Test Session' }],
      activeSessionId: 'test',
      persistenceEnabled: true,
      storageVersion: STORAGE_VERSION,
    }
    storage.writePersisted(state)
    const size = storage.getSize()
    expect(size).toBeGreaterThan(0)
  })
})
