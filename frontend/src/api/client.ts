import axios from 'axios'
import { getToken } from '@/auth/store'
import * as authApi from '@/auth/api'
import { setAuth, clearAuth } from '@/auth/store'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || ''

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
})

// Request interceptor: add auth header
apiClient.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  // Add withCredentials for auth endpoints
  if (config.url?.startsWith('/api/auth')) {
    config.withCredentials = true
  }
  return config
})

// Response interceptor: handle 401 and refresh
let isRefreshing = false
let refreshPromise: Promise<void> | null = null

apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config

    if (!originalRequest || !error.response || error.response.status !== 401) {
      return Promise.reject(error)
    }

    // Don't retry auth endpoint requests
    if (originalRequest.url?.startsWith('/api/auth')) {
      return Promise.reject(error)
    }

    // Mark retried requests
    if (originalRequest._retry) {
      return Promise.reject(error)
    }
    originalRequest._retry = true

    // Single-flight refresh
    if (!isRefreshing) {
      isRefreshing = true
      refreshPromise = authApi
        .refresh()
        .then((response) => {
          setAuth(response.user, response.access_token)
        })
        .catch(() => {
          clearAuth()
        })
        .finally(() => {
          isRefreshing = false
          refreshPromise = null
        })
    }

    // Wait for refresh
    if (refreshPromise) {
      try {
        await refreshPromise
        // Retry original request
        return apiClient(originalRequest)
      } catch {
        return Promise.reject(error)
      }
    }

    return Promise.reject(error)
  },
)

function extractErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error) && error.response?.data) {
    const data = error.response.data as { detail?: string; message?: string }
    return data.detail ?? data.message ?? error.message
  }
  if (error instanceof Error) return error.message
  return 'Analysis failed'
}

export { extractErrorMessage }
export default apiClient
