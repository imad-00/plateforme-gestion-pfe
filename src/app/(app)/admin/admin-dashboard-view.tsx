'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  AlertCircle,
  Award,
  BookOpen,
  CalendarDays,
  CheckCircle2,
  ClipboardList,
  Gavel,
  Layers,
  Loader2,
  Mail,
  Upload,
  Users,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type { AdminDashboard } from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'


function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

// ─── Stat card ────────────────────────────────────────────────────────────────
// One headline number + optional breakdown chips below. Drill-down link is
// optional — used to push admin to the page that resolves the metric.

interface StatBreakdown {
  label: string
  value: number
  tone?: 'success' | 'warning' | 'error' | 'neutral'
}

function StatCard({
  icon: Icon,
  label,
  value,
  breakdown,
  href,
}: {
  icon: React.ComponentType<{ className?: string }>
  label: string
  value: number
  breakdown?: StatBreakdown[]
  href?: string
}) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {label}
        </CardTitle>
        <Icon className="size-4 text-muted-foreground" />
      </CardHeader>
      <CardContent className="space-y-3">
        <div className="text-2xl font-bold tabular-nums tracking-tight">{value}</div>
        {breakdown && breakdown.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {breakdown.map(b => (
              <BreakdownChip key={b.label} {...b} />
            ))}
          </div>
        )}
        {href && (
          <Link
            href={href}
            className="inline-block text-xs font-medium text-primary underline-offset-4 hover:underline"
          >
            View details →
          </Link>
        )}
      </CardContent>
    </Card>
  )
}

function BreakdownChip({ label, value, tone = 'neutral' }: StatBreakdown) {
  const toneClasses: Record<NonNullable<StatBreakdown['tone']>, string> = {
    success: 'bg-status-success-bg text-status-success-fg border-status-success-border',
    warning: 'bg-status-warning-bg text-status-warning-fg border-status-warning-border',
    error: 'bg-status-error-bg text-status-error-fg border-status-error-border',
    neutral: 'bg-status-neutral-bg text-status-neutral-fg border-status-neutral-border',
  }
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-md border px-1.5 py-0.5 text-xs font-medium ${toneClasses[tone]}`}
    >
      <span>{label}</span>
      <span className="tabular-nums">{value}</span>
    </span>
  )
}

// ─── Loading + empty year ─────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {Array.from({ length: 6 }).map((_, i) => (
        <Skeleton key={i} className="h-32 w-full rounded-xl" />
      ))}
    </div>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function AdminDashboardView() {
  useAuth()

  const dashApi = useApi<AdminDashboard>(() => api.get('/api/dashboard/admin/'), [])

  if (dashApi.isLoading) {
    return (
      <>
        <PageHeader title="Dashboard" description="Loading administrative overview…" />
        <LoadingSkeleton />
      </>
    )
  }

  if (dashApi.error) {
    return (
      <>
        <PageHeader title="Dashboard" description="Administrative overview." />
        <InlineError message={dashApi.error} />
      </>
    )
  }

  const d = dashApi.data
  if (!d) return null

  const yearLabel = d.academic_year.year

  return (
    <>
      <PageHeader
        title="Dashboard"
        description={`Overview for academic year ${yearLabel}.`}
      />

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
        <StatCard
          icon={Users}
          label="Teams"
          value={d.teams.total}
          breakdown={[
            { label: 'Forming', value: d.teams.forming, tone: 'warning' },
            { label: 'Locked', value: d.teams.locked, tone: 'warning' },
            { label: 'Validated', value: d.teams.validated, tone: 'success' },
            { label: 'Dissolved', value: d.teams.dissolved, tone: 'error' },
          ]}
          href="/admin/teams"
        />

        <StatCard
          icon={ClipboardList}
          label="Assignments"
          value={d.assignments.assigned + d.assignments.unassigned}
          breakdown={[
            { label: 'Assigned', value: d.assignments.assigned, tone: 'success' },
            { label: 'Unassigned', value: d.assignments.unassigned, tone: 'neutral' },
          ]}
          href="/admin/assignments"
        />

        <StatCard
          icon={BookOpen}
          label="Subjects"
          value={d.subjects.total}
          breakdown={[
            { label: 'Approved', value: d.subjects.approved, tone: 'success' },
            { label: 'Submitted', value: d.subjects.submitted, tone: 'warning' },
            { label: 'Assigned', value: d.subjects.assigned, tone: 'neutral' },
            { label: 'Draft', value: d.subjects.draft, tone: 'neutral' },
            { label: 'Rejected', value: d.subjects.rejected, tone: 'error' },
          ]}
          href="/admin/subjects"
        />

        <StatCard
          icon={Gavel}
          label="Appeals"
          value={d.appeals.total}
          breakdown={[
            { label: 'Pending', value: d.appeals.pending_or_submitted, tone: 'warning' },
            { label: 'Accepted', value: d.appeals.accepted, tone: 'success' },
            { label: 'Rejected', value: d.appeals.rejected, tone: 'error' },
          ]}
          href="/admin/assignments"
        />

        <StatCard
          icon={Upload}
          label="Deliverables"
          value={d.deliverables.total_files}
          breakdown={[
            { label: 'Pending review', value: d.deliverables.pending_review, tone: 'warning' },
            { label: 'Accepted', value: d.deliverables.accepted, tone: 'success' },
            { label: 'Needs revision', value: d.deliverables.needs_revision, tone: 'warning' },
            { label: 'Rejected', value: d.deliverables.rejected, tone: 'error' },
          ]}
        />

        <StatCard
          icon={Award}
          label="Defenses"
          value={d.defenses.total}
          breakdown={[
            { label: 'Requested', value: d.defenses.requested, tone: 'warning' },
            { label: 'Ready', value: d.defenses.ready_to_schedule, tone: 'warning' },
            { label: 'Scheduled', value: d.defenses.scheduled, tone: 'success' },
            { label: 'Completed', value: d.defenses.completed, tone: 'success' },
            { label: 'Cancelled', value: d.defenses.cancelled, tone: 'error' },
          ]}
        />
      </div>

      {/* Quick actions */}
      <section className="mt-8 space-y-3">
        <h2 className="flex items-center gap-2 text-base font-semibold tracking-tight">
          <Layers className="size-4 text-muted-foreground" />
          Quick actions
        </h2>
        <div className="flex flex-wrap gap-2">
          <Button asChild variant="outline" size="sm">
            <Link href="/admin/users">Manage users</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/admin/academic-years">
              <CalendarDays className="size-4" />
              Academic years
            </Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/admin/subjects">Moderate subjects</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/admin/teams">Manage teams</Link>
          </Button>
          <Button asChild variant="outline" size="sm">
            <Link href="/admin/assignments">Run assignments</Link>
          </Button>
        </div>
      </section>

      <SystemDiagnostics />
    </>
  )
}

// ─── System diagnostics card ──────────────────────────────────────────────────
// Currently houses the "Send test email" button. Useful when the admin wants to
// confirm SMTP is wired up after changing email settings, without needing to
// trigger a real workflow event that flips a NotificationDelivery row.

function SystemDiagnostics() {
  const [loading, setLoading] = useState(false)
  const [feedback, setFeedback] = useState<
    | { kind: 'ok'; message: string }
    | { kind: 'error'; message: string }
    | null
  >(null)

  async function handleSendTest() {
    setLoading(true)
    setFeedback(null)
    try {
      const res = await api.post<{ detail: string }>(
        '/api/admin/notifications/test-email/',
      )
      setFeedback({ kind: 'ok', message: res.detail })
    } catch (err) {
      const message =
        err instanceof ApiClientError
          ? err.message
          : err instanceof Error
            ? err.message
            : 'Could not send test email.'
      setFeedback({ kind: 'error', message })
    } finally {
      setLoading(false)
    }
  }

  return (
    <section className="mt-8 space-y-3">
      <h2 className="flex items-center gap-2 text-base font-semibold tracking-tight">
        <Mail className="size-4 text-muted-foreground" />
        System diagnostics
      </h2>
      <Card>
        <CardContent className="flex flex-col gap-3 pt-5 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0 space-y-1">
            <p className="text-sm font-medium text-foreground">Send test email</p>
            <p className="text-xs text-muted-foreground">
              Sends a verification email to your own address using the current
              SMTP backend. Bypasses Celery — useful to prove email delivery
              works before triggering real workflow events.
            </p>
            {feedback && (
              <div
                className={[
                  'mt-2 flex items-start gap-2 rounded-lg p-2.5 text-xs',
                  feedback.kind === 'ok'
                    ? 'bg-status-success-bg text-status-success-fg'
                    : 'bg-status-error-bg text-status-error-fg',
                ].join(' ')}
              >
                {feedback.kind === 'ok' ? (
                  <CheckCircle2 className="mt-0.5 size-3.5 shrink-0" />
                ) : (
                  <AlertCircle className="mt-0.5 size-3.5 shrink-0" />
                )}
                <span>{feedback.message}</span>
              </div>
            )}
          </div>
          <Button size="sm" onClick={handleSendTest} disabled={loading} className="shrink-0">
            {loading ? <Loader2 className="size-4 animate-spin" /> : <Mail className="size-4" />}
            Send test email
          </Button>
        </CardContent>
      </Card>
    </section>
  )
}
