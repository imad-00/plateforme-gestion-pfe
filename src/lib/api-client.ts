import { API_BASE } from '@/lib/config'
import type { ApiError } from '@/lib/types'

// ─── Error class ──────────────────────────────────────────────────────────────

// Walks the API error response for the first string value. DRF returns
// `{ detail: "..." }` for permission/auth errors but `{ field_name: ["..."] }`
// or `{ field_name: "..." }` for validation errors — both forms now produce
// a usable message instead of the generic "Request failed with status N".
function firstStringValue(data: ApiError): string | undefined {
  for (const v of Object.values(data)) {
    if (typeof v === 'string' && v.trim()) return v
    if (Array.isArray(v)) {
      const s = v.find(x => typeof x === 'string' && x.trim())
      if (s) return s as string
    }
  }
  return undefined
}

export class ApiClientError extends Error {
  constructor(
    public readonly status: number,
    public readonly data: ApiError,
  ) {
    super(data.detail ?? firstStringValue(data) ?? `Request failed with status ${status}`)
    this.name = 'ApiClientError'
  }
}

// ─── Auth callbacks ───────────────────────────────────────────────────────────
// AuthProvider calls registerAuth() on mount so the client can read/write
// tokens without importing from auth-context (which would create a circular dep).
// logout() in AuthProvider must use fetch() directly for the blacklist call —
// not apiClient() — to avoid re-entering this module on token expiry.

interface AuthCallbacks {
  getAccessToken: () => string | null
  getRefreshToken: () => string | null
  setAccessToken: (token: string) => void
  logout: () => void
}

let _auth: AuthCallbacks | null = null

export function registerAuth(callbacks: AuthCallbacks): void {
  _auth = callbacks
}

// ─── Single-flight refresh ────────────────────────────────────────────────────
// If multiple requests 401 concurrently, they all await the same promise
// instead of each firing a separate refresh call.

let refreshPromise: Promise<string> | null = null

async function doRefresh(): Promise<string> {
  if (refreshPromise) return refreshPromise

  refreshPromise = (async () => {
    const refreshToken = _auth?.getRefreshToken() ?? null
    if (!refreshToken) throw new Error('no refresh token')

    const res = await fetch(`${API_BASE}/api/auth/refresh/`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ refresh: refreshToken }),
    })

    if (!res.ok) throw new Error('refresh failed')

    const data = (await res.json()) as { access: string }
    _auth?.setAccessToken(data.access)
    return data.access
  })().finally(() => {
    refreshPromise = null
  })

  return refreshPromise
}

// ─── Response parser ──────────────────────────────────────────────────────────

async function parseResponse<T>(res: Response): Promise<T> {
  // 204 No Content or empty body
  const contentLength = res.headers.get('content-length')
  if (res.status === 204 || contentLength === '0') {
    return undefined as T
  }

  const data: unknown = await res.json()

  if (!res.ok) {
    throw new ApiClientError(res.status, data as ApiError)
  }

  return data as T
}

// ─── Core fetch wrapper ───────────────────────────────────────────────────────

export async function apiClient<T = unknown>(
  path: string,
  options: RequestInit = {},
): Promise<T> {
  const token = _auth?.getAccessToken() ?? null

  const headers = new Headers(options.headers)
  if (token) headers.set('Authorization', `Bearer ${token}`)
  // Do not set Content-Type for FormData — the browser sets it with the boundary.
  if (!(options.body instanceof FormData)) {
    headers.set('Content-Type', 'application/json')
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })

  if (res.status === 401) {
    try {
      const newToken = await doRefresh()
      headers.set('Authorization', `Bearer ${newToken}`)
      const retryRes = await fetch(`${API_BASE}${path}`, { ...options, headers })
      return parseResponse<T>(retryRes)
    } catch {
      _auth?.logout()
      throw new ApiClientError(401, { detail: 'Session expired. Please log in again.' })
    }
  }

  return parseResponse<T>(res)
}

// ─── Convenience helpers ──────────────────────────────────────────────────────

function bodyInit(body: unknown): BodyInit | undefined {
  if (body === undefined) return undefined
  if (body instanceof FormData) return body
  return JSON.stringify(body)
}

// Binary fetch + browser-download trigger used by report exports. The standard
// api.get pipeline calls res.json() which would choke on CSV/XLSX bodies, so
// this helper goes around it while still using the same JWT + refresh plumbing.
async function fetchBinary(path: string): Promise<Blob> {
  const token = _auth?.getAccessToken() ?? null
  const headers = new Headers()
  if (token) headers.set('Authorization', `Bearer ${token}`)

  const run = async (authHeader: string | null): Promise<Response> => {
    const h = new Headers(headers)
    if (authHeader) h.set('Authorization', authHeader)
    return fetch(`${API_BASE}${path}`, { method: 'GET', headers: h })
  }

  let res = await run(token ? `Bearer ${token}` : null)
  if (res.status === 401) {
    try {
      const newToken = await doRefresh()
      res = await run(`Bearer ${newToken}`)
    } catch {
      _auth?.logout()
      throw new ApiClientError(401, { detail: 'Session expired. Please log in again.' })
    }
  }
  if (!res.ok) {
    // For binary endpoints the body is usually empty or text — surface a
    // structured error so callers can show a useful message.
    let detail = `Request failed with status ${res.status}`
    try {
      const text = await res.text()
      if (text) detail = text
    } catch {
      /* ignore */
    }
    throw new ApiClientError(res.status, { detail })
  }
  return res.blob()
}

async function downloadFile(path: string, filename: string): Promise<void> {
  const blob = await fetchBinary(path)
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  URL.revokeObjectURL(url)
}

export const api = {
  get: <T>(path: string) =>
    apiClient<T>(path, { method: 'GET' }),

  post: <T>(path: string, body?: unknown) =>
    apiClient<T>(path, { method: 'POST', body: bodyInit(body) }),

  patch: <T>(path: string, body?: unknown) =>
    apiClient<T>(path, { method: 'PATCH', body: bodyInit(body) }),

  delete: <T>(path: string) =>
    apiClient<T>(path, { method: 'DELETE' }),

  download: downloadFile,
}
