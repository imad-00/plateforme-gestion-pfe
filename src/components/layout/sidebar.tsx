'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import {
  Archive,
  Award,
  BookMarked,
  BookOpen,
  CalendarDays,
  Eye,
  FileBarChart,
  Gavel,
  GraduationCap,
  Hourglass,
  Landmark,
  LayoutDashboard,
  ListChecks,
  UserSearch,
  ScrollText,
  Upload,
  UserCog,
  Users,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type { CampaignStatus, DefenseListItem, PaginatedResponse, PhaseType, User } from '@/lib/types'
import { cn } from '@/lib/utils'

// ─── Nav config ───────────────────────────────────────────────────────────────

interface NavItem {
  href: string
  label: string
  icon: React.ComponentType<{ className?: string }>
  // When true, the item is only active for an exact pathname match. Used for
  // role roots (/admin, /teacher, /student) so they don't stay highlighted
  // when the user navigates into a child page like /admin/users.
  exact?: boolean
  // When set, the entry only renders while this phase is in `open_phases`.
  // Used by Defense routes so they vanish outside DEFENSE_WINDOW.
  requiresPhase?: PhaseType
  // When true, the entry only renders if the user currently has ≥1 jury
  // assignment (used for /jury/defenses).
  requiresJury?: boolean
  // When true, the entry only renders for SUPER_ADMIN platform grants. ADMIN-
  // only grants don't qualify. Used for the lifecycle + audit log pages.
  requiresSuperAdmin?: boolean
}

const NAV_STUDENT: NavItem[] = [
  { href: '/student',              label: 'Dashboard',    icon: LayoutDashboard, exact: true },
  { href: '/student/team',         label: 'My Team',      icon: Users      },
  { href: '/student/discover',     label: 'Find Teammates', icon: UserSearch },
  { href: '/student/subjects',     label: 'Subjects',     icon: BookOpen   },
  { href: '/student/wishlist',     label: 'My Wishlist',  icon: ListChecks },
  { href: '/student/results',      label: 'Results',      icon: Award      },
  { href: '/student/deliverables', label: 'Deliverables', icon: Upload     },
  { href: '/student/defense',      label: 'Defense',      icon: Landmark,   requiresPhase: 'DEFENSE_WINDOW' },
]

const NAV_TEACHER: NavItem[] = [
  { href: '/teacher',                  label: 'Dashboard',        icon: LayoutDashboard, exact: true },
  { href: '/teacher/subjects',         label: 'My Subjects',      icon: BookMarked },
  { href: '/teacher/supervision',      label: 'Supervision',      icon: Eye        },
  { href: '/teacher/defense-requests', label: 'Defense requests', icon: Landmark, requiresPhase: 'DEFENSE_WINDOW' },
  { href: '/jury/defenses',            label: 'Jury',             icon: Gavel,    requiresJury: true },
]

const NAV_EXTERNAL: NavItem[] = [
  { href: '/teacher',                  label: 'Dashboard',        icon: LayoutDashboard, exact: true },
  { href: '/teacher/supervision',      label: 'Supervision',      icon: Eye },
  { href: '/teacher/defense-requests', label: 'Defense requests', icon: Landmark, requiresPhase: 'DEFENSE_WINDOW' },
  { href: '/jury/defenses',            label: 'Jury',             icon: Gavel,    requiresJury: true },
]

const NAV_ADMIN: NavItem[] = [
  { href: '/admin',                label: 'Dashboard',      icon: LayoutDashboard, exact: true },
  { href: '/admin/users',          label: 'Users',          icon: UserCog    },
  { href: '/admin/academic-years', label: 'Academic Year',  icon: CalendarDays },
  { href: '/admin/history',        label: 'History',        icon: Archive    },
  { href: '/admin/subjects',       label: 'Subjects',       icon: BookOpen   },
  { href: '/admin/teams',          label: 'Teams',          icon: Users      },
  { href: '/admin/assignments',    label: 'Assignments',    icon: ListChecks },
  { href: '/admin/defenses',       label: 'Defenses',       icon: Landmark   },
  { href: '/admin/reports',        label: 'Reports',        icon: FileBarChart },
  { href: '/admin/lifecycle',      label: 'Lifecycle',      icon: Hourglass,   requiresSuperAdmin: true },
  { href: '/admin/audit',          label: 'Audit log',      icon: ScrollText,  requiresSuperAdmin: true },
  { href: '/jury/defenses',        label: 'Jury',           icon: Gavel,       requiresJury: true },
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

export function Sidebar({ onNavigate, className }: { onNavigate?: () => void; className?: string } = {}) {
  const { user } = useAuth()
  const pathname = usePathname()
  // One quick fetch shared by every phase-gated entry. Errors are silent —
  // a failed campaign fetch simply hides phase-gated routes rather than blocking
  // the sidebar.
  const campaignApi = useApi<CampaignStatus>(() => api.get('/api/campaign/current/'), [])
  // Probe the jury list to know whether to surface the Jury entry. Students
  // are never jury (excluded server-side too) so we skip the probe for them.
  // Errors are silent — a failed fetch simply hides the entry.
  const isStudent = user?.business_identity === 'STUDENT' && !user?.platform_access_level
  const juryApi = useApi<PaginatedResponse<DefenseListItem>>(
    () =>
      isStudent
        ? Promise.resolve({ count: 0, next: null, previous: null, results: [] })
        : api.get('/api/jury/defenses/?page_size=1'),
    [isStudent],
  )

  if (!user) return null

  const openPhases = new Set(campaignApi.data?.open_phases ?? [])
  const hasJuryAssignments = (juryApi.data?.count ?? 0) > 0
  const isSuperAdmin = user.platform_access_level === 'SUPER_ADMIN'
  const items = getNavItems(user).filter(item => {
    if (item.requiresPhase && !openPhases.has(item.requiresPhase)) return false
    if (item.requiresJury && !hasJuryAssignments) return false
    if (item.requiresSuperAdmin && !isSuperAdmin) return false
    return true
  })

  return (
    <aside className={cn('flex h-full w-64 shrink-0 flex-col border-r border-sidebar-border bg-sidebar', className)}>
      {/* Logo */}
      <div className="flex h-14 items-center gap-2.5 border-b border-sidebar-border px-4">
        <div className="flex size-7 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <GraduationCap className="size-4" />
        </div>
        <div className="flex min-w-0 flex-col leading-tight">
          <span className="font-semibold tracking-tight text-sidebar-foreground">
            GradeX
          </span>
          <span className="truncate text-[10px] uppercase tracking-wider text-muted-foreground">
            ESI-SBA
          </span>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 overflow-y-auto px-3 py-4">
        <ul className="space-y-0.5">
          {items.map(item => {
            const active = item.exact
              ? pathname === item.href
              : pathname === item.href || pathname.startsWith(item.href + '/')
            return (
              <li key={item.href}>
                <Link
                  href={item.href}
                  onClick={onNavigate}
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
