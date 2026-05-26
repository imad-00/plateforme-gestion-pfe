'use client'

import { useEffect, useState } from 'react'
import { AlertCircle, BookOpen, Loader2, MoreHorizontal } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type {
  AcademicYear,
  PaginatedResponse,
  Subject,
  SubjectStatus,
  SubjectType,
} from '@/lib/types'
import { DataTable } from '@/components/shared/data-table'
import { EmptyState } from '@/components/shared/empty-state'
import { StatusBadge } from '@/components/shared/status-badge'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Textarea } from '@/components/ui/textarea'

// ─── Constants ────────────────────────────────────────────────────────────────

const SUBJECT_TYPE_LABELS: Record<SubjectType, string> = {
  RESEARCH_PROJECT: 'Research',
  APPLIED_PROJECT: 'Applied',
  STARTUP_PROJECT: 'Startup',
}

const SUBJECT_TYPE_CLASSES: Record<SubjectType, string> = {
  RESEARCH_PROJECT: 'bg-violet-50 text-violet-700 border-violet-200',
  APPLIED_PROJECT: 'bg-sky-50 text-sky-700 border-sky-200',
  STARTUP_PROJECT: 'bg-emerald-50 text-emerald-700 border-emerald-200',
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) {
    const d = err.data as Record<string, unknown>
    const first = Object.values(d).flat().find(v => typeof v === 'string')
    return (first as string | undefined) ?? err.message
  }
  return err instanceof Error ? err.message : 'An unexpected error occurred.'
}

// ─── Shared UI ────────────────────────────────────────────────────────────────

function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

function SubjectTypeBadge({ type }: { type: SubjectType }) {
  return (
    <span
      className={`inline-flex items-center rounded-full border px-2 py-0.5 text-xs font-medium ${SUBJECT_TYPE_CLASSES[type]}`}
    >
      {SUBJECT_TYPE_LABELS[type]}
    </span>
  )
}

// ─── Reject dialog ────────────────────────────────────────────────────────────

function RejectDialog({
  subject,
  open,
  onOpenChange,
  onSuccess,
}: {
  subject: Subject | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}) {
  const [reason, setReason] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setReason('')
    setError(null)
    setLoading(false)
  }, [open])

  async function handleReject() {
    if (!subject) return
    setLoading(true)
    setError(null)
    try {
      await api.post(`/api/admin/subjects/${subject.id}/reject/`, { reason })
      onSuccess()
      onOpenChange(false)
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={loading ? undefined : onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Reject Subject</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {subject && (
            <p className="text-sm text-muted-foreground">
              Rejecting{' '}
              <span className="font-medium text-foreground">
                {subject.subject_code ? `[${subject.subject_code}] ` : ''}{subject.title}
              </span>
            </p>
          )}
          <div className="space-y-1.5">
            <Label htmlFor="reject-reason">
              Reason{' '}
              <span className="font-normal text-muted-foreground">(optional)</span>
            </Label>
            <Textarea
              id="reject-reason"
              placeholder="Explain why the subject is being rejected…"
              value={reason}
              onChange={e => setReason(e.target.value)}
              className="min-h-24"
            />
          </div>
        </div>

        {error && <InlineError message={error} />}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button variant="destructive" onClick={handleReject} disabled={loading}>
            {loading && <Loader2 className="size-4 animate-spin" />}
            Reject Subject
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Subject detail dialog ────────────────────────────────────────────────────

function SubjectDetailDialog({
  subject,
  open,
  onOpenChange,
}: {
  subject: Subject | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  if (!subject) return null
  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="leading-snug">
            {subject.subject_code && (
              <span className="mr-2 font-mono text-base font-normal text-muted-foreground">
                {subject.subject_code}
              </span>
            )}
            {subject.title}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4 text-sm">
          <div className="flex flex-wrap gap-2">
            <SubjectTypeBadge type={subject.subject_type} />
            <StatusBadge status={subject.status} />
          </div>

          <p className="text-muted-foreground leading-relaxed">{subject.description}</p>

          <div className="grid grid-cols-2 gap-x-4 gap-y-2 border-t border-border pt-4">
            <div>
              <p className="text-xs font-medium text-muted-foreground">Proposed by</p>
              <p className="text-sm text-foreground">
                {subject.proposed_by.first_name} {subject.proposed_by.last_name}
              </p>
              <p className="text-xs text-muted-foreground">{subject.proposed_by.email}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground">Academic year</p>
              <p className="text-sm text-foreground">{subject.academic_year.year}</p>
            </div>
            <div>
              <p className="text-xs font-medium text-muted-foreground">Submitted</p>
              <p className="text-sm text-foreground">{formatDate(subject.submitted_at)}</p>
            </div>
            {subject.rejection_reason && (
              <div className="col-span-2">
                <p className="text-xs font-medium text-muted-foreground">Rejection reason</p>
                <p className="text-sm text-status-error-fg">{subject.rejection_reason}</p>
              </div>
            )}
            {subject.assigned_to_team && (
              <div>
                <p className="text-xs font-medium text-muted-foreground">Assigned to team</p>
                <p className="font-mono text-sm text-foreground">{subject.assigned_to_team}</p>
              </div>
            )}
          </div>

          {subject.attachment_url && (
            <div className="border-t border-border pt-3">
              <a
                href={subject.attachment_url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-sm text-primary hover:underline"
              >
                {subject.attachment_original_name ?? 'View attachment'}
              </a>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Row actions ──────────────────────────────────────────────────────────────

function SubjectRowActions({
  subject,
  onView,
  onApprove,
  onReject,
  onArchive,
}: {
  subject: Subject
  onView: (s: Subject) => void
  onApprove: (s: Subject) => void
  onReject: (s: Subject) => void
  onArchive: (s: Subject) => void
}) {
  const canApprove = subject.status === 'SUBMITTED'
  const canReject = subject.status === 'SUBMITTED'
  const canArchive = subject.status === 'APPROVED' || subject.status === 'REJECTED'

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label="Actions">
          <MoreHorizontal className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onSelect={() => onView(subject)}>
          View Details
        </DropdownMenuItem>

        {(canApprove || canReject || canArchive) && (
          <DropdownMenuSeparator />
        )}

        {canApprove && (
          <DropdownMenuItem onSelect={() => onApprove(subject)}>
            Approve
          </DropdownMenuItem>
        )}
        {canReject && (
          <DropdownMenuItem
            onSelect={() => onReject(subject)}
            className="text-status-error-fg focus:text-status-error-fg"
          >
            Reject…
          </DropdownMenuItem>
        )}
        {canArchive && (
          <DropdownMenuItem
            onSelect={() => onArchive(subject)}
            className="text-status-error-fg focus:text-status-error-fg"
          >
            Archive
          </DropdownMenuItem>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

const STATUS_FILTER_OPTIONS: { value: SubjectStatus | 'all'; label: string }[] = [
  { value: 'all', label: 'All statuses' },
  { value: 'SUBMITTED', label: 'Submitted' },
  { value: 'APPROVED', label: 'Approved' },
  { value: 'REJECTED', label: 'Rejected' },
  { value: 'ASSIGNED', label: 'Assigned' },
  { value: 'DRAFT', label: 'Draft' },
  { value: 'ARCHIVED', label: 'Archived' },
]

export function AdminSubjectsView() {
  useAuth()

  // ── Filters ────────────────────────────────────────────────────────────────
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [statusFilter, setStatusFilter] = useState<SubjectStatus | 'all'>('SUBMITTED')
  const [yearFilter, setYearFilter] = useState<string>('all')

  // ── Dialog state ───────────────────────────────────────────────────────────
  const [viewSubject, setViewSubject] = useState<Subject | null>(null)
  const [approveSubject, setApproveSubject] = useState<Subject | null>(null)
  const [approveLoading, setApproveLoading] = useState(false)
  const [approveError, setApproveError] = useState<string | null>(null)
  const [rejectSubject, setRejectSubject] = useState<Subject | null>(null)
  const [archiveSubject, setArchiveSubject] = useState<Subject | null>(null)
  const [archiveLoading, setArchiveLoading] = useState(false)
  const [archiveError, setArchiveError] = useState<string | null>(null)

  // ── Data ───────────────────────────────────────────────────────────────────
  const yearsApi = useApi<PaginatedResponse<AcademicYear>>(
    () => api.get('/api/admin/academic-years/?page_size=100'),
    [],
  )

  const subjectsApi = useApi<PaginatedResponse<Subject>>(
    () => {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      })
      if (statusFilter !== 'all') params.set('status', statusFilter)
      if (yearFilter !== 'all') params.set('academic_year', yearFilter)
      return api.get(`/api/admin/subjects/?${params.toString()}`)
    },
    [page, pageSize, statusFilter, yearFilter],
  )

  // ── Filter helpers ─────────────────────────────────────────────────────────
  function applyFilter<T>(setter: (v: T) => void) {
    return (v: T) => {
      setter(v)
      setPage(1)
    }
  }

  // ── Actions ────────────────────────────────────────────────────────────────
  async function handleApprove() {
    if (!approveSubject) return
    setApproveLoading(true)
    setApproveError(null)
    try {
      await api.post(`/api/admin/subjects/${approveSubject.id}/approve/`, {})
      setApproveSubject(null)
      subjectsApi.refetch()
    } catch (err) {
      setApproveError(extractMessage(err))
    } finally {
      setApproveLoading(false)
    }
  }

  async function handleArchive() {
    if (!archiveSubject) return
    setArchiveLoading(true)
    setArchiveError(null)
    try {
      await api.post(`/api/admin/subjects/${archiveSubject.id}/archive/`, {})
      setArchiveSubject(null)
      subjectsApi.refetch()
    } catch (err) {
      setArchiveError(extractMessage(err))
    } finally {
      setArchiveLoading(false)
    }
  }

  // ── Derived ────────────────────────────────────────────────────────────────
  const years = yearsApi.data?.results ?? []
  const subjects = subjectsApi.data?.results ?? []
  const total = subjectsApi.data?.count ?? 0

  // ── Columns ────────────────────────────────────────────────────────────────
  const columns = [
    {
      key: 'subject_code',
      header: 'Code',
      className: 'w-28',
      render: (s: Subject) => (
        <span className="font-mono text-xs text-muted-foreground">
          {s.subject_code ?? '—'}
        </span>
      ),
    },
    {
      key: 'title',
      header: 'Title',
      render: (s: Subject) => (
        <span className="font-medium text-foreground">{s.title}</span>
      ),
    },
    {
      key: 'subject_type',
      header: 'Type',
      className: 'w-28',
      render: (s: Subject) => <SubjectTypeBadge type={s.subject_type} />,
    },
    {
      key: 'proposed_by',
      header: 'Proposed by',
      className: 'w-44',
      render: (s: Subject) => (
        <span className="text-sm text-foreground">
          {s.proposed_by.first_name} {s.proposed_by.last_name}
        </span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      className: 'w-32',
      render: (s: Subject) => <StatusBadge status={s.status} />,
    },
    {
      key: 'submitted_at',
      header: 'Submitted',
      className: 'w-32',
      render: (s: Subject) => (
        <span className="text-xs text-muted-foreground">{formatDate(s.submitted_at)}</span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'w-12',
      render: (s: Subject) => (
        <SubjectRowActions
          subject={s}
          onView={setViewSubject}
          onApprove={sub => { setApproveError(null); setApproveSubject(sub) }}
          onReject={setRejectSubject}
          onArchive={sub => { setArchiveError(null); setArchiveSubject(sub) }}
        />
      ),
    },
  ]

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <>
      <PageHeader
        title="Subject Moderation"
        description="Review and moderate subject proposals."
      />

      {/* ── Filters ── */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Select
          value={statusFilter}
          onValueChange={applyFilter<SubjectStatus | 'all'>(setStatusFilter)}
        >
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUS_FILTER_OPTIONS.map(o => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        <Select
          value={yearFilter}
          onValueChange={applyFilter<string>(setYearFilter)}
        >
          <SelectTrigger className="w-52">
            <SelectValue placeholder="All years" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All years</SelectItem>
            {years.map(y => (
              <SelectItem key={y.id} value={String(y.id)}>
                {y.year_label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {total > 0 && !subjectsApi.isLoading && (
          <span className="ml-auto text-sm text-muted-foreground">
            {total} {total === 1 ? 'subject' : 'subjects'}
          </span>
        )}
      </div>

      {/* ── Table ── */}
      {subjectsApi.error ? (
        <InlineError message={subjectsApi.error} />
      ) : (
        <DataTable
          columns={columns}
          data={subjects}
          keyField="id"
          isLoading={subjectsApi.isLoading}
          page={page}
          pageSize={pageSize}
          total={total}
          onPageChange={setPage}
          onPageSizeChange={size => { setPageSize(size); setPage(1) }}
          emptyState={
            <EmptyState
              icon={BookOpen}
              title="No subjects found"
              description={
                statusFilter !== 'all'
                  ? `No subjects with status "${statusFilter.toLowerCase()}" match the current filters.`
                  : 'No subjects have been proposed yet.'
              }
            />
          }
        />
      )}

      {/* ── Dialogs ── */}
      <SubjectDetailDialog
        subject={viewSubject}
        open={viewSubject !== null}
        onOpenChange={open => { if (!open) setViewSubject(null) }}
      />

      <ConfirmDialog
        open={approveSubject !== null}
        onOpenChange={open => { if (!open) { setApproveSubject(null); setApproveError(null) } }}
        title="Approve Subject"
        description={`Approve "${approveSubject?.title ?? ''}"? It will become visible to students in the subject catalog.`}
        confirmLabel="Approve"
        isLoading={approveLoading}
        error={approveError}
        onConfirm={handleApprove}
      />

      <RejectDialog
        subject={rejectSubject}
        open={rejectSubject !== null}
        onOpenChange={open => { if (!open) setRejectSubject(null) }}
        onSuccess={subjectsApi.refetch}
      />

      <ConfirmDialog
        open={archiveSubject !== null}
        onOpenChange={open => { if (!open) { setArchiveSubject(null); setArchiveError(null) } }}
        title="Archive Subject"
        description={`Archive "${archiveSubject?.title ?? ''}"? This cannot be undone.`}
        confirmLabel="Archive"
        destructive
        isLoading={archiveLoading}
        error={archiveError}
        onConfirm={handleArchive}
      />
    </>
  )
}
