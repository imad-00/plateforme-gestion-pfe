'use client'

import Link from 'next/link'
import { useState } from 'react'
import {
  AlertCircle,
  Archive,
  ArrowRight,
  CalendarDays,
  ChevronDown,
  ChevronRight,
  FileBarChart,
  Hourglass,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type {
  AcademicYear,
  CampaignPhase,
  PaginatedResponse,
  PhaseType,
} from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { EmptyState } from '@/components/shared/empty-state'
import { StatusBadge } from '@/components/shared/status-badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

// Reuse the same labels we render in the main academic-years view so the
// phase names are consistent across both surfaces.
const PHASE_LABELS: Record<PhaseType, string> = {
  CAMPAIGN_SETUP: 'Campaign Setup',
  SUBJECT_MANAGEMENT: 'Subject Management',
  TEAM_FORMATION: 'Team Formation',
  WISHLIST_1: 'Wishlist — Round 1',
  ASSIGNMENT_REVIEW_1: 'Assignment Review — Round 1',
  RESULTS_AND_APPEALS: 'Results & Appeals',
  WISHLIST_2: 'Wishlist — Round 2',
  ASSIGNMENT_REVIEW_2: 'Assignment Review — Round 2',
  WORK_AND_SUPERVISION: 'Work & Supervision',
  DEFENSE_WINDOW: 'Defense Window',
  ARCHIVE: 'Archive',
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

// ─── Phase summary (read-only) ────────────────────────────────────────────────

function PhaseHistoryList({ yearId }: { yearId: number }) {
  const phasesApi = useApi<PaginatedResponse<CampaignPhase>>(
    () => api.get(`/api/admin/campaign-phases/?academic_year=${yearId}&page_size=100`),
    [yearId],
  )

  if (phasesApi.isLoading) return <Skeleton className="h-32 w-full rounded-lg" />
  if (phasesApi.error) return <InlineError message={phasesApi.error} />

  const records = phasesApi.data?.results ?? []
  if (records.length === 0) {
    return <p className="text-sm text-muted-foreground">No phase records for this year.</p>
  }

  // Sort by display_order so the timeline reads top to bottom in campaign order.
  const sorted = [...records].sort((a, b) => a.display_order - b.display_order)

  return (
    <div className="space-y-1.5">
      {sorted.map(p => (
        <div
          key={p.id}
          className="flex items-center gap-3 rounded-lg border border-border bg-card p-2.5 text-xs"
        >
          <span className="size-6 shrink-0 rounded-md bg-muted text-center font-medium leading-6 text-muted-foreground">
            {p.display_order}
          </span>
          <div className="min-w-0 flex-1">
            <p className="truncate text-sm font-medium text-foreground">{PHASE_LABELS[p.phase_type]}</p>
            <p className="text-muted-foreground">
              {formatDateTime(p.start_at)} → {p.end_at ? formatDateTime(p.end_at) : 'open-ended'}
            </p>
          </div>
          {p.is_archived && <StatusBadge status="ARCHIVED" />}
        </div>
      ))}
    </div>
  )
}

// ─── Year row ─────────────────────────────────────────────────────────────────

function YearHistoryRow({ year }: { year: AcademicYear }) {
  const [expanded, setExpanded] = useState(false)
  const Icon = year.status === 'ARCHIVED' ? Archive : Hourglass

  return (
    <Card>
      <CardContent className="space-y-3">
        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <Icon className="size-4 text-muted-foreground" />
              <span className="font-mono text-sm font-semibold text-foreground">{year.year}</span>
              <StatusBadge status={year.status} />
            </div>
            <p className="text-sm text-foreground">{year.year_label}</p>
            <p className="text-xs text-muted-foreground">
              {formatDate(year.start_date)} → {formatDate(year.end_date)}
              {' · '}Wishlist size: {year.wishlist_size}
            </p>
          </div>

          <div className="flex shrink-0 flex-wrap items-center gap-2">
            <Link href={`/admin/reports?year=${year.id}`}>
              <Button variant="outline" size="sm">
                <FileBarChart className="size-3.5" />
                Reports
              </Button>
            </Link>
            <Button variant="ghost" size="sm" onClick={() => setExpanded(v => !v)}>
              {expanded ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
              Phases
            </Button>
          </div>
        </div>

        {expanded && (
          <div>
            <p className="mb-2 text-xs font-medium uppercase tracking-wider text-muted-foreground">
              Phase schedule snapshot
            </p>
            <PhaseHistoryList yearId={year.id} />
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function HistoryView() {
  useAuth()

  // include_archived=true returns ARCHIVED rows too. We then filter to
  // CLOSED + ARCHIVED so the ACTIVE year (which lives at /admin/academic-years)
  // doesn't show up twice across pages.
  const yearsApi = useApi<PaginatedResponse<AcademicYear>>(
    () => api.get('/api/admin/academic-years/?include_archived=true&page_size=100'),
    [],
  )

  const years = (yearsApi.data?.results ?? []).filter(
    y => y.status === 'CLOSED' || y.status === 'ARCHIVED',
  )

  return (
    <>
      <PageHeader
        title="History"
        description="Closed and archived academic years. Read-only — operational actions live in the current campaign workspace."
      />

      {yearsApi.isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-24 w-full rounded-xl" />
          <Skeleton className="h-24 w-full rounded-xl" />
        </div>
      ) : yearsApi.error ? (
        <InlineError message={yearsApi.error} />
      ) : years.length === 0 ? (
        <EmptyState
          icon={CalendarDays}
          title="No history yet"
          description="Years move here once they are closed or archived."
          action={
            <Link href="/admin/academic-years">
              <Button variant="outline" size="sm">
                Go to current year
                <ArrowRight className="size-3.5" />
              </Button>
            </Link>
          }
        />
      ) : (
        <div className="space-y-3">
          {years.map(y => (
            <YearHistoryRow key={y.id} year={y} />
          ))}
        </div>
      )}
    </>
  )
}
