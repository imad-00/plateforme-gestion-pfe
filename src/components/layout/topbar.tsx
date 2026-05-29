'use client'

import { LogOut } from 'lucide-react'
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

export function Topbar() {
  const { user, logout } = useAuth()

  if (!user) return null

  return (
    <header className="flex h-14 shrink-0 items-center justify-end border-b border-border bg-card px-6">
      <div className="flex items-center gap-3">
        {/* Notifications */}
        <NotificationBell />

        {/* Avatar */}
        <Avatar size="sm">
          <AvatarFallback className="bg-primary/10 text-xs text-primary">
            {getInitials(user)}
          </AvatarFallback>
        </Avatar>

        {/* Identity */}
        <div className="flex flex-col leading-tight">
          <span className="text-sm font-medium text-foreground">
            {user.first_name} {user.last_name}
          </span>
          <span className="text-xs text-muted-foreground">
            {getRoleLabel(user)}
          </span>
        </div>

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
