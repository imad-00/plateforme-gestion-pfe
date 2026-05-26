'use client'

import { useState } from 'react'
import {
  AlertCircle,
  CheckCircle2,
  ClipboardCheck,
  Info,
  Loader2,
  ListChecks,
  Shuffle,
  Trophy,
  XCircle,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type {
  BulkAssignmentResult,
  ManualAssignmentResult,
  PaginatedResponse,
  WishlistListItem,
} from '@/lib/types'
import { DataTable, type Column } from '@/components/shared/data-table'
import { StatusBadge } from '@/components/shared/status-badge'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { EmptyState } from '@/components/shared/empty-state'
import { PageHeader } from '@/components/layout/page-header'
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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

// ─── Constants ────────────────────────────────────────────────────────────────

const ROUND_LABELS: Record<string, string> = {
  FIRST: 'Round 1',
  SECOND: 'Round 2',
}

const WISHLIST_STATUS_OPTIONS = [
  { value: 'all', label: 'All statuses' },
  { value: 'SUBMITTED', label: 'Submitted' },
  { value: 'LOCKED', label: 'Locked' },
  { value: 'ARCHIVED', label: 'Archived' },
] as const

const ROUND_FILTER_OPTIONS = [
  { value: 'all', label: 'All rounds' },
  { value: 'FIRST', label: 'Round 1' },
  { value: 'SECOND', label: 'Round 2' },
] as const

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

// ─── Bulk Run Dialog (Merit / Random) ─────────────────────────────────────────

function BulkRunDialog({
  mode,
  open,
  onOpenChange,
  onSuccess,
}: {
  mode: 'merit' | 'random'
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: (result: BulkAssignmentResult) => void
}) {
  const [round, setRound] = useState<'FIRST' | 'SECOND'>('FIRST')
  const [seed, setSeed] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function handleClose() {
    if (loading) return
    onOpenChange(false)
    setSeed('')
    setError(null)
  }

  async function handleRun() {
    setLoading(true)
    setError(null)
    try {
      const body: { selection_round: string; seed?: number } = { selection_round: round }
      if (seed.trim()) body.seed = Number(seed)
      const endpoint =
        mode === 'merit'
          ? '/api/admin/assignments/merit/'
          : '/api/admin/assignments/random/'
      const result = await api.post<BulkAssignmentResult>(endpoint, body)
      onSuccess(result)
      handleClose()
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {mode === 'merit' ? (
              <Trophy className="size-4 text-primary" />
            ) : (
              <Shuffle className="size-4 text-primary" />
            )}
            {mode === 'merit' ? 'Merit Assignment' : 'Random Assignment'}
          </DialogTitle>
          <DialogDescription>
            {mode === 'merit'
              ? 'Assigns subjects to locked teams sorted by annual average, highest first.'
              : 'Assigns subjects to locked teams in randomised order, respecting wishlist rank.'}
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Selection round</Label>
            <Select
              value={round}
              onValueChange={v => setRound(v as 'FIRST' | 'SECOND')}
              disabled={loading}
            >
              <SelectTrigger>
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="FIRST">Round 1</SelectItem>
                <SelectItem value="SECOND">Round 2</SelectItem>
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-1.5">
            <Label>
              Random seed{' '}
              <span className="font-normal text-muted-foreground">(optional)</span>
            </Label>
            <Input
              type="number"
              placeholder="e.g. 42 — omit for a random seed"
              value={seed}
              onChange={e => setSeed(e.target.value)}
              disabled={loading}
            />
          </div>

          {error && <InlineError message={error} />}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleRun} disabled={loading}>
            {loading && <Loader2 className="size-4 animate-spin" />}
            Run Assignment
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Manual Assign Dialog ─────────────────────────────────────────────────────

function ManualAssignDialog({
  open,
  onOpenChange,
  onSuccess,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: (result: ManualAssignmentResult) => void
}) {
  const [teamCode, setTeamCode] = useState('')
  const [subjectId, setSubjectId] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  function handleClose() {
    if (loading) return
    onOpenChange(false)
    setTeamCode('')
    setSubjectId('')
    setError(null)
  }

  async function handleAssign() {
    if (!teamCode.trim() || !subjectId.trim()) return
    setLoading(true)
    setError(null)
    try {
      const result = await api.post<ManualAssignmentResult>(
        '/api/admin/assignments/manual/',
        { team_code: teamCode.trim(), subject_id: Number(subjectId) },
      )
      onSuccess(result)
      handleClose()
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const canSubmit = teamCode.trim().length > 0 && subjectId.trim().length > 0

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-sm">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <ClipboardCheck className="size-4 text-primary" />
            Manual Assignment
          </DialogTitle>
          <DialogDescription>
            Assign a specific approved subject to a locked team.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label>Team code</Label>
            <Input
              placeholder="e.g. TEAM-ABC123"
              value={teamCode}
              onChange={e => setTeamCode(e.target.value)}
              disabled={loading}
            />
          </div>

          <div className="space-y-1.5">
            <Label>Subject ID</Label>
            <Input
              type="number"
              placeholder="e.g. 5"
              value={subjectId}
              onChange={e => setSubjectId(e.target.value)}
              disabled={loading}
            />
          </div>

          {error && <InlineError message={error} />}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleAssign} disabled={!canSubmit || loading}>
            {loading && <Loader2 className="size-4 animate-spin" />}
            Assign
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Bulk Result Card ─────────────────────────────────────────────────────────

function BulkResultCard({ result }: { result: BulkAssignmentResult }) {
  const assignedCount = result.assigned_teams.length
  const unassignedCount = result.unassigned_teams.length
  const skippedCount = result.skipped_teams.length

  return (
    <Card className="border-status-success-border bg-status-success-bg">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-base text-status-success-fg">
          <CheckCircle2 className="size-4" />
          Assignment complete —{' '}
          {ROUND_LABELS[result.selection_round] ?? result.selection_round}
          {' · '}
          {result.mode === 'MERIT_AVERAGE' ? 'Merit' : 'Random'}
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 text-sm">
        <div className="flex gap-6">
          <span className="font-semibold text-status-success-fg">
            {assignedCount} assigned
          </span>
          {unassignedCount > 0 && (
            <span className="font-semibold text-status-warning-fg">
              {unassignedCount} unassigned
            </span>
          )}
          {skippedCount > 0 && (
            <span className="font-medium text-muted-foreground">
              {skippedCount} skipped
            </span>
          )}
        </div>

        {unassignedCount > 0 && (
          <div className="space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Unassigned Teams
            </p>
            <div className="max-h-32 overflow-y-auto rounded-md border border-status-warning-border bg-status-warning-bg p-2">
              {result.unassigned_teams.map(t => (
                <div key={t.team_code} className="flex items-baseline gap-2 py-0.5">
                  <span className="font-mono text-xs text-status-warning-fg">{t.team_code}</span>
                  <span className="text-xs text-muted-foreground">{t.reason}</span>
                </div>
              ))}
            </div>
          </div>
        )}

        {skippedCount > 0 && (
          <div className="space-y-1">
            <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              Skipped Teams
            </p>
            <div className="max-h-24 overflow-y-auto rounded-md border border-border p-2">
              {result.skipped_teams.map(t => (
                <div key={t.team_code} className="flex items-baseline gap-2 py-0.5">
                  <span className="font-mono text-xs">{t.team_code}</span>
                  <span className="text-xs text-muted-foreground">{t.reason}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Manual Result Card ───────────────────────────────────────────────────────

function ManualResultCard({ result }: { result: ManualAssignmentResult }) {
  return (
    <Card className="border-status-success-border bg-status-success-bg">
      <CardContent className="flex items-center gap-3 pt-4 text-sm">
        <CheckCircle2 className="size-4 shrink-0 text-status-success-fg" />
        <span className="text-status-success-fg">
          Manual assignment complete — team{' '}
          <span className="font-mono font-semibold">{result.team_code}</span> assigned
          subject <span className="font-semibold">#{result.subject_id}</span>.
        </span>
      </CardContent>
    </Card>
  )
}

// ─── Main View ────────────────────────────────────────────────────────────────

export function AdminAssignmentsView() {
  useAuth()

  // ── Dialog visibility ──────────────────────────────────────────────────────
  const [meritOpen, setMeritOpen] = useState(false)
  const [randomOpen, setRandomOpen] = useState(false)
  const [manualOpen, setManualOpen] = useState(false)

  // ── Last-run results ───────────────────────────────────────────────────────
  const [bulkResult, setBulkResult] = useState<BulkAssignmentResult | null>(null)
  const [manualResult, setManualResult] = useState<ManualAssignmentResult | null>(null)

  // ── Validate state ─────────────────────────────────────────────────────────
  const [validateCode, setValidateCode] = useState('')
  const [validateOpen, setValidateOpen] = useState(false)
  const [validateLoading, setValidateLoading] = useState(false)
  const [validateError, setValidateError] = useState<string | null>(null)
  const [validateSuccess, setValidateSuccess] = useState<string | null>(null)

  async function handleValidate() {
    setValidateLoading(true)
    setValidateError(null)
    setValidateSuccess(null)
    try {
      await api.post(`/api/admin/assignments/${validateCode.trim()}/validate/`, {})
      setValidateSuccess(`Assignment for team ${validateCode.trim()} has been validated.`)
      setValidateCode('')
      setValidateOpen(false)
    } catch (err) {
      setValidateError(extractMessage(err))
    } finally {
      setValidateLoading(false)
    }
  }

  // ── Wishlists table ────────────────────────────────────────────────────────
  const [wlPage, setWlPage] = useState(1)
  const [wlPageSize, setWlPageSize] = useState(10)
  const [wlRound, setWlRound] = useState('all')
  const [wlStatus, setWlStatus] = useState('SUBMITTED')

  function applyFilter(setter: (v: string) => void) {
    return (v: string) => { setter(v); setWlPage(1) }
  }

  const wishlistsApi = useApi<PaginatedResponse<WishlistListItem>>(
    () => {
      const params = new URLSearchParams({
        page: String(wlPage),
        page_size: String(wlPageSize),
      })
      if (wlRound !== 'all') params.set('selection_round', wlRound)
      if (wlStatus !== 'all') params.set('status', wlStatus)
      return api.get(`/api/admin/wishlists/?${params}`)
    },
    [wlPage, wlPageSize, wlRound, wlStatus],
  )

  const wlTotal = wishlistsApi.data?.count ?? 0

  const wlColumns: Column<WishlistListItem>[] = [
    {
      key: 'team',
      header: 'Team',
      render: w => (
        <div>
          <p className="font-mono text-xs font-semibold text-foreground">{w.team.team_code}</p>
          <p className="text-xs text-muted-foreground">{w.team.name}</p>
        </div>
      ),
    },
    {
      key: 'selection_round',
      header: 'Round',
      className: 'w-24',
      render: w => (
        <span className="text-sm">{ROUND_LABELS[w.selection_round] ?? w.selection_round}</span>
      ),
    },
    {
      key: 'item_count',
      header: 'Items',
      className: 'w-16 text-center',
      // item_count is a string from DRF — display directly, no .length needed
      render: w => <span className="tabular-nums">{w.item_count}</span>,
    },
    {
      key: 'status',
      header: 'Status',
      className: 'w-28',
      render: w => <StatusBadge status={w.status} />,
    },
    {
      key: 'submitted_at',
      header: 'Submitted',
      className: 'w-32',
      render: w => (
        <span className="text-sm text-muted-foreground">{formatDate(w.submitted_at)}</span>
      ),
    },
  ]

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <>
      <PageHeader
        title="Assignments"
        description="Run assignment algorithms, validate assignments, and review wishlists."
      />

      {/* ── Run Assignment ── */}
      <section className="mb-6 space-y-4">
        <h2 className="text-lg font-semibold tracking-tight">Run Assignment</h2>

        <div className="grid gap-3 sm:grid-cols-3">
          {/* Merit */}
          <Card className="flex flex-col gap-3 p-4">
            <div className="flex items-center gap-2">
              <Trophy className="size-4 text-primary" />
              <span className="font-semibold">Merit</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Assigns subjects ranked by team annual average (highest first).
            </p>
            <Button
              className="mt-auto w-full"
              onClick={() => { setBulkResult(null); setManualResult(null); setMeritOpen(true) }}
            >
              Run Merit
            </Button>
          </Card>

          {/* Random */}
          <Card className="flex flex-col gap-3 p-4">
            <div className="flex items-center gap-2">
              <Shuffle className="size-4 text-primary" />
              <span className="font-semibold">Random</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Assigns subjects in randomised order respecting wishlist rank.
            </p>
            <Button
              className="mt-auto w-full"
              onClick={() => { setBulkResult(null); setManualResult(null); setRandomOpen(true) }}
            >
              Run Random
            </Button>
          </Card>

          {/* Manual */}
          <Card className="flex flex-col gap-3 p-4">
            <div className="flex items-center gap-2">
              <ClipboardCheck className="size-4 text-primary" />
              <span className="font-semibold">Manual</span>
            </div>
            <p className="text-xs text-muted-foreground">
              Assign one specific approved subject to a specific locked team.
            </p>
            <Button
              variant="outline"
              className="mt-auto w-full"
              onClick={() => { setBulkResult(null); setManualResult(null); setManualOpen(true) }}
            >
              Manual Assign
            </Button>
          </Card>
        </div>

        {/* Last-run result */}
        {bulkResult && <BulkResultCard result={bulkResult} />}
        {manualResult && <ManualResultCard result={manualResult} />}
      </section>

      {/* ── Validate Assignment ── */}
      <section className="mb-6">
        <h2 className="mb-3 text-lg font-semibold tracking-tight">Validate Assignment</h2>
        <Card className="p-4">
          <div className="flex flex-wrap items-end gap-3">
            <div className="flex-1 space-y-1.5" style={{ minWidth: '12rem' }}>
              <Label htmlFor="validate-code">Team code</Label>
              <Input
                id="validate-code"
                placeholder="e.g. TEAM-ABC123"
                value={validateCode}
                onChange={e => { setValidateCode(e.target.value); setValidateSuccess(null) }}
              />
            </div>
            <Button
              disabled={!validateCode.trim() || validateLoading}
              onClick={() => { setValidateError(null); setValidateOpen(true) }}
            >
              <ListChecks className="size-4" />
              Validate
            </Button>
          </div>

          {validateSuccess && (
            <div className="mt-3 flex items-center gap-2 text-sm text-status-success-fg">
              <CheckCircle2 className="size-4 shrink-0" />
              <span>{validateSuccess}</span>
            </div>
          )}
          {validateError && <div className="mt-3"><InlineError message={validateError} /></div>}
        </Card>
      </section>

      {/* ── Wishlists ── */}
      <section>
        <h2 className="mb-3 text-lg font-semibold tracking-tight">Wishlists</h2>

        <div className="mb-3 flex flex-wrap items-center gap-3">
          <Select value={wlRound} onValueChange={applyFilter(setWlRound)}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {ROUND_FILTER_OPTIONS.map(o => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          <Select value={wlStatus} onValueChange={applyFilter(setWlStatus)}>
            <SelectTrigger className="w-36">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              {WISHLIST_STATUS_OPTIONS.map(o => (
                <SelectItem key={o.value} value={o.value}>
                  {o.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>

          {wlTotal > 0 && !wishlistsApi.isLoading && (
            <span className="ml-auto text-sm text-muted-foreground">
              {wlTotal} {wlTotal === 1 ? 'wishlist' : 'wishlists'}
            </span>
          )}
        </div>

        {wishlistsApi.error ? (
          <InlineError message={wishlistsApi.error} />
        ) : (
          <DataTable<WishlistListItem>
            columns={wlColumns}
            data={wishlistsApi.data?.results ?? []}
            keyField="wishlist_id"
            isLoading={wishlistsApi.isLoading}
            page={wlPage}
            pageSize={wlPageSize}
            total={wlTotal}
            onPageChange={setWlPage}
            onPageSizeChange={size => { setWlPageSize(size); setWlPage(1) }}
            emptyState={
              <EmptyState
                icon={Info}
                title="No wishlists found"
                description="Try adjusting the round or status filter."
              />
            }
          />
        )}
      </section>

      {/* ── Appeals note ── */}
      <section className="mt-6">
        <div className="flex items-start gap-2 rounded-lg border border-border bg-muted/30 p-4 text-sm text-muted-foreground">
          <Info className="mt-0.5 size-4 shrink-0" />
          <p>
            <span className="font-medium text-foreground">Appeals</span> — there is no admin list
            endpoint for appeals. To accept or reject an appeal, find the team on the{' '}
            <a href="/admin/teams" className="text-primary underline-offset-2 hover:underline">
              Teams page
            </a>
            {' '}and use the team detail panel, or call{' '}
            <code className="rounded bg-muted px-1 py-0.5 font-mono text-xs">
              POST /api/admin/appeals/&#123;appeal_id&#125;/accept|reject/
            </code>{' '}
            directly via API.
          </p>
        </div>
      </section>

      {/* ── Dialogs ── */}
      <BulkRunDialog
        mode="merit"
        open={meritOpen}
        onOpenChange={setMeritOpen}
        onSuccess={result => { setBulkResult(result); wishlistsApi.refetch() }}
      />

      <BulkRunDialog
        mode="random"
        open={randomOpen}
        onOpenChange={setRandomOpen}
        onSuccess={result => { setBulkResult(result); wishlistsApi.refetch() }}
      />

      <ManualAssignDialog
        open={manualOpen}
        onOpenChange={setManualOpen}
        onSuccess={result => { setManualResult(result); wishlistsApi.refetch() }}
      />

      <ConfirmDialog
        open={validateOpen}
        onOpenChange={open => { if (!open) setValidateOpen(false) }}
        title="Validate Assignment"
        description={`Finalise the assignment for team "${validateCode.trim()}"? This marks the assignment as validated and cannot be undone.`}
        confirmLabel="Validate"
        isLoading={validateLoading}
        error={validateError}
        onConfirm={handleValidate}
      />
    </>
  )
}
