'use client'

import { useEffect, useState } from 'react'
import { usePathname, useRouter } from 'next/navigation'
import { X } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import type { User } from '@/lib/types'
import { Sidebar } from '@/components/layout/sidebar'
import { Topbar } from '@/components/layout/topbar'
import { Skeleton } from '@/components/ui/skeleton'
import { cn } from '@/lib/utils'

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
const SHARED_ROUTES = ['/notifications', '/profile']

function isJuryPath(pathname: string): boolean {
  return pathname === '/jury' || pathname.startsWith('/jury/')
}

function isAllowed(user: User, pathname: string): boolean {
  if (SHARED_ROUTES.some(r => pathname === r || pathname.startsWith(r + '/'))) return true
  // Jury routes are accessible to anyone who CAN be on a jury — teachers,
  // external supervisors, and platform admins. Students are explicitly excluded
  // per product rule.
  if (isJuryPath(pathname)) {
    return (
      user.business_identity === 'TEACHER' ||
      user.business_identity === 'EXTERNAL_SUPERVISOR' ||
      !!user.platform_access_level
    )
  }
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
      <div className="hidden w-64 shrink-0 border-r border-border bg-sidebar lg:block" />

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
  const [mobileNavOpen, setMobileNavOpen] = useState(false)

  // Close the mobile drawer whenever the route changes so tapping a nav entry
  // doesn't leave the overlay covering the freshly-loaded page.
  useEffect(() => {
    setMobileNavOpen(false)
  }, [pathname])

  // Lock body scroll while the drawer is open so the page behind it stays put.
  useEffect(() => {
    if (!mobileNavOpen) return
    const prev = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => { document.body.style.overflow = prev }
  }, [mobileNavOpen])

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
      {/* Desktop sidebar — docked from the lg breakpoint up (≥1024px). Below
          that the drawer takes over so tablets in portrait don't get a
          squeezed main column. The wrapper owns the responsive hide so it
          never depends on class-merge order. */}
      <div className="hidden shrink-0 lg:flex">
        <Sidebar />
      </div>

      {/* Mobile / tablet drawer — slides in over the content with a dimmed backdrop. */}
      <div
        className={cn(
          'fixed inset-0 z-50 lg:hidden',
          mobileNavOpen ? 'pointer-events-auto' : 'pointer-events-none',
        )}
        aria-hidden={!mobileNavOpen}
      >
        {/* Backdrop */}
        <div
          onClick={() => setMobileNavOpen(false)}
          className={cn(
            'absolute inset-0 bg-foreground/40 backdrop-blur-sm transition-opacity duration-300',
            mobileNavOpen ? 'opacity-100' : 'opacity-0',
          )}
        />
        {/* Panel */}
        <div
          className={cn(
            'absolute inset-y-0 left-0 flex w-72 max-w-[85%] flex-col bg-sidebar shadow-modal transition-transform duration-300 ease-out',
            mobileNavOpen ? 'translate-x-0' : '-translate-x-full',
          )}
        >
          <button
            type="button"
            onClick={() => setMobileNavOpen(false)}
            aria-label="Close navigation menu"
            className="absolute right-3 top-3.5 z-10 flex size-8 items-center justify-center rounded-md text-muted-foreground transition-colors hover:bg-muted hover:text-foreground"
          >
            <X className="size-4" />
          </button>
          <Sidebar className="w-full border-r-0" onNavigate={() => setMobileNavOpen(false)} />
        </div>
      </div>

      <div className="flex min-w-0 flex-1 flex-col overflow-hidden">
        <Topbar onMenuClick={() => setMobileNavOpen(true)} />
        <main className="flex-1 overflow-y-auto p-4 sm:p-6 lg:p-8">
          {children}
        </main>
      </div>
    </div>
  )
}
