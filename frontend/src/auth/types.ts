export interface User {
  id: number
  email: string
  display_name: string | null
}

export interface AuthState {
  user: User | null
  accessToken: string | null
  isLoading: boolean
}

export interface LoginRequest {
  email: string
  password: string
}

export interface RegisterRequest {
  email: string
  password: string
  display_name?: string
}

export interface AuthResponse {
  access_token: string
  user: User
}

export type AuthListener = (state: AuthState) => void
