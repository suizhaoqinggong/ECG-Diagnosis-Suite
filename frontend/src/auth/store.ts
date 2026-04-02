import type { AuthState, AuthListener, User } from './types'

const initialState: AuthState = {
  user: null,
  accessToken: null,
  isLoading: true,
}

let state: AuthState = { ...initialState }
const listeners: Set<AuthListener> = new Set()

function setState(partial: Partial<AuthState>) {
  state = { ...state, ...partial }
  listeners.forEach((listener) => listener(state))
}

export function getState(): AuthState {
  return state
}

export function subscribe(listener: AuthListener): () => void {
  listeners.add(listener)
  return () => {
    listeners.delete(listener)
  }
}

export function getToken(): string | null {
  return state.accessToken
}

export function setAuth(user: User, accessToken: string) {
  setState({ user, accessToken, isLoading: false })
}

export function clearAuth() {
  setState({ user: null, accessToken: null, isLoading: false })
}

export function setLoading(loading: boolean) {
  setState({ isLoading: loading })
}
