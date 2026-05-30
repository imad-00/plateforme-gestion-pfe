'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  Calendar,
  Edit3,
  Loader2,
  Lock,
  Pencil,
  PlayCircle,
  Plus,
  XCircle,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type {
  AcademicYear,
  CampaignPhase,
  CampaignStatus,
  PaginatedResponse,
  PhaseType,
} from '@/lib/types'
import { StatusBadge } from '@/components/shared/status-badge'
import { EmptyState } from '@/components/shared/empty-state'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'

// ─── Constants ────────────────────────────────────────────────────────────────

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

const ALL_PHASE_TYPES: PhaseType[] = [
  'CAMPAIGN_SETUP',
  'SUBJECT_MANAGEMENT',
  'TEAM_FORMATION',
  'WISHLIST_1',
  'ASSIGNMENT_REVIEW_1',
  'RESULTS_AND_APPEALS',
  'WISHLIST_2',
  'ASSIGNMENT_REVIEW_2',
  'WORK_AND_SUPERVISION',
  'DEFENSE_WINDOW',
  'ARCHIVE',
]

// ─── Types & forms ────────────────────────────────────────────────────────────

interface YearForm {
  year: string
  year_label: string
  start_date: string
  end_date: string
  wishlist_size: string
}

const EMPTY_YEAR_FORM: YearForm = {
  year: '',
  year_label: '',
  start_date: '',
  end_date: '',
  wishlist_size: '5',
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

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

function toDateInput(iso: string | null | undefined): string {
  if (!iso) return ''
  return iso.slice(0, 10)
}

// Convert an ISO datetime to the local-time value expected by datetime-local input.
function toLocalInput(iso: string | null | undefined): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function fromLocalInput(local: string): string {
  return new Date(local).toISOString()
}

function yearToForm(y: AcademicYear): YearForm {
  return {
    year: y.year,
    year_label: y.year_label,
    start_date: toDateInput(y.start_date),
    end_date: toDateInput(y.end_date),
    wishlist_size: String(y.wishlist_size),
  }
}

function buildYearBody(form: YearForm, includeStatus: boolean): Record<string, unknown> {
  const body: Record<string, unknown> = {
    year: form.year.trim(),
    year_label: form.year_label.trim(),
    start_date: form.start_date || null,
    end_date: form.end_date || null,
    wishlist_size: Number(form.wishlist_size) || 5,
  }
  // On creation we always send status=ACTIVE — the only allowed value once the
  // previous year is closed. On update we don't touch status (lifecycle owns it).
  if (includeStatus) body.status = 'ACTIVE'
  return body
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

// ─── Year form fields ─────────────────────────────────────────────────────────

function YearFormFields({
  form,
  onChange,
  disabled,
}: {
  form: YearForm
  onChange: (patch: Partial<YearForm>) => void
  disabled: boolean
}) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="yr-code">Year code</Label>
          <Input
            id="yr-code"
            placeholder="2026-2027"
            value={form.year}
            onChange={e => onChange({ year: e.target.value })}
            disabled={disabled}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="yr-label">Display label</Label>
          <Input
            id="yr-label"
            placeholder="Academic Year 2026-2027"
            value={form.year_label}
            onChange={e => onChange({ year_label: e.target.value })}
            disabled={disabled}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="yr-start">Start date</Label>
          <Input
            id="yr-start"
            type="date"
            value={form.start_date}
            onChange={e => onChange({ start_date: e.target.value })}
            disabled={disabled}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="yr-end">End date</Label>
          <Input
            id="yr-end"
            type="date"
            value={form.end_date}
            onChange={e => onChange({ end_date: e.target.value })}
            disabled={disabled}
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="yr-wishlist">Wishlist size</Label>
        <Input
          id="yr-wishlist"
          type="number"
          min={1}
          max={20}
          value={form.wishlist_size}
          onChange={e => onChange({ wishlist_size: e.target.value })}
          disabled={disabled}
        />
      </div>
    </div>
  )
}

// ─── Year create/edit dialog ──────────────────────────────────────────────────

function YearDialog({
  open,
  onOpenChange,
  initial,
  onSuccess,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  initial: AcademicYear | null
  onSuccess: () => void
}) {
  const isEdit = initial !== null
  const [form, setForm] = useState<YearForm>(EMPTY_YEAR_FORM)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setForm(initial ? yearToForm(initial) : EMPTY_YEAR_FORM)
      setError(null)
    }
  }, [open, initial])

  async function handleSubmit() {
    setLoading(true)
    setError(null)
    try {
      if (isEdit && initial) {
        await api.patch(`/api/admin/academic-years/${initial.id}/`, buildYearBody(form, false))
      } else {
        // New year is created as ACTIVE — the rule "only one ACTIVE" is the
        // precondition for the button being shown at all (see AcademicYearsView).
        await api.post('/api/admin/academic-years/', buildYearBody(form, true))
      }
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
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>{isEdit ? 'Edit academic year' : 'Open new academic year'}</DialogTitle>
          <DialogDescription>
            {isEdit
              ? 'Update the year code, label, dates, or wishlist size. Status transitions go through the lifecycle workspace.'
              : 'The new year is created as ACTIVE. All 11 campaign phases are auto-scheduled — you can then open or reschedule them individually.'}
          </DialogDescription>
        </DialogHeader>

        <YearFormFields form={form} onChange={p => setForm(prev => ({ ...prev, ...p }))} disabled={loading} />

        {error && <InlineError message={error} />}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading && <Loader2 className="size-4 animate-spin" />}
            {isEdit ? 'Save' : 'Open year'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Phase row ────────────────────────────────────────────────────────────────

function PhaseRow({
  phaseType,
  record,
  isOpen,
  yearEditable,
  onEdit,
  onQuickAction,
}: {
  phaseType: PhaseType
  record: CampaignPhase | undefined
  isOpen: boolean
  yearEditable: boolean
  onEdit: (record: CampaignPhase) => void
  onQuickAction: (record: CampaignPhase, action: 'open' | 'close') => void
}) {
  if (!record) {
    return (
      <Card>
        <CardContent className="flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <p className="font-medium text-foreground">{PHASE_LABELS[phaseType]}</p>
            <p className="text-xs text-muted-foreground">Not yet provisioned.</p>
          </div>
          {isOpen ? <StatusBadge status="ACTIVE" label="Open" /> : (
            <span className="text-xs text-muted-foreground">Auto-creates on next year activation.</span>
          )}
        </CardContent>
      </Card>
    )
  }

  const now = new Date()
  const start = record.start_at ? new Date(record.start_at) : null
  const end = record.end_at ? new Date(record.end_at) : null
  const hasOpened = start !== null && start <= now
  const hasClosed = end !== null && end <= now
  const canOpenNow = yearEditable && !record.is_archived && !isOpen
  const canCloseNow = yearEditable && !record.is_archived && isOpen

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <p className="font-medium text-foreground">{PHASE_LABELS[phaseType]}</p>
            {isOpen ? (
              <StatusBadge status="ACTIVE" label="Open" />
            ) : hasClosed ? (
              <StatusBadge status="CLOSED" label="Closed" />
            ) : hasOpened ? (
              <StatusBadge status="CLOSED" label="Ended" />
            ) : (
              <StatusBadge status="PENDING" label="Scheduled" />
            )}
            {record.is_archived && <StatusBadge status="ARCHIVED" />}
          </div>
          <p className="text-xs text-muted-foreground">
            {start ? formatDateTime(record.start_at) : '—'} → {end ? formatDateTime(record.end_at) : 'open-ended'}
          </p>
        </div>

        {yearEditable && !record.is_archived && (
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {canOpenNow && (
              <Button size="sm" onClick={() => onQuickAction(record, 'open')}>
                <PlayCircle className="size-3.5" />
                Open now
              </Button>
            )}
            {canCloseNow && (
              <Button size="sm" variant="outline" onClick={() => onQuickAction(record, 'close')}>
                <XCircle className="size-3.5" />
                Close now
              </Button>
            )}
            <Button size="sm" variant="ghost" onClick={() => onEdit(record)}>
              <Edit3 className="size-3.5" />
              Schedule
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Phase schedule dialog ────────────────────────────────────────────────────

function PhaseScheduleDialog({
  open,
  onOpenChange,
  record,
  onSuccess,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  record: CampaignPhase | null
  onSuccess: () => void
}) {
  const [startAt, setStartAt] = useState('')
  const [endAt, setEndAt] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open && record) {
      setStartAt(toLocalInput(record.start_at))
      setEndAt(toLocalInput(record.end_at))
      setError(null)
    }
  }, [open, record])

  if (!record) return null

  async function handleSubmit() {
    if (!startAt) {
      setError('Start date is required.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      await api.patch(`/api/admin/campaign-phases/${record!.id}/`, {
        start_at: fromLocalInput(startAt),
        end_at: endAt ? fromLocalInput(endAt) : null,
      })
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
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Schedule phase</DialogTitle>
          <DialogDescription>
            Set when this phase opens and (optionally) when it closes. Leave end date blank
            for an open-ended phase.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3">
          <p className="text-sm text-foreground">
            {PHASE_LABELS[record.phase_type]}
          </p>
          <div className="space-y-1.5">
            <Label htmlFor="ps-start">Start at</Label>
            <Input
              id="ps-start"
              type="datetime-local"
              value={startAt}
              onChange={e => setStartAt(e.target.value)}
              disabled={loading}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="ps-end">End at <span className="font-normal text-muted-foreground">(optional)</span></Label>
            <Input
              id="ps-end"
              type="datetime-local"
              value={endAt}
              onChange={e => setEndAt(e.target.value)}
              disabled={loading}
            />
          </div>

          {error && <InlineError message={error} />}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={loading || !startAt}>
            {loading && <Loader2 className="size-4 animate-spin" />}
            Save schedule
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function AcademicYearsView() {
  const { user } = useAuth()
  const isSuperAdmin = user?.platform_access_level === 'SUPER_ADMIN'

  const yearsApi = useApi<PaginatedResponse<AcademicYear>>(
    () => api.get('/api/admin/academic-years/?page_size=100'),
    [],
  )
  const campaignApi = useApi<CampaignStatus>(() => api.get('/api/campaign/current/'), [])

  // ── Active year ────────────────────────────────────────────────────────────
  const allYears = yearsApi.data?.results ?? []
  const activeYear = allYears.find(y => y.status === 'ACTIVE') ?? null

  const phasesApi = useApi<PaginatedResponse<CampaignPhase>>(
    () =>
      activeYear
        ? api.get(`/api/admin/campaign-phases/?academic_year=${activeYear.id}&page_size=100`)
        : Promise.resolve<PaginatedResponse<CampaignPhase>>({ count: 0, next: null, previous: null, results: [] }),
    [activeYear?.id],
  )

  // ── Dialog state ───────────────────────────────────────────────────────────
  const [yearDialog, setYearDialog] = useState<{ open: boolean; initial: AcademicYear | null }>({
    open: false,
    initial: null,
  })
  const [phaseDialog, setPhaseDialog] = useState<{ open: boolean; record: CampaignPhase | null }>({
    open: false,
    record: null,
  })
  const [actionError, setActionError] = useState<string | null>(null)

  // Map phase_type → record so the fixed 11-row list can render even when the
  // backend hasn't provisioned every type (e.g. partial test data).
  const phasesByType = useMemo(() => {
    const m = new Map<PhaseType, CampaignPhase>()
    for (const p of phasesApi.data?.results ?? []) {
      m.set(p.phase_type, p)
    }
    return m
  }, [phasesApi.data])

  const openPhaseTypes = new Set(campaignApi.data?.open_phases ?? [])

  async function handlePhaseQuickAction(record: CampaignPhase, action: 'open' | 'close') {
    setActionError(null)
    try {
      const nowIso = new Date().toISOString()
      if (action === 'open') {
        // Open the phase: move start_at to now and clear any past end_at.
        const body: Record<string, string | null> = { start_at: nowIso }
        if (record.end_at && new Date(record.end_at) <= new Date()) body.end_at = null
        await api.patch(`/api/admin/campaign-phases/${record.id}/`, body)
      } else {
        await api.patch(`/api/admin/campaign-phases/${record.id}/`, { end_at: nowIso })
      }
      phasesApi.refetch()
      campaignApi.refetch()
    } catch (err) {
      setActionError(extractMessage(err))
    }
  }

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <>
      <PageHeader
        title="Academic Years"
        description="Manage the current academic year and its campaign phases. Closed and archived years live in the History workspace."
        action={
          isSuperAdmin && !activeYear ? (
            <Button onClick={() => setYearDialog({ open: true, initial: null })}>
              <Plus className="size-4" />
              Open new year
            </Button>
          ) : undefined
        }
      />

      {actionError && <div className="mb-4"><InlineError message={actionError} /></div>}

      {yearsApi.isLoading || campaignApi.isLoading ? (
        <Skeleton className="h-32 w-full rounded-xl" />
      ) : yearsApi.error ? (
        <InlineError message={yearsApi.error} />
      ) : !activeYear ? (
        <EmptyState
          icon={Calendar}
          title="No active academic year"
          description={
            isSuperAdmin
              ? 'Open a new academic year to start a campaign. All phases will be auto-scheduled and ready to open.'
              : 'A super-admin needs to open a new academic year before a campaign can start.'
          }
        />
      ) : (
        <Tabs defaultValue="year">
          <TabsList className="mb-4">
            <TabsTrigger value="year">Current year</TabsTrigger>
            <TabsTrigger value="phases">Campaign phases</TabsTrigger>
          </TabsList>

          {/* ── Tab 1: Year details ── */}
          <TabsContent value="year">
            <Card>
              <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="font-mono text-sm font-semibold text-foreground">{activeYear.year}</span>
                    <StatusBadge status={activeYear.status} />
                  </div>
                  <p className="text-sm text-foreground">{activeYear.year_label}</p>
                  <p className="text-xs text-muted-foreground">
                    {formatDate(activeYear.start_date)} → {formatDate(activeYear.end_date)}
                    {' · '}Wishlist size: {activeYear.wishlist_size}
                  </p>
                </div>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => setYearDialog({ open: true, initial: activeYear })}
                >
                  <Pencil className="size-3.5" />
                  Edit
                </Button>
              </CardContent>
            </Card>

            <div className="mt-4 flex items-start gap-2 rounded-lg border border-border bg-muted/30 p-3 text-xs text-muted-foreground">
              <Lock className="mt-0.5 size-3.5 shrink-0" />
              <span>
                Closing, reopening, or archiving this year happens in the Lifecycle workspace
                (super-admin only). Closed and archived years move to the History workspace.
              </span>
            </div>
          </TabsContent>

          {/* ── Tab 2: Campaign phases ── */}
          <TabsContent value="phases">
            {phasesApi.isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-20 w-full rounded-xl" />
                <Skeleton className="h-20 w-full rounded-xl" />
                <Skeleton className="h-20 w-full rounded-xl" />
              </div>
            ) : phasesApi.error ? (
              <InlineError message={phasesApi.error} />
            ) : (
              <div className="space-y-2">
                {ALL_PHASE_TYPES.map(pt => (
                  <PhaseRow
                    key={pt}
                    phaseType={pt}
                    record={phasesByType.get(pt)}
                    isOpen={openPhaseTypes.has(pt)}
                    yearEditable={activeYear.status === 'ACTIVE'}
                    onEdit={record => setPhaseDialog({ open: true, record })}
                    onQuickAction={handlePhaseQuickAction}
                  />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      )}

      <YearDialog
        open={yearDialog.open}
        onOpenChange={open => setYearDialog(prev => ({ ...prev, open }))}
        initial={yearDialog.initial}
        onSuccess={() => {
          yearsApi.refetch()
          campaignApi.refetch()
        }}
      />

      <PhaseScheduleDialog
        open={phaseDialog.open}
        onOpenChange={open => setPhaseDialog(prev => ({ ...prev, open }))}
        record={phaseDialog.record}
        onSuccess={() => {
          phasesApi.refetch()
          campaignApi.refetch()
        }}
      />
    </>
  )
}
