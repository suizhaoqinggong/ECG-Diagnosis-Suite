import apiClient from './client'
import type { HealthJobResponse } from '@/types/health'

export const healthApi = {
  async createJob(
    files: File[],
    note: string,
    sessionId?: string,
  ): Promise<HealthJobResponse> {
    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    formData.append('note', note)
    if (sessionId) {
      formData.append('session_id', sessionId)
    }
    const response = await apiClient.post<HealthJobResponse>('/api/health/jobs', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return response.data
  },

  async getJob(jobId: string): Promise<HealthJobResponse> {
    const response = await apiClient.get<HealthJobResponse>(`/api/health/jobs/${jobId}`)
    return response.data
  },
}
