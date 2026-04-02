import apiClient from './client'

export interface SessionResponse {
  id: string
  title: string
  updated_at: string
}

export interface MessageResponse {
  id: string
  role: string
  type: string
  content: string
  attachments: Record<string, unknown> | null
  result: Record<string, unknown> | null
  status: string
  created_at: string
}

export interface MessageCreate {
  id: string
  role: string
  type: string
  content: string
  attachments?: Record<string, unknown> | null
  result?: Record<string, unknown> | null
  result_schema_version?: number | null
  status: string
}

export const chatApi = {
  async listSessions(limit = 50): Promise<SessionResponse[]> {
    const response = await apiClient.get<SessionResponse[]>(
      `/api/chat/sessions?limit=${limit}`,
    )
    return response.data
  },

  async createSession(id: string, title: string): Promise<SessionResponse> {
    const response = await apiClient.post<SessionResponse>('/api/chat/sessions', {
      id,
      title,
    })
    return response.data
  },

  async getSession(sessionId: string): Promise<SessionResponse> {
    const response = await apiClient.get<SessionResponse>(
      `/api/chat/sessions/${sessionId}`,
    )
    return response.data
  },

  async updateSession(sessionId: string, title: string): Promise<SessionResponse> {
    const response = await apiClient.patch<SessionResponse>(
      `/api/chat/sessions/${sessionId}`,
      { title },
    )
    return response.data
  },

  async deleteSession(sessionId: string): Promise<void> {
    await apiClient.delete(`/api/chat/sessions/${sessionId}`)
  },

  async deleteAllSessions(): Promise<void> {
    await apiClient.delete('/api/chat/sessions')
  },

  async listMessages(
    sessionId: string,
    cursor?: string,
    limit = 50,
  ): Promise<MessageResponse[]> {
    const params = new URLSearchParams()
    params.set('limit', String(limit))
    if (cursor) params.set('cursor', cursor)

    const response = await apiClient.get<MessageResponse[]>(
      `/api/chat/sessions/${sessionId}/messages?${params.toString()}`,
    )
    return response.data
  },

  async createMessages(
    sessionId: string,
    messages: MessageCreate[],
  ): Promise<MessageResponse[]> {
    const response = await apiClient.post<MessageResponse[]>(
      `/api/chat/sessions/${sessionId}/messages`,
      { messages },
    )
    return response.data
  },
}
