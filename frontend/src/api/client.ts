import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL?.trim() || ''

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
})

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
