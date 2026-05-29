'use client'

import { useEffect } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { useAuth } from '@/lib/auth-context'
import type { User } from '@/lib/types'
import { Sidebar } from '@/components/layout/sidebar'
import { Topbar } from '@/components/layout/topbar'
import { Skeleton } from '@/components/ui/skeleton'

// ─── Auth helpers ─────────────────────────────────────────────────────────────

function defaultRoute(user: User): string {
  if (user.platform_access_level) return '/admin'
  switch (user.business_identity) {
    case 'STUDENT':             return '/student'
    case 'TEACHER':             return '/teacher'
    case 'EXTERNAL_SUPERVISOR': return '/teacher'
    default:                    return '/login'
  }
}

// Cross-role routes any authenticated user may access regardless of identity
// or platform grant.
const SHARED_ROUTES = ['/notifications']

function isAllowed(user: User, pathname: string): boolean {
  if (SHARED_ROUTES.some(r => pathname === r || pathname.startsWith(r + '/'))) return true
  if (user.platform_access_level) return pathname.startsWith('/admin')
  switch (user.business_identity) {
    case 'STUDENT':             return pathname.startsWith('/student')
    case 'TEACHER':             return pathname.startsWith('/teacher')
    case 'EXTERNAL_SUPERVISOR': return pathname.startsWith('/teacher')
    default:                    return false
  }
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────
// Shown while the auth context is restoring the session from localStorage,
// and while a redirect is in-flight — prevents any layout flash.

function LoadingShell() {
  return (
    <div className="flex h-screen overflow-hidden bg-background">
      {/* Sidebar placeholder */}
      <div className="w-64 shrink-0 border-r border-border bg-sidebar" />

      <div className="flex flex-1 flex-col overflow-hidden">
        {/* Topbar placeholder */}
        <div className="flex h-14 shrink-0 items-center justify-end border-b border-border bg-card px-6">
          <Skeleton className="h-6 w-40" />
        </div>

        {/* Content placeholder */}
        <div className="flex-1 p-6 lg:p-8">
          <Skeleton className="mb-2 h-7 w-48" />
          <Skeleton className="h-4 w-72" />
        </div>
      </div>
    </div>
  )
}

// ─── Layout ───────────────────────────────────────────────────────────────────

export default function AppLayout({ children }: { children: React.ReactNode }) {
  const { user, isLoading } = useAuth()
  const pathname = usePathname()
  const router = useRouter()

  useEffect(() => {
    if (isLoading) return
    if (!user) {
      // A refresh token means login just completed or a session restore is
      // still in-flight — the auth context will set user on the next render.
      // Redirecting now would bounce the user back to /login incorrectly.
      try { if (localStorage.getItem('gradex_refresh')) return } catch { /* ignore */ }
      router.replace('/login')
      return
    }
    if (!isAllowed(user, pathname)) router.replace(defaultRoute(user))
  }, [user, isLoading, pathname, router])

  // Show skeleton while the session is resolving or a redirect is queued.
  if (isLoading || !user || !isAllowed(user, pathname)) {
    return <LoadingShell />
  }

  return (
    <div className="flex h-screen overflow-hidden bg-background">
      <Sidebar />
      <div className="flex flex-1 flex-col overflow-hidden">
        <Topbar />
        <main className="flex-1 overflow-y-auto p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  )
}
