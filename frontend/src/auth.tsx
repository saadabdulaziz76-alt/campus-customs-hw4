/** Authentication provider for the whole app. */

import { useCallback, useEffect, useMemo, useState } from 'react'
import type { ReactNode } from 'react'
import { API_BASE } from './api'
import { AuthContext, readToken, writeToken } from './authContext'
import type { User } from './authContext'

interface AuthResponse {
  token: string
  user: User
}

/** Turn a FastAPI error body into a readable message. */
async function errorMessage(response: Response): Promise<string> {
  try {
    const data = await response.json()
    if (typeof data?.detail === 'string') return data.detail
    if (Array.isArray(data?.detail) && data.detail[0]?.msg) return String(data.detail[0].msg)
  } catch {
    /* fall through */
  }
  return `Something went wrong (${response.status}).`
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  // Only "loading" if there is actually a stored session to restore.
  const [loading, setLoading] = useState(() => readToken() !== null)

  // Restore the session by asking the API who the stored token belongs to. A
  // token that has expired or been tampered with is simply discarded.
  useEffect(() => {
    const token = readToken()
    if (!token) return

    const controller = new AbortController()
    fetch(new URL('/api/auth/me', API_BASE), {
      headers: { Authorization: `Bearer ${token}` },
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          writeToken(null)
          return null
        }
        return (await response.json()) as User
      })
      .then(setUser)
      .catch(() => undefined)
      .finally(() => setLoading(false))

    return () => controller.abort()
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    const response = await fetch(new URL('/api/auth/login', API_BASE), {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ email, password }),
    })
    if (!response.ok) throw new Error(await errorMessage(response))
    const data = (await response.json()) as AuthResponse
    writeToken(data.token)
    setUser(data.user)
  }, [])

  const register = useCallback(
    async (input: { firstName: string; lastName: string; email: string; password: string }) => {
      const response = await fetch(new URL('/api/auth/register', API_BASE), {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          first_name: input.firstName,
          last_name: input.lastName,
          email: input.email,
          password: input.password,
        }),
      })
      if (!response.ok) throw new Error(await errorMessage(response))
      const data = (await response.json()) as AuthResponse
      writeToken(data.token)
      setUser(data.user)
    },
    [],
  )

  const logout = useCallback(() => {
    writeToken(null)
    setUser(null)
  }, [])

  const authHeader = useCallback((): Record<string, string> => {
    const token = readToken()
    return token ? { Authorization: `Bearer ${token}` } : {}
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, logout, authHeader }),
    [user, loading, login, register, logout, authHeader],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
