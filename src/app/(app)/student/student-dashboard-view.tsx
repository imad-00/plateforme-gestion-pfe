'use client'

import Link from 'next/link'
import {
  AlertCircle,
  Award,
  BookOpen,
  Clock,
  FileText,
  Upload,
  Users,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type { StudentDashboard } from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/shared/status-badge'
import { EmptyState } from '@/components/shared/empty-state'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) {
    const d = err.data as Record<string, unknown>
    const first = Object.values(d).flat().find(v => typeof v === 'string')
    return (first as string | undefined) ?? err.message
  }
  return err instanceof Error ? err.message : 'An unexpected error occurred.'
}

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
  return new Date(iso).toLocaleString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const SUBJECT_TYPE_LABELS: Record<string, string> = {
  RESEARCH_PROJECT: 'Research',
  APPLIED_PROJECT: 'Applied',
  STARTUP_PROJECT: 'Startup',
}

const ROUND_LABELS: Record<string, string> = {
  FIRST: 'Round 1',
  SECOND: 'Round 2',
}

// ─── Loading ──────────────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <div className="grid gap-4 lg:grid-cols-2">
        <Skeleton className="h-48 rounded-xl" />
        <Skeleton className="h-48 rounded-xl" />
      </div>
      <Skeleton className="h-32 rounded-xl" />
      <Skeleton className="h-48 rounded-xl" />
    </div>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function StudentDashboardView() {
  useAuth()
  const dashApi = useApi<StudentDashboard>(() => api.get('/api/dashboard/student/'), [])

  if (dashApi.isLoading) {
    return (
      <>
        <PageHeader title="Dashboard" description="Loading your overview…" />
        <LoadingSkeleton />
      </>
    )
  }

  if (dashApi.error) {
    return (
      <>
        <PageHeader title="Dashboard" description="Your overview." />
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
        description={`Your overview for academic year ${d.academic_year.year}.`}
      />

      {/* ── Team + Subject side by side ── */}
      <div className="grid gap-4 lg:grid-cols-2">
        {/* Team */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0">
            <CardTitle className="flex items-center gap-2 text-base">
              <Users className="size-4 text-muted-foreground" />
              My team
            </CardTitle>
            {d.team && <StatusBadge status={d.team.status} />}
          </CardHeader>
          <CardContent>
            {d.team === null ? (
              <EmptyState
                icon={Users}
                title="No team yet"
                description="When you join or form a team, it will appear here."
                action={
                  <Button asChild size="sm">
                    <Link href="/student/team">Go to My Team</Link>
                  </Button>
                }
              />
            ) : (
              <div className="space-y-3">
                <div>
                  <p className="text-lg font-semibold tracking-tight">{d.team.name}</p>
                  <p className="font-mono text-xs text-muted-foreground">
                    {d.team.team_code} · you are{' '}
                    <span className="font-sans font-semibold text-foreground">
                      {d.team.role === 'LEADER' ? 'Leader' : 'Member'}
                    </span>
                  </p>
                </div>

                <div className="space-y-1.5">
                  <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Members ({d.team.members.length})
                  </p>
                  <ul className="space-y-1 text-sm">
                    {d.team.members.map(m => (
                      <li key={m.id} className="flex items-center justify-between">
                        <span>{m.name}</span>
                        {m.role === 'LEADER' && (
                          <span className="text-xs font-medium text-primary">Leader</span>
                        )}
                      </li>
                    ))}
                  </ul>
                </div>

                {d.team.supervisors.length > 0 && (
                  <div className="space-y-1.5">
                    <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                      Supervisors ({d.team.supervisors.length})
                    </p>
                    <ul className="space-y-1 text-sm">
                      {d.team.supervisors.map(s => (
                        <li key={s.id}>{s.name}</li>
                      ))}
                    </ul>
                  </div>
                )}

                <Button asChild variant="outline" size="sm">
                  <Link href="/student/team">Manage team</Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Assigned subject */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0">
            <CardTitle className="flex items-center gap-2 text-base">
              <BookOpen className="size-4 text-muted-foreground" />
              Assigned subject
            </CardTitle>
            {d.assignment.selection_round && (
              <span className="rounded-md border border-status-neutral-border bg-status-neutral-bg px-2 py-0.5 text-xs font-medium text-status-neutral-fg">
                {ROUND_LABELS[d.assignment.selection_round] ?? d.assignment.selection_round}
              </span>
            )}
          </CardHeader>
          <CardContent>
            {d.subject === null ? (
              <EmptyState
                icon={BookOpen}
                title="No assigned subject yet"
                description={
                  d.assignment.assigned
                    ? 'Subject is pending — try refreshing.'
                    : 'Your subject will appear here once assignment is published.'
                }
                action={
                  <Button asChild variant="outline" size="sm">
                    <Link href="/student/results">Check results</Link>
                  </Button>
                }
              />
            ) : (
              <div className="space-y-3">
                <div>
                  <p className="text-lg font-semibold tracking-tight">{d.subject.title}</p>
                  <p className="text-xs text-muted-foreground">
                    {SUBJECT_TYPE_LABELS[d.subject.type] ?? d.subject.type}
                    {' · '}
                    <StatusBadge status={d.subject.status} />
                  </p>
                </div>
                <Button asChild variant="outline" size="sm">
                  <Link href="/student/results">View result</Link>
                </Button>
              </div>
            )}
          </CardContent>
        </Card>
      </div>

      {/* ── Defense status ── */}
      {d.defense && (
        <section className="mt-4">
          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-2 space-y-0 pb-2">
              <CardTitle className="flex items-center gap-2 text-base">
                <Award className="size-4 text-muted-foreground" />
                Defense
              </CardTitle>
              <StatusBadge status={d.defense.status} />
            </CardHeader>
            <CardContent className="space-y-1 text-sm">
              {d.defense.scheduled_at && (
                <p className="flex items-center gap-2 text-muted-foreground">
                  <Clock className="size-3.5" />
                  {formatDateTime(d.defense.scheduled_at)}
                  {d.defense.location && ` · ${d.defense.location}`}
                </p>
              )}
              {d.defense.final_grade && (
                <p className="text-sm">
                  <span className="text-muted-foreground">Final grade: </span>
                  <span className="font-semibold tabular-nums">{d.defense.final_grade}</span>
                  {' / 20'}
                </p>
              )}
              {d.defense.pv_uploaded && (
                <p className="text-xs text-status-success-fg">PV uploaded ✓</p>
              )}
            </CardContent>
          </Card>
        </section>
      )}

      {/* ── Latest deliverables ── */}
      <section className="mt-6 space-y-3">
        <h2 className="flex items-center gap-2 text-base font-semibold tracking-tight">
          <FileText className="size-4 text-muted-foreground" />
          Latest deliverables
          {d.deliverables.total_files > 0 && (
            <span className="text-sm font-normal text-muted-foreground">
              ({d.deliverables.total_files} total)
            </span>
          )}
        </h2>
        <Card>
          {d.deliverables.latest.length === 0 ? (
            <CardContent className="py-8">
              <EmptyState
                icon={Upload}
                title="No deliverables uploaded"
                description="Once your team uploads files, the latest 5 appear here."
                action={
                  d.team !== null && d.assignment.assigned ? (
                    <Button asChild size="sm">
                      <Link href="/student/deliverables">Upload a deliverable</Link>
                    </Button>
                  ) : undefined
                }
              />
            </CardContent>
          ) : (
            <ul className="divide-y divide-border">
              {d.deliverables.latest.map(f => (
                <li
                  key={f.file_id}
                  className="flex items-center justify-between gap-3 px-4 py-3"
                >
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">
                      {f.original_filename}
                    </p>
                    <p className="truncate text-xs text-muted-foreground">
                      {formatDateTime(f.uploaded_at)} · by {f.uploaded_by}
                    </p>
                  </div>
                  <StatusBadge status={f.review_status} />
                </li>
              ))}
            </ul>
          )}
        </Card>
      </section>
    </>
  )
}
