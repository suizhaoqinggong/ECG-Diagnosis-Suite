import { renderHook, act, waitFor } from '@testing-library/react'
import { beforeEach, describe, expect, it, vi } from 'vitest'

import { useWorkspaceController } from '@/controllers/useWorkspaceController'

const { toastMock, diagnoseImageMock, diagnoseDatPairMock } = vi.hoisted(() => ({
  toastMock: Object.assign(vi.fn(), {
    error: vi.fn(),
    success: vi.fn(),
  }),
  diagnoseImageMock: vi.fn(),
  diagnoseDatPairMock: vi.fn(),
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

vi.mock('@/api', () => ({
  diagnosisApi: {
    diagnoseImage: diagnoseImageMock,
    diagnoseDatPair: diagnoseDatPairMock,
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

describe('useWorkspaceController retry', () => {
  beforeEach(() => {
    storageState.clear()
    localStorage.clear()
    toastMock.mockReset()
    toastMock.error.mockReset()
    toastMock.success.mockReset()
    diagnoseImageMock.mockReset()
    diagnoseDatPairMock.mockReset()
  })

  it('retries with the last uploaded file even after composer attachments are cleared', async () => {
    const resultData = {
      prediction: '正常',
      confidence: 0.91,
      timestamp: new Date().toISOString(),
      disclaimer: 'Test only',
      report: {
        source: 'template' as const,
        summary: 'Test summary',
        clinical_interpretation: 'Test interpretation',
        key_findings: [],
        recommendations: [],
        follow_up: [],
        limitations: [],
      },
    }

    diagnoseImageMock
      .mockRejectedValueOnce(new Error('Network error'))
      .mockResolvedValueOnce(resultData)

    const { result } = renderHook(() => useWorkspaceController())

    await waitFor(() => {
      expect(result.current.activeSession).not.toBeNull()
    })

    const file = new File(['ecg'], 'retry.png', { type: 'image/png' })

    act(() => {
      result.current.dispatch({ type: 'ADD_FILES', files: [file] })
    })

    await act(async () => {
      await result.current.submit()
    })

    await waitFor(() => {
      expect(diagnoseImageMock).toHaveBeenCalledTimes(1)
      expect(result.current.state.submission.canRetry).toBe(true)
    })

    act(() => {
      result.current.dispatch({ type: 'CLEAR_COMPOSER' })
    })

    await act(async () => {
      await result.current.retry()
    })

    await waitFor(() => {
      expect(diagnoseImageMock).toHaveBeenCalledTimes(2)
      expect(diagnoseImageMock).toHaveBeenLastCalledWith(
        file,
        expect.any(Function),
        expect.any(AbortSignal),
      )
      expect(result.current.state.submission.canRetry).toBe(false)
    })
  })
})
