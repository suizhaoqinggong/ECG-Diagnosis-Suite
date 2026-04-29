import { renderHook, act, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useWorkspaceController } from '@/controllers/useWorkspaceController'

const { toastMock, createJobMock, getJobMock } = vi.hoisted(() => ({
  toastMock: Object.assign(vi.fn(), {
    error: vi.fn(),
    success: vi.fn(),
  }),
  createJobMock: vi.fn(),
  getJobMock: vi.fn(),
}))

vi.mock('react-hot-toast', () => ({
  default: toastMock,
}))

vi.mock('@/auth/AuthProvider', () => ({
  useAuth: () => ({
    user: null,
    accessToken: null,
    isLoading: false,
    setAuthenticated: vi.fn(),
    logout: vi.fn(),
  }),
}))

vi.mock('@/api/health', () => ({
  healthApi: {
    createJob: createJobMock,
    getJob: getJobMock,
  },
}))

vi.mock('@/api/chat', () => ({
  chatApi: {
    createSession: vi.fn(),
    createMessages: vi.fn(),
    deleteSession: vi.fn(),
    updateSession: vi.fn(),
    listSessions: vi.fn().mockResolvedValue([]),
    deleteAllSessions: vi.fn(),
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

describe('useWorkspaceController health flow', () => {
  beforeEach(() => {
    storageState.clear()
    localStorage.clear()
    toastMock.mockReset()
    toastMock.error.mockReset()
    toastMock.success.mockReset()
    createJobMock.mockReset()
    getJobMock.mockReset()
  })

  it('calls healthApi.createJob and polls getJob until completed', async () => {
    const jobResponse = { id: 'job-1', status: 'queued', message: 'Queued' }
    const completedResult = {
      id: 'job-1',
      status: 'completed' as const,
      message: 'Completed',
      result: {
        jobId: 'job-1',
        status: 'completed' as const,
        summary: '关注 LDL 与 ECG 结果',
        overallRisk: 'high' as const,
        findings: [],
        nextSteps: ['尽快门诊复查'],
        limitations: ['仅基于上传资料解释'],
        disclaimer: '本结果仅供参考',
      },
    }

    createJobMock.mockResolvedValueOnce(jobResponse)
    getJobMock
      .mockResolvedValueOnce({ id: 'job-1', status: 'processing', message: 'Processing' })
      .mockResolvedValueOnce(completedResult)

    const { result } = renderHook(() => useWorkspaceController())

    await waitFor(() => {
      expect(result.current.activeSession).not.toBeNull()
    })

    const file = new File(['x'], 'report.pdf', { type: 'application/pdf' })

    act(() => {
      result.current.dispatch({ type: 'ADD_FILES', files: [file] })
    })

    await act(async () => {
      await result.current.submit()
    })

    await waitFor(() => {
      expect(createJobMock).toHaveBeenCalledTimes(1)
      expect(getJobMock).toHaveBeenCalledTimes(2)
      expect(result.current.state.submission.phase).toBe('succeeded')
    })
  })

  it('sets error state when health job fails', async () => {
    const jobResponse = { id: 'job-2', status: 'queued', message: 'Queued' }

    createJobMock.mockResolvedValueOnce(jobResponse)
    getJobMock
      .mockResolvedValueOnce({ id: 'job-2', status: 'processing', message: 'Processing' })
      .mockResolvedValueOnce({ id: 'job-2', status: 'failed', message: 'Failed', error: 'Server error' })

    const { result } = renderHook(() => useWorkspaceController())

    await waitFor(() => {
      expect(result.current.activeSession).not.toBeNull()
    })

    const file = new File(['x'], 'bad.pdf', { type: 'application/pdf' })

    act(() => {
      result.current.dispatch({ type: 'ADD_FILES', files: [file] })
    })

    await act(async () => {
      await result.current.submit()
    })

    await waitFor(() => {
      expect(createJobMock).toHaveBeenCalledTimes(1)
      expect(result.current.state.submission.phase).toBe('failed')
    })
  })
})
