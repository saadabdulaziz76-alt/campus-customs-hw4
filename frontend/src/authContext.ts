/** Auth context and hook, kept apart from the provider component so the
 *  provider file exports only a component (which keeps fast refresh working). */

import { createContext, useContext } from 'react'

export interface User {
  id: number
  name: string
  first_name: string | null
  last_name: string | null
  email: string
  created_at: string | null
}

export interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (input: {
    firstName: string
    lastName: string
    email: string
    password: string
  }) => Promise<void>
  logout: () => void
  authHeader: () => Record<string, string>
}

export const AuthContext = createContext<AuthContextValue | null>(null)

/** The token is the only thing kept client-side. Passwords are never stored. */
export const TOKEN_KEY = 'campus_customs_token'

export function readToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function writeToken(token: string | null) {
  try {
    if (token) localStorage.setItem(TOKEN_KEY, token)
    else localStorage.removeItem(TOKEN_KEY)
  } catch {
    /* private browsing — the session just will not survive a reload */
  }
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext)
  if (!context) throw new Error('useAuth must be used inside <AuthProvider>')
  return context
}
