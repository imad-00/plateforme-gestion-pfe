'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Award,
  BookMarked,
  BookOpen,
  CalendarDays,
  Eye,
  GraduationCap,
  ListChecks,
  Upload,
  UserCog,
  Users,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import type { User } from '@/lib/types'
import { cn } from '@/lib/utils'

// ─── Nav config ───────────────────────────────────────────────────────────────

interface NavItem {
  href: string
  label: string
  icon: React.ComponentType<{ className?: string }>
}

const NAV_STUDENT: NavItem[] = [
  { href: '/student/team',         label: 'My Team',      icon: Users      },
  { href: '/student/subjects',     label: 'Subjects',     icon: BookOpen   },
  { href: '/student/results',      label: 'Results',      icon: Award      },
  { href: '/student/deliverables', label: 'Deliverables', icon: Upload     },
]

const NAV_TEACHER: NavItem[] = [
  { href: '/teacher/subjects',    label: 'My Subjects', icon: BookMarked },
  { href: '/teacher/supervision', label: 'Supervision', icon: Eye        },
]

const NAV_EXTERNAL: NavItem[] = [
  { href: '/teacher/supervision', label: 'Supervision', icon: Eye },
]

const NAV_ADMIN: NavItem[] = [
  { href: '/admin/users',          label: 'Users',          icon: UserCog    },
  { href: '/admin/academic-years', label: 'Academic Years', icon: CalendarDays },
  { href: '/admin/subjects',       label: 'Subjects',       icon: BookOpen   },
  { href: '/admin/teams',          label: 'Teams',          icon: Users      },
  { href: '/admin/assignments',    label: 'Assignments',    icon: ListChecks },
]

function getNavItems(user: User): NavItem[] {
  if (user.platform_access_level) return NAV_ADMIN
  switch (user.business_identity) {
    case 'STUDENT':             return NAV_STUDENT
    case 'TEACHER':             return NAV_TEACHER
    case 'EXTERNAL_SUPERVISOR': return NAV_EXTERNAL
    default:                    return []
  }
}

// ─── Component ────────────────────────────────────────────────────────────────

export function Sidebar() {
  const { user } = useAuth()
  const pathname = usePathname()

  if (!user) return null

  const items = getNavItems(user)

  return (
    <aside className="flex h-full w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar">
      {/* Logo */}
      <div className="flex h-14 items-center gap-2.5 border-b border-sidebar-border px-4">
        <div className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <GraduationCap className="size-4" />
        </div>
        <span className="font-semibold tracking-tight text-sidebar-foreground">
          GradeX
        </span>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-0.5">
          {items.map(item => {
            const active =
              pathname === item.href || pathname.startsWith(item.href + '/')
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  className={cn(
                    'flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors',
                    active
                      ? 'bg-accent text-accent-foreground'
                      : 'text-muted-foreground hover:bg-muted hover:text-foreground',
                  )}
                >
                  <item.icon className="size-4 shrink-0" />
                  {item.label}
                </Link>
              </li>
            )
          })}
        </ul>
      </nav>
    </aside>
  )
}
