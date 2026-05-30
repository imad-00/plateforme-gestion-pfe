'use client'

import { useEffect, useState } from 'react'
import {
  AlertCircle,
  AlertTriangle,
  Archive,
  ArchiveRestore,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Clock,
  Loader2,
  Lock,
  Shield,
  ShieldAlert,
  Undo2,
  XCircle,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type {
  AcademicYear,
  CloseAndArchiveResponse,
  ClosureReadiness,
  ClosureReadinessIssue,
  LifecycleActionResponse,
  LifecycleEvent,
  LifecycleEventType,
  PaginatedResponse,
} from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { StatusBadge } from '@/components/shared/status-badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function humanize(code: string): string {
  return code
    .split('_')
    .map(w => w.charAt(0) + w.slice(1).toLowerCase())
    .join(' ')
}

function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) return err.message
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

// ─── Action type ──────────────────────────────────────────────────────────────

type LifecycleAction = 'close' | 'force-close' | 'reopen' | 'archive' | 'close-and-archive'

interface ActionConfig {
  title: string
  description: string
  confirmLabel: string
  destructive: boolean
  endpoint: (id: number) => string
  body: (reason: string) => Record<string, unknown>
}

const ACTION_CONFIG: Record<LifecycleAction, ActionConfig> = {
  close: {
    title: 'Close academic year',
    description:
      'Closing freezes open phases and stops new admin write actions. Cannot proceed if blocking issues remain. Reopening is allowed afterwards.',
    confirmLabel: 'Close year',
    destructive: false,
    endpoint: id => `/api/super-admin/academic-years/${id}/close/`,
    body: reason => ({ reason, confirm: true, force: false }),
  },
  'force-close': {
    title: 'Force-close academic year',
    description:
      'Force-close ignores blocking issues. Unresolved validated teams, in-flight defenses, and pending appeals will remain as-is. Use only when normal closure is intentionally being bypassed.',
    confirmLabel: 'Force close',
    destructive: true,
    endpoint: id => `/api/super-admin/academic-years/${id}/close/`,
    body: reason => ({ reason, confirm: true, force: true }),
  },
  reopen: {
    title: 'Reopen academic year',
    description:
      'Reopening flips the year back to ACTIVE. Fails if another year is already ACTIVE. Child statuses (teams, defenses, etc.) are not changed.',
    confirmLabel: 'Reopen year',
    destructive: false,
    endpoint: id => `/api/super-admin/academic-years/${id}/reopen/`,
    body: reason => ({ reason, confirm: true }),
  },
  archive: {
    title: 'Archive academic year',
    description:
      'Archiving is IRREVERSIBLE. Students and external supervisors tied only to this year will be SUSPENDED. Teachers and administrative staff are not affected. Files are preserved.',
    confirmLabel: 'Archive permanently',
    destructive: true,
    endpoint: id => `/api/super-admin/academic-years/${id}/archive/`,
    body: reason => ({ reason, confirm: true }),
  },
  'close-and-archive': {
    title: 'Close and archive academic year',
    description:
      'Combined close + archive in one step. ARCHIVE IS IRREVERSIBLE. Force-close is applied if normal closure is not possible.',
    confirmLabel: 'Close and archive',
    destructive: true,
    endpoint: id => `/api/super-admin/academic-years/${id}/close-and-archive/`,
    body: reason => ({ reason, confirm: true, force: false }),
  },
}

// ─── Lifecycle action dialog ─────────────────────────────────────────────────

function LifecycleActionDialog({
  action,
  yearId,
  open,
  onOpenChange,
  onSuccess,
}: {
  action: LifecycleAction | null
  yearId: number | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}) {
  const [reason, setReason] = useState('')
  const [understood, setUnderstood] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setReason('')
      setUnderstood(false)
      setError(null)
    }
  }, [open])

  if (!action || !yearId) return null
  const config = ACTION_CONFIG[action]

  async function handleSubmit() {
    if (!action || !yearId) return
    const trimmed = reason.trim()
    if (!trimmed) {
      setError('A human-readable reason is required.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await api.post<LifecycleActionResponse | CloseAndArchiveResponse>(
        config.endpoint(yearId),
        config.body(trimmed),
      )
      onSuccess()
      onOpenChange(false)
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={open => !loading && onOpenChange(open)}>
      <DialogContent className="max-w-lg" showCloseButton={false}>
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {config.destructive ? (
              <ShieldAlert className="size-4 text-status-error-fg" />
            ) : (
              <Shield className="size-4 text-primary" />
            )}
            {config.title}
          </DialogTitle>
          <DialogDescription>{config.description}</DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="lifecycle-reason">Reason</Label>
            <Textarea
              id="lifecycle-reason"
              rows={3}
              placeholder="Explain why this action is being taken. Recorded in the audit log."
              value={reason}
              onChange={e => setReason(e.target.value)}
              disabled={loading}
              className="resize-none"
            />
          </div>

          <label className="flex cursor-pointer items-start gap-2 text-sm">
            <input
              type="checkbox"
              checked={understood}
              onChange={e => setUnderstood(e.target.checked)}
              disabled={loading}
              className="mt-0.5 size-4 shrink-0 accent-primary"
            />
            <span className="text-foreground">
              I understand the consequences of this action.
              {config.destructive && (
                <span className="font-medium text-status-error-fg"> This may be irreversible.</span>
              )}
            </span>
          </label>

          {error && <InlineError message={error} />}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button
            variant={config.destructive ? 'destructive' : 'default'}
            onClick={handleSubmit}
            disabled={loading || !understood || !reason.trim()}
          >
            {loading && <Loader2 className="size-4 animate-spin" />}
            {config.confirmLabel}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Issue card (blocker or warning) ──────────────────────────────────────────

function flattenIssueIds(issue: ClosureReadinessIssue): string[] {
  return [
    ...(issue.team_codes ?? []),
    ...(issue.defense_ids ?? []),
    ...(issue.appeal_ids ?? []),
    ...(issue.subject_ids ?? []).map(String),
    ...(issue.phase_ids ?? []).map(String),
    ...(issue.file_ids ?? []),
  ]
}

function IssueRow({ issue, severity }: { issue: ClosureReadinessIssue; severity: 'block' | 'warn' }) {
  const [open, setOpen] = useState(false)
  const ids = flattenIssueIds(issue)
  const Icon = severity === 'block' ? XCircle : AlertTriangle
  const colorClasses =
    severity === 'block'
      ? 'border-status-error-border bg-status-error-bg/40 text-status-error-fg'
      : 'border-status-warning-border bg-status-warning-bg/40 text-status-warning-fg'

  return (
    <div className={`space-y-1.5 rounded-lg border p-3 ${colorClasses}`}>
      <div className="flex items-start gap-2">
        <Icon className="mt-0.5 size-4 shrink-0" />
        <div className="min-w-0 flex-1">
          <p className="text-sm font-medium">{humanize(issue.code)}</p>
          {issue.message && <p className="text-xs">{issue.message}</p>}
        </div>
        {ids.length > 0 && (
          <button
            type="button"
            onClick={() => setOpen(v => !v)}
            className="rounded p-0.5 hover:bg-card/60"
            aria-label={open ? 'Hide IDs' : `Show ${ids.length} IDs`}
          >
            {open ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
          </button>
        )}
      </div>
      {open && ids.length > 0 && (
        <div className="rounded bg-card/60 p-2 font-mono text-[11px]">
          {ids.join(', ')}
        </div>
      )}
    </div>
  )
}

// ─── Event timeline ───────────────────────────────────────────────────────────

function EventTypeIcon({ type }: { type: LifecycleEventType }) {
  if (type === 'CLOSED') return <Lock className="size-4 text-status-warning-fg" />
  if (type === 'FORCE_CLOSED') return <ShieldAlert className="size-4 text-status-error-fg" />
  if (type === 'REOPENED') return <Undo2 className="size-4 text-primary" />
  return <Archive className="size-4 text-status-error-fg" />
}

function EventTimelineRow({ event }: { event: LifecycleEvent }) {
  const [expanded, setExpanded] = useState(false)
  const hasMetadata = event.metadata && Object.keys(event.metadata).length > 0

  return (
    <div className="rounded-lg border border-border bg-card p-3">
      <div className="flex items-start gap-3">
        <EventTypeIcon type={event.event_type} />
        <div className="min-w-0 flex-1 space-y-0.5">
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-0.5">
            <p className="text-sm font-medium text-foreground">{humanize(event.event_type)}</p>
            <p className="text-xs text-muted-foreground">{formatDateTime(event.performed_at)}</p>
          </div>
          <p className="text-xs text-muted-foreground">
            by {event.performed_by.full_name} ({event.performed_by.matricule})
          </p>
          {event.reason && (
            <p className="whitespace-pre-line pt-1 text-sm text-foreground">{event.reason}</p>
          )}
        </div>
        {hasMetadata && (
          <button
            type="button"
            onClick={() => setExpanded(v => !v)}
            className="rounded p-0.5 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label={expanded ? 'Hide metadata' : 'Show metadata'}
          >
            {expanded ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
          </button>
        )}
      </div>
      {expanded && hasMetadata && (
        <pre className="mt-2 overflow-x-auto rounded bg-muted/30 p-2 font-mono text-[11px] text-foreground">
          {JSON.stringify(event.metadata, null, 2)}
        </pre>
      )}
    </div>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function LifecycleView() {
  const { user } = useAuth()
  const isSuperAdmin = user?.platform_access_level === 'SUPER_ADMIN'

  const yearsApi = useApi<PaginatedResponse<AcademicYear>>(
    () => api.get('/api/admin/academic-years/?page_size=100'),
    [],
  )

  const [yearId, setYearId] = useState<string>('')
  const [dialogAction, setDialogAction] = useState<LifecycleAction | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)

  const years = yearsApi.data?.results ?? []
  const fallbackYearId = yearId || String(years[0]?.id ?? '')
  const selectedYear = years.find(y => String(y.id) === fallbackYearId) ?? null

  // Backend enforces "reopen fails if another year is already ACTIVE" — mirror
  // that in the UI so admins don't try and only learn on submit.
  const anotherActiveYear =
    selectedYear !== null &&
    years.find(y => y.status === 'ACTIVE' && y.id !== selectedYear.id) !== undefined

  const readinessApi = useApi<ClosureReadiness>(
    () =>
      selectedYear
        ? api.get(`/api/super-admin/academic-years/${selectedYear.id}/closure-readiness/`)
        : Promise.resolve({} as ClosureReadiness),
    [selectedYear?.id, refreshKey],
  )

  const eventsApi = useApi<PaginatedResponse<LifecycleEvent>>(
    () =>
      selectedYear
        ? api.get(`/api/super-admin/academic-years/${selectedYear.id}/lifecycle-events/?page_size=50`)
        : Promise.resolve<PaginatedResponse<LifecycleEvent>>({
            count: 0,
            next: null,
            previous: null,
            results: [],
          }),
    [selectedYear?.id, refreshKey],
  )

  function handleActionSuccess() {
    setRefreshKey(k => k + 1)
    yearsApi.refetch()
  }

  if (!isSuperAdmin) {
    return (
      <>
        <PageHeader title="Lifecycle" description="Academic year closure and archive workspace." />
        <div className="flex items-start gap-2.5 rounded-lg border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
          <Lock className="mt-0.5 size-4 shrink-0" />
          <span>This workspace is reserved for super-admins.</span>
        </div>
      </>
    )
  }

  return (
    <>
      <PageHeader
        title="Lifecycle"
        description="Academic year closure, reopen, and archive. Destructive actions are recorded in the audit log."
      />

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">Academic year</p>
          <Select
            value={fallbackYearId}
            onValueChange={setYearId}
            disabled={yearsApi.isLoading}
          >
            <SelectTrigger className="w-64">
              <SelectValue placeholder="Select a year" />
            </SelectTrigger>
            <SelectContent>
              {years.map(y => (
                <SelectItem key={y.id} value={String(y.id)}>
                  {y.year_label || y.year} ({y.status.toLowerCase()})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
        {selectedYear && <StatusBadge status={selectedYear.status} />}
      </div>

      {!selectedYear ? (
        <p className="text-sm text-muted-foreground">Select an academic year above to begin.</p>
      ) : (
        <div className="space-y-4">
          {/* ── Action panel ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Actions</CardTitle>
            </CardHeader>
            <CardContent>
              {selectedYear.status === 'ACTIVE' && (
                <div className="flex flex-wrap gap-2">
                  <Button
                    onClick={() => setDialogAction('close')}
                    disabled={!readinessApi.data?.can_close_normally}
                  >
                    <Lock className="size-3.5" />
                    Close
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={() => setDialogAction('force-close')}
                    disabled={!readinessApi.data?.can_force_close}
                  >
                    <ShieldAlert className="size-3.5" />
                    Force close
                  </Button>
                  <Button
                    variant="destructive"
                    onClick={() => setDialogAction('close-and-archive')}
                  >
                    <Archive className="size-3.5" />
                    Close & archive
                  </Button>
                </div>
              )}
              {selectedYear.status === 'CLOSED' && (
                <div className="space-y-2">
                  <div className="flex flex-wrap gap-2">
                    <Button
                      onClick={() => setDialogAction('reopen')}
                      disabled={anotherActiveYear}
                    >
                      <ArchiveRestore className="size-3.5" />
                      Reopen
                    </Button>
                    <Button variant="destructive" onClick={() => setDialogAction('archive')}>
                      <Archive className="size-3.5" />
                      Archive
                    </Button>
                  </div>
                  {anotherActiveYear && (
                    <p className="text-xs text-muted-foreground">
                      Cannot reopen — another academic year is already active. Close it first
                      from its own lifecycle workspace.
                    </p>
                  )}
                </div>
              )}
              {selectedYear.status === 'ARCHIVED' && (
                <p className="text-sm text-muted-foreground">
                  This year is archived. No further lifecycle actions are available.
                </p>
              )}
            </CardContent>
          </Card>

          {/* ── Readiness ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Closure readiness</CardTitle>
            </CardHeader>
            <CardContent>
              {readinessApi.isLoading ? (
                <Skeleton className="h-32 w-full rounded-lg" />
              ) : readinessApi.error ? (
                <InlineError message={readinessApi.error} />
              ) : readinessApi.data ? (
                <ReadinessPanel readiness={readinessApi.data} />
              ) : null}
            </CardContent>
          </Card>

          {/* ── Event timeline ── */}
          <Card>
            <CardHeader>
              <CardTitle className="text-base">Event timeline</CardTitle>
            </CardHeader>
            <CardContent>
              {eventsApi.isLoading ? (
                <Skeleton className="h-32 w-full rounded-lg" />
              ) : eventsApi.error ? (
                <InlineError message={eventsApi.error} />
              ) : (eventsApi.data?.results.length ?? 0) === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No lifecycle events recorded yet for this year.
                </p>
              ) : (
                <div className="space-y-2">
                  {eventsApi.data!.results.map(e => (
                    <EventTimelineRow key={e.id} event={e} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      <LifecycleActionDialog
        action={dialogAction}
        yearId={selectedYear?.id ?? null}
        open={dialogAction !== null}
        onOpenChange={open => {
          if (!open) setDialogAction(null)
        }}
        onSuccess={handleActionSuccess}
      />
    </>
  )
}

// ─── Readiness panel (split out for clarity) ──────────────────────────────────

function ReadinessPanel({ readiness }: { readiness: ClosureReadiness }) {
  const [showEntities, setShowEntities] = useState(false)
  const totalBlockingIds = readiness.blocking_issues.length
  const totalWarningIds = readiness.warnings.length
  const suspendStudents = readiness.affected_entities.students_that_would_be_suspended_on_archive.length
  const suspendExternals = readiness.affected_entities.external_supervisors_that_would_be_suspended_on_archive.length

  return (
    <div className="space-y-4">
      {/* Top status */}
      <div className="flex flex-wrap items-center gap-3">
        {readiness.can_close_normally ? (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-status-success-border bg-status-success-bg px-2.5 py-1 text-xs font-medium text-status-success-fg">
            <CheckCircle2 className="size-3.5" />
            Can close normally
          </span>
        ) : readiness.can_force_close ? (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-status-warning-border bg-status-warning-bg px-2.5 py-1 text-xs font-medium text-status-warning-fg">
            <AlertTriangle className="size-3.5" />
            Force close only
          </span>
        ) : (
          <span className="inline-flex items-center gap-1.5 rounded-full border border-status-neutral-border bg-status-neutral-bg px-2.5 py-1 text-xs font-medium text-status-neutral-fg">
            <Clock className="size-3.5" />
            Not in a closable state
          </span>
        )}
      </div>

      {/* Summary */}
      <div className="grid gap-2 sm:grid-cols-3 lg:grid-cols-5">
        <SummaryStat label="Open phases" value={readiness.summary.open_phases} />
        <SummaryStat label="Pending appeals" value={readiness.summary.appeals_pending} />
        <SummaryStat
          label="Teams (total)"
          value={Object.values(readiness.summary.teams_by_status).reduce((a, b) => a + b, 0)}
        />
        <SummaryStat
          label="Defenses (total)"
          value={Object.values(readiness.summary.defenses_by_status).reduce((a, b) => a + b, 0)}
        />
        <SummaryStat
          label="Subjects (total)"
          value={Object.values(readiness.summary.subjects_by_status).reduce((a, b) => a + b, 0)}
        />
      </div>

      {/* Blocking issues */}
      {totalBlockingIds > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-foreground">
            Blocking issues
            <span className="ml-2 font-normal text-muted-foreground">({totalBlockingIds})</span>
          </h3>
          {readiness.blocking_issues.map((i, idx) => (
            <IssueRow key={`${i.code}-${idx}`} issue={i} severity="block" />
          ))}
        </div>
      )}

      {/* Warnings */}
      {totalWarningIds > 0 && (
        <div className="space-y-2">
          <h3 className="text-sm font-medium text-foreground">
            Warnings
            <span className="ml-2 font-normal text-muted-foreground">({totalWarningIds})</span>
          </h3>
          {readiness.warnings.map((i, idx) => (
            <IssueRow key={`${i.code}-${idx}`} issue={i} severity="warn" />
          ))}
        </div>
      )}

      {/* Affected entities (archive consequences) */}
      <div className="rounded-lg border border-border bg-muted/30 p-3">
        <button
          type="button"
          onClick={() => setShowEntities(v => !v)}
          className="flex w-full items-center justify-between text-sm font-medium text-foreground"
        >
          <span>
            On archive: {suspendStudents} student{suspendStudents === 1 ? '' : 's'} +{' '}
            {suspendExternals} external supervisor{suspendExternals === 1 ? '' : 's'} would be suspended
          </span>
          {showEntities ? (
            <ChevronDown className="size-3.5 text-muted-foreground" />
          ) : (
            <ChevronRight className="size-3.5 text-muted-foreground" />
          )}
        </button>
        {showEntities && (
          <div className="mt-2 space-y-2 text-xs text-muted-foreground">
            <EntityList
              label="Students that would be suspended"
              ids={readiness.affected_entities.students_that_would_be_suspended_on_archive.map(String)}
            />
            <EntityList
              label="External supervisors that would be suspended"
              ids={readiness.affected_entities.external_supervisors_that_would_be_suspended_on_archive.map(String)}
            />
            <EntityList
              label="Forming teams"
              ids={readiness.affected_entities.forming_team_codes}
            />
            <EntityList
              label="Locked teams"
              ids={readiness.affected_entities.locked_team_codes}
            />
            <EntityList
              label="Validated teams without completed defense"
              ids={readiness.affected_entities.validated_without_completed_defense_team_codes}
            />
          </div>
        )}
      </div>
    </div>
  )
}

function SummaryStat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-lg border border-border bg-card p-2.5">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="text-lg font-semibold text-foreground">{value}</p>
    </div>
  )
}

function EntityList({ label, ids }: { label: string; ids: string[] }) {
  if (ids.length === 0) return null
  return (
    <div>
      <p className="font-medium text-foreground">
        {label} <span className="font-normal">({ids.length})</span>
      </p>
      <p className="break-words font-mono text-[11px]">{ids.join(', ')}</p>
    </div>
  )
}
