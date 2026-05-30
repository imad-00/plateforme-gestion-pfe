'use client'

import Link from 'next/link'
import { GraduationCap, LogOut, Menu } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import type { User } from '@/lib/types'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { NotificationBell } from '@/components/layout/notification-bell'

function getInitials(user: User): string {
  const from = [user.first_name, user.last_name]
    .map(s => s.at(0)?.toUpperCase() ?? '')
    .join('')
  return from || user.matricule.slice(0, 2).toUpperCase()
}

function getRoleLabel(user: User): string {
  if (user.platform_access_level === 'SUPER_ADMIN') return 'Super Admin'
  if (user.platform_access_level === 'ADMIN') return 'Admin'
  switch (user.business_identity) {
    case 'STUDENT':             return 'Student'
    case 'TEACHER':             return 'Teacher'
    case 'EXTERNAL_SUPERVISOR': return 'External Supervisor'
    default:                    return 'Staff'
  }
}

export function Topbar({ onMenuClick }: { onMenuClick?: () => void } = {}) {
  const { user, logout } = useAuth()

  if (!user) return null

  return (
    <header className="flex h-14 shrink-0 items-center justify-between gap-2 border-b border-border bg-card px-4 sm:px-6">
      {/* Left: mobile menu trigger + compact logo (sidebar is hidden on mobile) */}
      <div className="flex items-center gap-2 lg:hidden">
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onMenuClick}
          aria-label="Open navigation menu"
          className="text-muted-foreground hover:text-foreground"
        >
          <Menu className="size-5" />
        </Button>
        <Link href="/" className="flex items-center gap-2" aria-label="GradeX home">
          <span className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <GraduationCap className="size-4" />
          </span>
          <span className="font-semibold tracking-tight">GradeX</span>
        </Link>
      </div>

      {/* Spacer keeps the action cluster right-aligned on desktop */}
      <div className="hidden lg:block" />

      <div className="flex items-center gap-2 sm:gap-3">
        {/* Notifications */}
        <NotificationBell />

        {/* Avatar + identity → /profile */}
        <Link
          href="/profile"
          className="flex items-center gap-3 rounded-md px-1 py-1 hover:bg-muted"
          title="My profile"
        >
          <Avatar size="sm">
            <AvatarFallback className="bg-primary/10 text-xs text-primary">
              {getInitials(user)}
            </AvatarFallback>
          </Avatar>
          <div className="hidden flex-col leading-tight sm:flex">
            <span className="text-sm font-medium text-foreground">
              {user.first_name} {user.last_name}
            </span>
            <span className="text-xs text-muted-foreground">
              {getRoleLabel(user)}
            </span>
          </div>
        </Link>

        {/* Logout */}
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={logout}
          title="Sign out"
          className="ml-1 text-muted-foreground hover:text-foreground"
        >
          <LogOut className="size-4" />
        </Button>
      </div>
    </header>
  )
}
