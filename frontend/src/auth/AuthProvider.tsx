import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import type { AuthState, User } from './types'
import { getState, subscribe, setAuth, clearAuth, setLoading } from './store'
import { refresh } from './api'

interface AuthContextValue extends AuthState {
  setAuthenticated: (user: User, accessToken: string) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}

interface AuthProviderProps {
  children: ReactNode
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [localState, setLocalState] = useState<AuthState>(getState())

  useEffect(() => {
    return subscribe((newState) => setLocalState(newState))
  }, [])

  useEffect(() => {
    refresh()
      .then((response) => {
        setAuth(response.user, response.access_token)
      })
      .catch(() => {
        clearAuth()
      })
      .finally(() => {
        setLoading(false)
      })
  }, [])

  const handleSetAuthenticated = (user: User, accessToken: string) => {
    setAuth(user, accessToken)
  }

  const handleLogout = () => {
    clearAuth()
  }

  const value: AuthContextValue = {
    ...localState,
    setAuthenticated: handleSetAuthenticated,
    logout: handleLogout,
  }

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
