import { act, renderHook, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { STORAGE_VERSION } from '@/utils/storage'
import { useWorkspaceController } from '@/controllers/useWorkspaceController'
import type { ChatSession } from '@/types/chat'

const {
  authState,
  toastMock,
  listSessionsMock,
  listMessagesMock,
  createSessionMock,
  createMessagesMock,
  updateSessionMock,
  confirmMock,
} = vi.hoisted(() => ({
  authState: {
    user: null as { id: number; email: string; display_name: string | null } | null,
    accessToken: null as string | null,
    isLoading: false,
  },
  toastMock: Object.assign(vi.fn(), {
    error: vi.fn(),
    success: vi.fn(),
  }),
  listSessionsMock: vi.fn(),
  listMessagesMock: vi.fn(),
  createSessionMock: vi.fn(),
  createMessagesMock: vi.fn(),
  updateSessionMock: vi.fn(),
  confirmMock: vi.fn(() => true),
}))

vi.mock('react-hot-toast', () => ({
  default: toastMock,
}))

vi.mock('@/auth/AuthProvider', () => ({
  useAuth: () => ({
    ...authState,
    setAuthenticated: vi.fn(),
    logout: vi.fn(),
  }),
}))

vi.mock('@/api', () => ({
  diagnosisApi: {
    diagnoseImage: vi.fn(),
    diagnoseDatPair: vi.fn(),
  },
}))

vi.mock('@/api/chat', () => ({
  chatApi: {
    listSessions: listSessionsMock,
    listMessages: listMessagesMock,
    createSession: createSessionMock,
    createMessages: createMessagesMock,
    updateSession: updateSessionMock,
    deleteSession: vi.fn(),
    deleteAllSessions: vi.fn(),
    getSession: vi.fn(),
  },
}))

const storageState = new Map<string, string>()

Object.defineProperty(globalThis, 'localStorage', {
  configurable: true,
  value: {
    getItem: vi.fn((key: string) => storageState.get(key) ?? null),
    setItem: vi.fn((key: string, value: string) => {
      storageState.set(key, value)
    }),
    removeItem: vi.fn((key: string) => {
      storageState.delete(key)
    }),
    clear: vi.fn(() => {
      storageState.clear()
    }),
  },
})

function makeLocalSession(): ChatSession {
  const timestamp = '2026-04-06T04:00:00.000Z'
  return {
    id: '550e8400-e29b-41d4-a716-446655440000',
    title: 'Migrated ECG Review',
    preview: 'Submitted ECG for review',
    updatedAt: timestamp,
    messages: [
      {
        id: '660e8400-e29b-41d4-a716-446655440000',
        role: 'assistant',
        type: 'intro',
        content: 'Welcome',
        createdAt: timestamp,
        status: 'completed',
      },
      {
        id: '770e8400-e29b-41d4-a716-446655440000',
        role: 'user',
        type: 'prompt',
        title: 'Submitted ECG for review',
        content: 'Please analyze the attached ECG study.',
        createdAt: timestamp,
        status: 'completed',
      },
    ],
  }
}

function persistLocalSessions(session: ChatSession) {
  localStorage.setItem(
    'ecg-persisted',
    JSON.stringify({
      sessions: [session],
      activeSessionId: session.id,
      persistenceEnabled: true,
      storageVersion: STORAGE_VERSION,
    }),
  )
}

describe('useWorkspaceController login migration', () => {
  beforeEach(() => {
    storageState.clear()
    localStorage.clear()
    vi.mocked(localStorage.getItem).mockClear()
    vi.mocked(localStorage.setItem).mockClear()
    vi.mocked(localStorage.removeItem).mockClear()
    vi.mocked(localStorage.clear).mockClear()
    authState.user = null
    authState.accessToken = null
    authState.isLoading = false
    toastMock.mockReset()
    toastMock.error.mockReset()
    toastMock.success.mockReset()
    listSessionsMock.mockReset()
    listMessagesMock.mockReset()
    createSessionMock.mockReset()
    createMessagesMock.mockReset()
    updateSessionMock.mockReset()
    confirmMock.mockReset()
    confirmMock.mockReturnValue(true)
    vi.stubGlobal('confirm', confirmMock)
  })

  it('syncs local sessions to the cloud on login before hydrating remote state', async () => {
    const session = makeLocalSession()
    persistLocalSessions(session)
    listSessionsMock.mockResolvedValue([])
    createSessionMock.mockResolvedValue({
      id: session.id,
      title: session.title,
      updated_at: session.updatedAt,
    })
    createMessagesMock.mockResolvedValue([])

    const { result, rerender } = renderHook(() => useWorkspaceController())

    await waitFor(() => {
      expect(result.current.activeSession?.title).toBe(session.title)
    })

    act(() => {
      authState.user = {
        id: 1,
        email: 'doctor@example.com',
        display_name: 'Doctor',
      }
      authState.accessToken = 'token'
    })
    rerender()

    await waitFor(() => {
      expect(confirmMock).toHaveBeenCalledTimes(1)
      expect(createSessionMock).toHaveBeenCalledWith(session.id, session.title)
      expect(createMessagesMock).toHaveBeenCalledTimes(1)
      expect(localStorage.removeItem).toHaveBeenCalledWith('ecg-persisted')
    })
  })

  it('keeps local sessions visible when cloud sync fails', async () => {
    const session = makeLocalSession()
    persistLocalSessions(session)
    createSessionMock.mockResolvedValue({
      id: session.id,
      title: session.title,
      updated_at: session.updatedAt,
    })
    createMessagesMock.mockRejectedValue(new Error('sync failed'))

    const { result, rerender } = renderHook(() => useWorkspaceController())

    await waitFor(() => {
      expect(result.current.activeSession?.title).toBe(session.title)
    })

    act(() => {
      authState.user = {
        id: 1,
        email: 'doctor@example.com',
        display_name: 'Doctor',
      }
      authState.accessToken = 'token'
    })
    rerender()

    await waitFor(() => {
      expect(toastMock.error).toHaveBeenCalledWith('本地历史同步失败：sync failed')
    })

    expect(localStorage.removeItem).not.toHaveBeenCalledWith('ecg-persisted')
    expect(result.current.activeSession?.title).toBe(session.title)
  })
})
