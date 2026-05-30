'use client'

import Link from 'next/link'
import {
  AlertCircle,
  Award,
  Calendar,
  Eye,
  FileText,
  Inbox,
  Users,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type { TeacherDashboard } from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { EmptyState } from '@/components/shared/empty-state'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  const d = new Date(iso)
  return d.toLocaleString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
  })
}

// ─── Big counter card ─────────────────────────────────────────────────────────

function CounterCard({
  icon: Icon,
  label,
  value,
  hint,
  tone = 'neutral',
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: number
  hint?: string
  tone?: 'success' | 'warning' | 'neutral'
}) {
  const accent: Record<typeof tone, string> = {
    success: 'text-status-success-fg',
    warning: 'text-status-warning-fg',
    neutral: 'text-foreground',
  }
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">{label}</CardTitle>
        <Icon className="size-4 text-muted-foreground" />
      </CardHeader>
      <CardContent>
        <div className={`text-2xl font-bold tabular-nums tracking-tight ${accent[tone]}`}>
          {value}
        </div>
        {hint && <p className="mt-1 text-xs text-muted-foreground">{hint}</p>}
      </CardContent>
    </Card>
  )
}

// ─── Loading ──────────────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: 4 }).map((_, i) => (
          <Skeleton key={i} className="h-28 rounded-xl" />
        ))}
      </div>
      <Skeleton className="h-48 rounded-xl" />
      <Skeleton className="h-48 rounded-xl" />
    </div>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function TeacherDashboardView() {
  useAuth()
  const dashApi = useApi<TeacherDashboard>(() => api.get('/api/dashboard/teacher/'), [])

  if (dashApi.isLoading) {
    return (
      <>
        <PageHeader title="Dashboard" description="Loading your supervision overview…" />
        <LoadingSkeleton />
      </>
    )
  }

  if (dashApi.error) {
    return (
      <>
        <PageHeader title="Dashboard" description="Your supervision overview." />
        <InlineError message={dashApi.error} />
      </>
    )
  }

  const d = dashApi.data
  if (!d) return null

  return (
    <>
      <PageHeader
        title="Dashboard"
        description={`Your supervision overview for academic year ${d.academic_year.year}.`}
      />

      {/* ── Counters ── */}
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <CounterCard
          icon={Users}
          label="Supervised teams"
          value={d.supervision.supervised_teams_count}
          hint={`${d.supervision.validated_supervised_teams_count} validated`}
        />
        <CounterCard
          icon={FileText}
          label="Pending reviews"
          value={d.deliverables.pending_review_count}
          tone={d.deliverables.pending_review_count > 0 ? 'warning' : 'neutral'}
          hint={
            d.deliverables.pending_review_count > 0
              ? 'Deliverable files awaiting your review'
              : 'No pending reviews — you are caught up.'
          }
        />
        <CounterCard
          icon={Inbox}
          label="Defense requests"
          value={d.defenses.pending_requests_count}
          tone={d.defenses.pending_requests_count > 0 ? 'warning' : 'neutral'}
          hint={
            d.defenses.pending_requests_count > 0
              ? 'Awaiting your accept or deny'
              : 'No defense requests pending.'
          }
        />
        <CounterCard
          icon={Calendar}
          label="Upcoming defenses"
          value={d.defenses.upcoming_count}
          hint="Where you are supervisor or jury"
        />
      </div>

      {/* ── Pending deliverable reviews ── */}
      <section className="mt-8 space-y-3">
        <h2 className="flex items-center gap-2 text-base font-semibold tracking-tight">
          <FileText className="size-4 text-muted-foreground" />
          Latest pending reviews
        </h2>
        <Card>
          {d.deliverables.latest_pending_review.length === 0 ? (
            <CardContent className="py-8">
              <EmptyState
                icon={FileText}
                title="No pending reviews"
                description="When your supervised teams upload deliverables, they appear here."
              />
            </CardContent>
          ) : (
            <ul className="divide-y divide-border">
              {d.deliverables.latest_pending_review.map(f => (
                <li
                  key={f.file_id}
                  className="flex items-center justify-between gap-3 px-4 py-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">
                      {f.original_filename}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      <span className="font-mono">{f.team_code}</span>
                      {' · uploaded by '}
                      {f.uploaded_by}
                      {' · '}
                      {formatDateTime(f.uploaded_at)}
                    </p>
                  </div>
                  <Link
                    href="/teacher/supervision"
                    className="shrink-0 text-xs font-medium text-primary underline-offset-4 hover:underline"
                  >
                    Review →
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>
      </section>

      {/* ── Upcoming defenses ── */}
      <section className="mt-6 space-y-3">
        <h2 className="flex items-center gap-2 text-base font-semibold tracking-tight">
          <Award className="size-4 text-muted-foreground" />
          Upcoming defenses
        </h2>
        <Card>
          {d.defenses.upcoming.length === 0 ? (
            <CardContent className="py-8">
              <EmptyState
                icon={Calendar}
                title="No upcoming defenses"
                description="Scheduled defenses where you are supervisor or jury appear here."
              />
            </CardContent>
          ) : (
            <ul className="divide-y divide-border">
              {d.defenses.upcoming.map(def => (
                <li
                  key={def.defense_id}
                  className="flex items-center justify-between gap-3 px-4 py-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">
                      {def.team_name}
                      <span className="ml-1.5 font-mono text-xs font-normal text-muted-foreground">
                        {def.team_code}
                      </span>
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {formatDate(def.scheduled_at)}
                      {def.location && ` · ${def.location}`}
                    </p>
                  </div>
                  <RoleBadge context={def.role_context} />
                </li>
              ))}
            </ul>
          )}
        </Card>
      </section>

      {/* ── Quick actions ── */}
      <section className="mt-8 space-y-3">
        <h2 className="text-base font-semibold tracking-tight">Quick links</h2>
        <div className="flex flex-wrap gap-2">
          <Link
            href="/teacher/subjects"
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted"
          >
            My subjects
          </Link>
          <Link
            href="/teacher/supervision"
            className="inline-flex items-center gap-2 rounded-lg border border-border bg-card px-3 py-1.5 text-sm font-medium text-foreground hover:bg-muted"
          >
            <Eye className="size-4" />
            Supervision
          </Link>
        </div>
      </section>
    </>
  )
}

// ─── Role badge ───────────────────────────────────────────────────────────────

function RoleBadge({ context }: { context: 'SUPERVISOR' | 'JURY' | 'SUPERVISOR,JURY' }) {
  const label =
    context === 'SUPERVISOR,JURY' ? 'Supervisor · Jury' : context === 'SUPERVISOR' ? 'Supervisor' : 'Jury'
  return (
    <span className="shrink-0 rounded-md border border-status-neutral-border bg-status-neutral-bg px-2 py-0.5 text-xs font-medium text-status-neutral-fg">
      {label}
    </span>
  )
}
