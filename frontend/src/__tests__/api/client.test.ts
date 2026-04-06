import type { AxiosResponse, InternalAxiosRequestConfig } from 'axios'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

const { clearAuthMock, getTokenMock, setAuthMock, refreshMock } = vi.hoisted(() => ({
  clearAuthMock: vi.fn(),
  getTokenMock: vi.fn(() => 'token'),
  setAuthMock: vi.fn(),
  refreshMock: vi.fn(),
}))

vi.mock('@/auth/store', () => ({
  getToken: getTokenMock,
  setAuth: setAuthMock,
  clearAuth: clearAuthMock,
}))

vi.mock('@/auth/api', () => ({
  refresh: refreshMock,
}))

function makeAxiosResponse(
  config: InternalAxiosRequestConfig,
): AxiosResponse<Record<string, never>> {
  return {
    data: {},
    status: 200,
    statusText: 'OK',
    headers: {},
    config,
  }
}

describe('apiClient auth refresh handling', () => {
  beforeEach(() => {
    vi.resetModules()
    clearAuthMock.mockReset()
    getTokenMock.mockReset()
    getTokenMock.mockReturnValue('token')
    setAuthMock.mockReset()
    refreshMock.mockReset()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('rejects the original request when token refresh fails', async () => {
    refreshMock.mockRejectedValueOnce(new Error('refresh failed'))

    const { default: apiClient } = await import('@/api/client')
    const rejected = apiClient.interceptors.response.handlers[0]?.rejected
    expect(rejected).toBeTypeOf('function')

    const adapter = vi.fn(async (config: InternalAxiosRequestConfig) => makeAxiosResponse(config))
    apiClient.defaults.adapter = adapter

    const error = {
      config: {
        url: '/api/chat/sessions',
        headers: {},
      } as InternalAxiosRequestConfig & { _retry?: boolean },
      response: { status: 401 },
    }

    await expect(rejected?.(error)).rejects.toBe(error)
    expect(refreshMock).toHaveBeenCalledTimes(1)
    expect(clearAuthMock).toHaveBeenCalledTimes(1)
    expect(adapter).not.toHaveBeenCalled()
  })

  it('retries the original request after a successful refresh', async () => {
    refreshMock.mockResolvedValueOnce({
      access_token: 'new-token',
      user: { id: 1, email: 'test@example.com', display_name: 'Tester' },
    })

    const { default: apiClient } = await import('@/api/client')
    const rejected = apiClient.interceptors.response.handlers[0]?.rejected
    expect(rejected).toBeTypeOf('function')

    const adapter = vi.fn(async (config: InternalAxiosRequestConfig) => makeAxiosResponse(config))
    apiClient.defaults.adapter = adapter

    const error = {
      config: {
        url: '/api/chat/sessions',
        headers: {},
      } as InternalAxiosRequestConfig & { _retry?: boolean },
      response: { status: 401 },
    }

    const response = await rejected?.(error)

    expect(refreshMock).toHaveBeenCalledTimes(1)
    expect(setAuthMock).toHaveBeenCalledWith(
      { id: 1, email: 'test@example.com', display_name: 'Tester' },
      'new-token',
    )
    expect(adapter).toHaveBeenCalledTimes(1)
    expect(response?.status).toBe(200)
  })
})
