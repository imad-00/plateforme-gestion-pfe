'use client'

import { useAuth } from '@/lib/auth-context'
import type { User } from '@/lib/types'
import { LandingView } from './landing/landing-view'

/**
 * Root route — the public landing page.
 *
 * Reachable by everyone, including authenticated users (so they can come back
 * to the marketing surface after signing in). The landing CTAs swap based on
 * the auth state: guests see "Sign in" / "Get started"; signed-in users see
 * "Open your dashboard" pointing at their role's home.
 */
export default function RootPage() {
  const { user, isLoading } = useAuth()

  return (
    <LandingView
      authedDashboardHref={user ? dashboardHrefFor(user) : null}
      authChecked={!isLoading}
    />
  )
}

function dashboardHrefFor(user: User): string {
  if (user.platform_access_level) return '/admin'
  switch (user.business_identity) {
    case 'STUDENT':             return '/student'
    case 'TEACHER':             return '/teacher'
    case 'EXTERNAL_SUPERVISOR': return '/teacher'
    default:                    return '/login'
  }
}
