'use client'

import { useEffect, useState } from 'react'
import { AlertCircle, Calendar, CheckCircle2, Loader2, Plus } from 'lucide-react'
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
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { EmptyState } from '@/components/shared/empty-state'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
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

// ─── Types ────────────────────────────────────────────────────────────────────

interface YearForm {
  year: string
  year_label: string
  start_date: string
  end_date: string
  status: 'ACTIVE' | 'CLOSED'
  wishlist_size: string
}

interface PhaseForm {
  phase_type: PhaseType | ''
  start_at: string
  end_at: string
  display_order: string
}

const EMPTY_YEAR_FORM: YearForm = {
  year: '',
  year_label: '',
  start_date: '',
  end_date: '',
  status: 'CLOSED',
  wishlist_size: '5',
}

const EMPTY_PHASE_FORM: PhaseForm = {
  phase_type: '',
  start_at: '',
  end_at: '',
  display_order: '',
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

function toDateTimeLocal(iso: string | null | undefined): string {
  if (!iso) return ''
  return iso.slice(0, 16)
}

function yearToForm(y: AcademicYear): YearForm {
  return {
    year: y.year,
    year_label: y.year_label,
    start_date: toDateInput(y.start_date),
    end_date: toDateInput(y.end_date),
    status: y.status === 'ARCHIVED' ? 'CLOSED' : y.status,
    wishlist_size: String(y.wishlist_size),
  }
}

function phaseToForm(p: CampaignPhase): PhaseForm {
  return {
    phase_type: p.phase_type,
    start_at: toDateTimeLocal(p.start_at),
    end_at: toDateTimeLocal(p.end_at),
    display_order: String(p.display_order),
  }
}

function buildYearBody(form: YearForm): Record<string, unknown> {
  return {
    year: form.year.trim(),
    year_label: form.year_label.trim(),
    start_date: form.start_date || null,
    end_date: form.end_date || null,
    status: form.status,
    wishlist_size: Number(form.wishlist_size) || 5,
  }
}

function buildPhaseBody(form: PhaseForm, yearId: number): Record<string, unknown> {
  return {
    academic_year: yearId,
    phase_type: form.phase_type,
    start_at: form.start_at,
    end_at: form.end_at || null,
    display_order: form.display_order ? Number(form.display_order) : 0,
  }
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

function CardSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-20 w-full rounded-xl" />
      <Skeleton className="h-20 w-full rounded-xl" />
      <Skeleton className="h-20 w-full rounded-xl" />
    </div>
  )
}

// ─── Year form fields ─────────────────────────────────────────────────────────

function YearFormFields({
  form,
  onChange,
}: {
  form: YearForm
  onChange: (patch: Partial<YearForm>) => void
}) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="yr-code">Year Code</Label>
          <Input
            id="yr-code"
            placeholder="2024-2025"
            value={form.year}
            onChange={e => onChange({ year: e.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="yr-label">Display Label</Label>
          <Input
            id="yr-label"
            placeholder="Academic Year 2024-2025"
            value={form.year_label}
            onChange={e => onChange({ year_label: e.target.value })}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="yr-start">Start Date</Label>
          <Input
            id="yr-start"
            type="date"
            value={form.start_date}
            onChange={e => onChange({ start_date: e.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="yr-end">End Date</Label>
          <Input
            id="yr-end"
            type="date"
            value={form.end_date}
            onChange={e => onChange({ end_date: e.target.value })}
          />
        </div>
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label>Status</Label>
          <Select
            value={form.status}
            onValueChange={v => onChange({ status: v as 'ACTIVE' | 'CLOSED' })}
          >
            <SelectTrigger className="w-full">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="ACTIVE">Active</SelectItem>
              <SelectItem value="CLOSED">Closed</SelectItem>
            </SelectContent>
          </Select>
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="yr-wishlist">Wishlist Size</Label>
          <Input
            id="yr-wishlist"
            type="number"
            min={1}
            max={20}
            value={form.wishlist_size}
            onChange={e => onChange({ wishlist_size: e.target.value })}
          />
        </div>
      </div>
    </div>
  )
}

// ─── Phase form fields ────────────────────────────────────────────────────────

function PhaseFormFields({
  form,
  onChange,
  isEdit = false,
}: {
  form: PhaseForm
  onChange: (patch: Partial<PhaseForm>) => void
  isEdit?: boolean
}) {
  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label>Phase Type</Label>
        {isEdit ? (
          <Input
            value={form.phase_type ? PHASE_LABELS[form.phase_type] : ''}
            disabled
          />
        ) : (
          <Select
            value={form.phase_type}
            onValueChange={v => onChange({ phase_type: v as PhaseType })}
          >
            <SelectTrigger className="w-full">
              <SelectValue placeholder="Select phase type…" />
            </SelectTrigger>
            <SelectContent>
              {ALL_PHASE_TYPES.map(pt => (
                <SelectItem key={pt} value={pt}>
                  {PHASE_LABELS[pt]}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        )}
      </div>

      <div className="grid grid-cols-2 gap-3">
        <div className="space-y-1.5">
          <Label htmlFor="ph-start">Start</Label>
          <Input
            id="ph-start"
            type="datetime-local"
            value={form.start_at}
            onChange={e => onChange({ start_at: e.target.value })}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="ph-end">
            End{' '}
            <span className="font-normal text-muted-foreground">(optional)</span>
          </Label>
          <Input
            id="ph-end"
            type="datetime-local"
            value={form.end_at}
            onChange={e => onChange({ end_at: e.target.value })}
          />
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="ph-order">Display Order</Label>
        <Input
          id="ph-order"
          type="number"
          min={0}
          placeholder="0"
          value={form.display_order}
          onChange={e => onChange({ display_order: e.target.value })}
        />
      </div>
    </div>
  )
}

// ─── Year dialog ──────────────────────────────────────────────────────────────

function YearDialog({
  mode,
  year,
  open,
  onOpenChange,
  onSuccess,
}: {
  mode: 'create' | 'edit'
  year?: AcademicYear
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}) {
  const [form, setForm] = useState<YearForm>(EMPTY_YEAR_FORM)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setError(null)
    setLoading(false)
    setForm(mode === 'edit' && year ? yearToForm(year) : EMPTY_YEAR_FORM)
  }, [open, mode, year])

  async function handleSubmit() {
    setLoading(true)
    setError(null)
    try {
      if (mode === 'edit' && year) {
        await api.patch(`/api/admin/academic-years/${year.id}/`, buildYearBody(form))
      } else {
        await api.post('/api/admin/academic-years/', buildYearBody(form))
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
    <Dialog open={open} onOpenChange={loading ? undefined : onOpenChange}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>
            {mode === 'edit' ? 'Edit Academic Year' : 'New Academic Year'}
          </DialogTitle>
        </DialogHeader>

        <YearFormFields
          form={form}
          onChange={patch => setForm(prev => ({ ...prev, ...patch }))}
        />

        {error && <InlineError message={error} />}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading && <Loader2 className="size-4 animate-spin" />}
            {mode === 'edit' ? 'Save Changes' : 'Create'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Phase dialog ─────────────────────────────────────────────────────────────

function PhaseDialog({
  mode,
  phase,
  yearId,
  open,
  onOpenChange,
  onSuccess,
}: {
  mode: 'create' | 'edit'
  phase?: CampaignPhase
  yearId: number
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}) {
  const [form, setForm] = useState<PhaseForm>(EMPTY_PHASE_FORM)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!open) return
    setError(null)
    setLoading(false)
    setForm(mode === 'edit' && phase ? phaseToForm(phase) : EMPTY_PHASE_FORM)
  }, [open, mode, phase])

  async function handleSubmit() {
    setLoading(true)
    setError(null)
    try {
      if (mode === 'edit' && phase) {
        await api.patch(`/api/admin/campaign-phases/${phase.id}/`, buildPhaseBody(form, yearId))
      } else {
        await api.post('/api/admin/campaign-phases/', buildPhaseBody(form, yearId))
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
    <Dialog open={open} onOpenChange={loading ? undefined : onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>{mode === 'edit' ? 'Edit Phase' : 'Add Phase'}</DialogTitle>
        </DialogHeader>

        <PhaseFormFields
          form={form}
          onChange={patch => setForm(prev => ({ ...prev, ...patch }))}
          isEdit={mode === 'edit'}
        />

        {error && <InlineError message={error} />}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading && <Loader2 className="size-4 animate-spin" />}
            {mode === 'edit' ? 'Save Changes' : 'Add Phase'}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Year card ────────────────────────────────────────────────────────────────

function YearCard({
  year,
  onEdit,
  onActivate,
  onArchive,
}: {
  year: AcademicYear
  onEdit: (y: AcademicYear) => void
  onActivate: (y: AcademicYear) => void
  onArchive: (y: AcademicYear) => void
}) {
  const isArchived = year.status === 'ARCHIVED'

  return (
    <Card>
      <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="font-mono text-sm font-semibold text-foreground">{year.year}</span>
            <StatusBadge status={year.status} />
          </div>
          <p className="text-sm text-foreground">{year.year_label}</p>
          <p className="text-xs text-muted-foreground">
            {formatDate(year.start_date)} → {formatDate(year.end_date)}
            {' · '}Wishlist size: {year.wishlist_size}
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {!isArchived && (
            <Button variant="ghost" size="sm" onClick={() => onEdit(year)}>
              Edit
            </Button>
          )}
          {year.status === 'CLOSED' && (
            <Button variant="outline" size="sm" onClick={() => onActivate(year)}>
              Set Active
            </Button>
          )}
          {!isArchived && (
            <Button
              variant="ghost"
              size="sm"
              className="text-status-error-fg hover:text-status-error-fg"
              onClick={() => onArchive(year)}
            >
              Archive
            </Button>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

// ─── Phase card ───────────────────────────────────────────────────────────────

function PhaseCard({
  phase,
  openPhases,
  onEdit,
  onArchive,
}: {
  phase: CampaignPhase
  openPhases: PhaseType[]
  onEdit: (p: CampaignPhase) => void
  onArchive: (p: CampaignPhase) => void
}) {
  const isOpen = openPhases.includes(phase.phase_type)
  const isArchived = phase.is_archived

  return (
    <Card className={isArchived ? 'opacity-60' : undefined}>
      <CardContent className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div className="min-w-0 space-y-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-medium text-foreground">
              {PHASE_LABELS[phase.phase_type]}
            </span>
            {isOpen && (
              <span className="inline-flex items-center gap-1 rounded-full border border-status-success-border bg-status-success-bg px-2 py-0.5 text-xs font-medium text-status-success-fg">
                <CheckCircle2 className="size-3" />
                Open
              </span>
            )}
            {isArchived && <StatusBadge status="ARCHIVED" />}
          </div>
          <p className="flex flex-wrap gap-x-3 text-xs text-muted-foreground">
            <span className="flex items-center gap-1">
              <Calendar className="size-3" />
              {formatDateTime(phase.start_at)}
            </span>
            {phase.end_at && (
              <span>→ {formatDateTime(phase.end_at)}</span>
            )}
          </p>
        </div>

        {!isArchived && (
          <div className="flex shrink-0 items-center gap-2">
            <Button variant="ghost" size="sm" onClick={() => onEdit(phase)}>
              Edit
            </Button>
            <Button
              variant="ghost"
              size="sm"
              className="text-status-error-fg hover:text-status-error-fg"
              onClick={() => onArchive(phase)}
            >
              Archive
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function AcademicYearsView() {
  useAuth()

  // ── Years state ────────────────────────────────────────────────────────────
  const [includeArchived, setIncludeArchived] = useState(false)
  const [createYearOpen, setCreateYearOpen] = useState(false)
  const [editYear, setEditYear] = useState<AcademicYear | null>(null)
  const [archiveYear, setArchiveYear] = useState<AcademicYear | null>(null)
  const [archiveYearLoading, setArchiveYearLoading] = useState(false)
  const [archiveYearError, setArchiveYearError] = useState<string | null>(null)
  const [activateYear, setActivateYear] = useState<AcademicYear | null>(null)
  const [activateLoading, setActivateLoading] = useState(false)
  const [activateError, setActivateError] = useState<string | null>(null)

  // ── Phases state ───────────────────────────────────────────────────────────
  const [selectedYearId, setSelectedYearId] = useState<string>('')
  const [createPhaseOpen, setCreatePhaseOpen] = useState(false)
  const [editPhase, setEditPhase] = useState<CampaignPhase | null>(null)
  const [archivePhase, setArchivePhase] = useState<CampaignPhase | null>(null)
  const [archivePhaseLoading, setArchivePhaseLoading] = useState(false)
  const [archivePhaseError, setArchivePhaseError] = useState<string | null>(null)

  // ── Data ───────────────────────────────────────────────────────────────────
  // Fetch all years (including archived) once; filter client-side for Tab 1
  const yearsApi = useApi<PaginatedResponse<AcademicYear>>(
    () => api.get('/api/admin/academic-years/?page_size=100&include_archived=true'),
    [],
  )

  const phasesApi = useApi<PaginatedResponse<CampaignPhase>>(
    () =>
      selectedYearId
        ? api.get(`/api/admin/campaign-phases/?academic_year=${selectedYearId}&page_size=100`)
        : Promise.resolve<PaginatedResponse<CampaignPhase>>({
            count: 0, next: null, previous: null, results: [],
          }),
    [selectedYearId],
  )

  const campaignApi = useApi<CampaignStatus>(() => api.get('/api/campaign/current/'), [])

  // Auto-select the active year when data first loads
  useEffect(() => {
    if (selectedYearId || !yearsApi.data) return
    const all = yearsApi.data.results
    const active = all.find(y => y.status === 'ACTIVE')
    const first = all.find(y => y.status !== 'ARCHIVED')
    const pick = active ?? first
    if (pick) setSelectedYearId(String(pick.id))
  }, [yearsApi.data, selectedYearId])

  // ── Actions ────────────────────────────────────────────────────────────────
  async function handleArchiveYear() {
    if (!archiveYear) return
    setArchiveYearLoading(true)
    setArchiveYearError(null)
    try {
      await api.post(`/api/admin/academic-years/${archiveYear.id}/archive/`, {})
      setArchiveYear(null)
      yearsApi.refetch()
    } catch (err) {
      setArchiveYearError(extractMessage(err))
    } finally {
      setArchiveYearLoading(false)
    }
  }

  async function handleActivateYear() {
    if (!activateYear) return
    setActivateLoading(true)
    setActivateError(null)
    try {
      await api.patch(`/api/admin/academic-years/${activateYear.id}/`, { status: 'ACTIVE' })
      setActivateYear(null)
      yearsApi.refetch()
    } catch (err) {
      setActivateError(extractMessage(err))
    } finally {
      setActivateLoading(false)
    }
  }

  async function handleArchivePhase() {
    if (!archivePhase) return
    setArchivePhaseLoading(true)
    setArchivePhaseError(null)
    try {
      await api.post(`/api/admin/campaign-phases/${archivePhase.id}/archive/`, {})
      setArchivePhase(null)
      phasesApi.refetch()
    } catch (err) {
      setArchivePhaseError(extractMessage(err))
    } finally {
      setArchivePhaseLoading(false)
    }
  }

  // ── Derived ────────────────────────────────────────────────────────────────
  const allYears = yearsApi.data?.results ?? []
  const visibleYears = includeArchived ? allYears : allYears.filter(y => y.status !== 'ARCHIVED')
  const selectableYears = allYears.filter(y => y.status !== 'ARCHIVED')
  const phases = phasesApi.data?.results ?? []
  const openPhases = campaignApi.data?.open_phases ?? []
  const selectedYearNum = Number(selectedYearId) || 0

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <>
      <PageHeader
        title="Academic Years"
        description="Manage academic years and campaign phases."
      />

      <Tabs defaultValue="years">
        <TabsList className="mb-6">
          <TabsTrigger value="years">Academic Years</TabsTrigger>
          <TabsTrigger value="phases">Campaign Phases</TabsTrigger>
        </TabsList>

        {/* ── Tab 1: Academic Years ── */}
        <TabsContent value="years">
          <div className="mb-4 flex items-center justify-between gap-3">
            <label className="flex cursor-pointer items-center gap-2 text-sm text-muted-foreground select-none">
              <input
                type="checkbox"
                checked={includeArchived}
                onChange={e => setIncludeArchived(e.target.checked)}
                className="size-4 rounded border-border accent-primary"
              />
              Show archived
            </label>
            <Button size="sm" onClick={() => setCreateYearOpen(true)}>
              <Plus className="size-4" />
              New Year
            </Button>
          </div>

          {yearsApi.isLoading ? (
            <CardSkeleton />
          ) : yearsApi.error ? (
            <InlineError message={yearsApi.error} />
          ) : visibleYears.length === 0 ? (
            <EmptyState
              icon={Calendar}
              title="No academic years"
              description="Create your first academic year to get started."
            />
          ) : (
            <div className="space-y-3">
              {visibleYears.map(y => (
                <YearCard
                  key={y.id}
                  year={y}
                  onEdit={setEditYear}
                  onActivate={yr => { setActivateError(null); setActivateYear(yr) }}
                  onArchive={yr => { setArchiveYearError(null); setArchiveYear(yr) }}
                />
              ))}
            </div>
          )}
        </TabsContent>

        {/* ── Tab 2: Campaign Phases ── */}
        <TabsContent value="phases">
          <div className="mb-4 flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <span className="text-sm font-medium text-muted-foreground shrink-0">Year</span>
              {yearsApi.isLoading ? (
                <Skeleton className="h-8 w-52" />
              ) : (
                <Select value={selectedYearId} onValueChange={setSelectedYearId}>
                  <SelectTrigger className="w-56">
                    <SelectValue placeholder="Select a year…" />
                  </SelectTrigger>
                  <SelectContent>
                    {selectableYears.map(y => (
                      <SelectItem key={y.id} value={String(y.id)}>
                        {y.year_label}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              )}
            </div>
            {selectedYearId && (
              <Button size="sm" onClick={() => setCreatePhaseOpen(true)}>
                <Plus className="size-4" />
                Add Phase
              </Button>
            )}
          </div>

          {!selectedYearId ? (
            <EmptyState
              icon={Calendar}
              title="Select a year"
              description="Choose an academic year above to view and manage its campaign phases."
            />
          ) : phasesApi.isLoading ? (
            <CardSkeleton />
          ) : phasesApi.error ? (
            <InlineError message={phasesApi.error} />
          ) : phases.length === 0 ? (
            <EmptyState
              icon={Calendar}
              title="No phases yet"
              description="Add phases to define the timeline of this academic year."
            />
          ) : (
            <div className="space-y-3">
              {phases.map(p => (
                <PhaseCard
                  key={p.id}
                  phase={p}
                  openPhases={openPhases}
                  onEdit={setEditPhase}
                  onArchive={ph => { setArchivePhaseError(null); setArchivePhase(ph) }}
                />
              ))}
            </div>
          )}
        </TabsContent>
      </Tabs>

      {/* ── Year dialogs ── */}
      <YearDialog
        mode="create"
        open={createYearOpen}
        onOpenChange={setCreateYearOpen}
        onSuccess={yearsApi.refetch}
      />
      <YearDialog
        mode="edit"
        year={editYear ?? undefined}
        open={editYear !== null}
        onOpenChange={open => { if (!open) setEditYear(null) }}
        onSuccess={yearsApi.refetch}
      />
      <ConfirmDialog
        open={activateYear !== null}
        onOpenChange={open => { if (!open) { setActivateYear(null); setActivateError(null) } }}
        title="Set Active Year"
        description={`Make "${activateYear?.year_label ?? ''}" the active academic year? Any currently active year will be closed.`}
        confirmLabel="Set Active"
        isLoading={activateLoading}
        error={activateError}
        onConfirm={handleActivateYear}
      />
      <ConfirmDialog
        open={archiveYear !== null}
        onOpenChange={open => { if (!open) { setArchiveYear(null); setArchiveYearError(null) } }}
        title="Archive Academic Year"
        description={`Archive "${archiveYear?.year_label ?? ''}"? Archived years cannot be edited or reactivated.`}
        confirmLabel="Archive"
        destructive
        isLoading={archiveYearLoading}
        error={archiveYearError}
        onConfirm={handleArchiveYear}
      />

      {/* ── Phase dialogs ── */}
      <PhaseDialog
        mode="create"
        yearId={selectedYearNum}
        open={createPhaseOpen}
        onOpenChange={setCreatePhaseOpen}
        onSuccess={phasesApi.refetch}
      />
      <PhaseDialog
        mode="edit"
        phase={editPhase ?? undefined}
        yearId={selectedYearNum}
        open={editPhase !== null}
        onOpenChange={open => { if (!open) setEditPhase(null) }}
        onSuccess={phasesApi.refetch}
      />
      <ConfirmDialog
        open={archivePhase !== null}
        onOpenChange={open => { if (!open) { setArchivePhase(null); setArchivePhaseError(null) } }}
        title="Archive Phase"
        description={`Archive the "${archivePhase ? PHASE_LABELS[archivePhase.phase_type] : ''}" phase? It will no longer be visible to users.`}
        confirmLabel="Archive"
        destructive
        isLoading={archivePhaseLoading}
        error={archivePhaseError}
        onConfirm={handleArchivePhase}
      />
    </>
  )
}
