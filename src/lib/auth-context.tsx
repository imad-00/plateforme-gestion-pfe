'use client'

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useRef,
  useState,
} from 'react'
import { useRouter } from 'next/navigation'
import { registerAuth } from '@/lib/api-client'
import { API_BASE } from '@/lib/config'
import type { LoginResponse, User } from '@/lib/types'

const REFRESH_KEY = 'gradex_refresh'
const SESSION_COOKIE = 'gradex_session'

// ─── Context shape ────────────────────────────────────────────────────────────

interface AuthContextValue {
  user: User | null
  accessToken: string | null
  isLoading: boolean
  login: (identifier: string, password: string) => Promise<User>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

// ─── Helpers ──────────────────────────────────────────────────────────────────

function readRefreshToken(): string | null {
  try {
    return localStorage.getItem(REFRESH_KEY)
  } catch {
    return null
  }
}

function writeRefreshToken(token: string): void {
  try {
    localStorage.setItem(REFRESH_KEY, token)
  } catch { /* ignore */ }
}

function removeRefreshToken(): void {
  try {
    localStorage.removeItem(REFRESH_KEY)
  } catch { /* ignore */ }
}

// ─── Provider ─────────────────────────────────────────────────────────────────

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [accessToken, setAccessToken] = useState<string | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const router = useRouter()

  // Ref mirrors the state value so the registerAuth callbacks always read the
  // current token synchronously — a closure over `accessToken` state would be
  // stale because it captures the value at the time the callback was created.
  const tokenRef = useRef<string | null>(null)

  const storeAccessToken = useCallback((token: string | null) => {
    tokenRef.current = token
    setAccessToken(token)
  }, [])

  const clearSession = useCallback(() => {
    storeAccessToken(null)
    setUser(null)
    removeRefreshToken()
    document.cookie = `${SESSION_COOKIE}=; path=/; max-age=0; SameSite=Lax`
  }, [storeAccessToken])

  // logout uses plain fetch — NOT apiClient — so a 401 on the blacklist call
  // cannot re-enter the refresh cycle and cause an infinite loop.
  const logout = useCallback(() => {
    const refreshToken = readRefreshToken()
    if (refreshToken) {
      fetch(`${API_BASE}/api/auth/logout/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          ...(tokenRef.current
            ? { Authorization: `Bearer ${tokenRef.current}` }
            : {}),
        },
        body: JSON.stringify({ refresh: refreshToken }),
      }).catch(() => {}) // fire-and-forget; session is cleared regardless
    }
    clearSession()
    router.push('/login')
  }, [clearSession, router])

  // Wire up the callbacks that api-client needs to attach/refresh tokens and
  // trigger logout on irrecoverable 401s — done here to avoid a circular import.
  useEffect(() => {
    registerAuth({
      getAccessToken: () => tokenRef.current,
      getRefreshToken: readRefreshToken,
      setAccessToken: storeAccessToken,
      logout,
    })
  }, [logout, storeAccessToken])

  // Restore session on mount. Keeps isLoading=true until we know whether the
  // stored refresh token yields a valid session, preventing a flash to /login.
  useEffect(() => {
    let cancelled = false

    async function restoreSession() {
      const refreshToken = readRefreshToken()

      if (!refreshToken) {
        setIsLoading(false)
        return
      }

      try {
        // Step 1: exchange refresh token for a new access token
        const refreshRes = await fetch(`${API_BASE}/api/auth/refresh/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh: refreshToken }),
        })
        if (!refreshRes.ok) throw new Error('refresh failed')
        const { access } = (await refreshRes.json()) as { access: string }

        // Step 2: fetch the current user with the new access token
        const meRes = await fetch(`${API_BASE}/api/auth/me/`, {
          headers: { Authorization: `Bearer ${access}` },
        })
        if (!meRes.ok) throw new Error('me failed')
        const userData = (await meRes.json()) as User

        if (!cancelled) {
          storeAccessToken(access)
          setUser(userData)
        }
      } catch {
        // Refresh token expired or revoked — clear everything silently
        if (!cancelled) clearSession()
      } finally {
        if (!cancelled) setIsLoading(false)
      }
    }

    restoreSession()
    return () => {
      cancelled = true
    }
  // storeAccessToken and clearSession are stable (useCallback with stable deps),
  // so including them satisfies exhaustive-deps without causing extra runs.
  }, [storeAccessToken, clearSession])

  // login uses plain fetch — apiClient has no token to attach on a fresh login,
  // and this avoids any ordering dependency on registerAuth having run first.
  const login = useCallback(
    async (identifier: string, password: string): Promise<User> => {
      const res = await fetch(`${API_BASE}/api/auth/login/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ identifier, password }),
      })

      if (!res.ok) {
        const err = (await res.json()) as Record<string, unknown>
        const message =
          typeof err.detail === 'string'
            ? err.detail
            : 'Invalid credentials. Please try again.'
        throw new Error(message)
      }

      const data = (await res.json()) as LoginResponse

      // Write to localStorage before updating React state so that AppLayout's
      // guard can detect an in-flight session even if the state update hasn't
      // committed yet when the new route renders.
      writeRefreshToken(data.refresh)
      document.cookie = `${SESSION_COOKIE}=1; path=/; SameSite=Lax`
      storeAccessToken(data.access)
      setUser(data.user)

      return data.user
    },
    [storeAccessToken],
  )

  return (
    <AuthContext.Provider value={{ user, accessToken, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

// ─── Hook ─────────────────────────────────────────────────────────────────────

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within an AuthProvider')
  return ctx
}
