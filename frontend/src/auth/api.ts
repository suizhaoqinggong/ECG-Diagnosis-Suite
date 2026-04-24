import apiClient from '@/api/client'
import type { AuthResponse, LoginRequest, RegisterRequest } from './types'

export async function login(data: LoginRequest): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>('/api/auth/login', data, {
    withCredentials: true,
  })
  return response.data
}

export async function register(data: RegisterRequest): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>('/api/auth/register', data, {
    withCredentials: true,
  })
  return response.data
}

export async function refresh(): Promise<AuthResponse> {
  const response = await apiClient.post<AuthResponse>(
    '/api/auth/refresh',
    {},
    { withCredentials: true },
  )
  return response.data
}

export async function logout(): Promise<void> {
  await apiClient.post('/api/auth/logout', {}, { withCredentials: true })
}

export async function changePassword(oldPassword: string, newPassword: string): Promise<void> {
  await apiClient.post('/api/auth/change-password', {
    old_password: oldPassword,
    new_password: newPassword,
  })
}

export async function deleteAccount(password: string): Promise<void> {
  await apiClient.post(
    '/api/auth/delete-account',
    { password },
    { withCredentials: true },
  )
}
