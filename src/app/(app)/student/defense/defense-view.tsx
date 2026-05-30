'use client'

import { useMemo, useRef, useState } from 'react'
import {
  AlertCircle,
  CalendarClock,
  CheckCircle2,
  Clock,
  FileText,
  Loader2,
  Lock,
  MapPin,
  Plus,
  Send,
  ShieldQuestion,
  Trash2,
  Upload,
  Users,
  XCircle,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type {
  CampaignStatus,
  DefenseDetail,
  DefenseSupervisorDecision,
  DeliverableFile,
  PaginatedResponse,
  Team,
} from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { EmptyState } from '@/components/shared/empty-state'
import { StatusBadge } from '@/components/shared/status-badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
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
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { buildFileUrl } from '@/lib/config'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1_048_576).toFixed(1)} MB`
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function initials(first: string, last: string): string {
  return `${first[0] ?? ''}${last[0] ?? ''}`.toUpperCase()
}

function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) return err.message
  return err instanceof Error ? err.message : 'An unexpected error occurred.'
}

// GET /api/defenses/me/ returns `{}` (not null, not 404) when no defense exists.
// The unique field that disambiguates: an actual defense always has an `id`.
function hasDefense(payload: DefenseDetail | Record<string, never> | null | undefined): payload is DefenseDetail {
  return !!payload && typeof payload === 'object' && 'id' in payload
}

// ─── Inline error ─────────────────────────────────────────────────────────────

function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

// ─── Locked notice ────────────────────────────────────────────────────────────

function LockedNotice({ reason }: { reason: string }) {
  return (
    <div className="flex items-start gap-2.5 rounded-lg border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
      <Lock className="mt-0.5 size-4 shrink-0" />
      <span>{reason}</span>
    </div>
  )
}

// ─── Attach existing files sub-modal ──────────────────────────────────────────

function AttachExistingDialog({
  open,
  onOpenChange,
  alreadyAttachedIds,
  onConfirm,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  alreadyAttachedIds: Set<string>
  onConfirm: (files: DeliverableFile[]) => void
}) {
  const filesApi = useApi<PaginatedResponse<DeliverableFile>>(
    () => api.get('/api/deliverable-files/me/'),
    [open],
  )
  const [selected, setSelected] = useState<Set<string>>(new Set())

  function toggle(id: string) {
    setSelected(prev => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  function handleClose() {
    onOpenChange(false)
    setSelected(new Set())
  }

  function handleConfirm() {
    const all = filesApi.data?.results ?? []
    onConfirm(all.filter(f => selected.has(f.id)))
    handleClose()
  }

  const available = (filesApi.data?.results ?? []).filter(f => !alreadyAttachedIds.has(f.id))

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle>Attach existing files</DialogTitle>
          <DialogDescription>
            Select files already uploaded by your team to attach to this defense request.
          </DialogDescription>
        </DialogHeader>

        <div className="max-h-[360px] space-y-2 overflow-y-auto">
          {filesApi.isLoading ? (
            <>
              <Skeleton className="h-12 w-full rounded-lg" />
              <Skeleton className="h-12 w-full rounded-lg" />
            </>
          ) : filesApi.error ? (
            <InlineError message={filesApi.error} />
          ) : available.length === 0 ? (
            <p className="rounded-lg border border-border bg-muted/30 p-4 text-center text-sm text-muted-foreground">
              No additional deliverable files available.
            </p>
          ) : (
            available.map(file => {
              const checked = selected.has(file.id)
              return (
                <label
                  key={file.id}
                  className={[
                    'flex cursor-pointer items-start gap-3 rounded-lg border p-3 transition-colors',
                    checked
                      ? 'border-primary/40 bg-primary/5'
                      : 'border-border bg-card hover:bg-muted/40',
                  ].join(' ')}
                >
                  <input
                    type="checkbox"
                    checked={checked}
                    onChange={() => toggle(file.id)}
                    className="mt-0.5 size-4 shrink-0 accent-primary"
                  />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">
                      {file.original_filename}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatSize(file.file_size)} · {formatDateTime(file.uploaded_at)}
                    </p>
                  </div>
                </label>
              )
            })
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <Button onClick={handleConfirm} disabled={selected.size === 0}>
            Attach {selected.size > 0 ? `(${selected.size})` : ''}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Request defense dialog ───────────────────────────────────────────────────

interface AttachedItem {
  kind: 'existing' | 'new'
  // For 'existing': the deliverable_file id
  // For 'new': a synthetic uuid we generate locally to identify the row
  key: string
  // For 'existing': the deliverable id sent to the backend
  existingId?: string
  // For 'new': the File handle
  file?: File
  displayName: string
  sizeBytes: number
}

function RequestDefenseDialog({
  open,
  onOpenChange,
  onSuccess,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: (defense: DefenseDetail) => void
}) {
  const [items, setItems] = useState<AttachedItem[]>([])
  const [showExisting, setShowExisting] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  function reset() {
    setItems([])
    setError(null)
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  function handleClose() {
    if (loading) return
    onOpenChange(false)
    reset()
  }

  function handleAddNewFiles(fileList: FileList | null) {
    if (!fileList) return
    const newItems: AttachedItem[] = Array.from(fileList).map(file => ({
      kind: 'new',
      key: crypto.randomUUID(),
      file,
      displayName: file.name,
      sizeBytes: file.size,
    }))
    setItems(prev => [...prev, ...newItems])
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  function handleAttachExisting(files: DeliverableFile[]) {
    const newItems: AttachedItem[] = files.map(f => ({
      kind: 'existing',
      key: f.id,
      existingId: f.id,
      displayName: f.original_filename,
      sizeBytes: f.file_size,
    }))
    setItems(prev => [...prev, ...newItems])
  }

  function handleRemove(key: string) {
    setItems(prev => prev.filter(i => i.key !== key))
  }

  async function handleSubmit() {
    if (items.length === 0) {
      setError('Attach at least one file before requesting a defense.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const formData = new FormData()
      const existingIds = items.filter(i => i.kind === 'existing').map(i => i.existingId!)
      if (existingIds.length > 0) {
        formData.append('existing_file_ids', JSON.stringify(existingIds))
      }
      items
        .filter(i => i.kind === 'new')
        .forEach(i => formData.append('files', i.file!))

      const defense = await api.post<DefenseDetail>('/api/defenses/request/', formData)
      onSuccess(defense)
      handleClose()
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const attachedIds = useMemo(
    () => new Set(items.filter(i => i.kind === 'existing').map(i => i.existingId!)),
    [items],
  )

  return (
    <>
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Send className="size-4 text-primary" />
              Request defense
            </DialogTitle>
            <DialogDescription>
              Attach the files your jury will review. You can upload new files or pick from
              your team&apos;s existing deliverables.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            {/* Drag/drop area for new files */}
            <label
              htmlFor="defense-files"
              className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed border-border bg-muted/30 p-6 text-center transition-colors hover:bg-muted/50"
            >
              <Upload className="size-6 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium text-foreground">Upload new files</p>
                <p className="text-xs text-muted-foreground">
                  Click to choose or drop files here
                </p>
              </div>
              <input
                id="defense-files"
                ref={fileInputRef}
                type="file"
                multiple
                className="sr-only"
                onChange={e => handleAddNewFiles(e.target.files)}
              />
            </label>

            {/* Attach existing trigger */}
            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={() => setShowExisting(true)}
            >
              <Plus className="size-4" />
              Attach existing files
            </Button>

            {/* Attached items list */}
            {items.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-muted-foreground">
                  Attached files <span className="font-normal">({items.length})</span>
                </p>
                {items.map((item, index) => (
                  <div
                    key={item.key}
                    className="flex items-center gap-2 rounded-lg border border-border bg-card p-2.5"
                  >
                    <span className="size-6 shrink-0 rounded-md bg-muted text-center text-xs font-medium leading-6 text-muted-foreground">
                      {index + 1}
                    </span>
                    <FileText className="size-4 shrink-0 text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-foreground">
                        {item.displayName}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatSize(item.sizeBytes)} ·{' '}
                        {item.kind === 'existing' ? 'Existing deliverable' : 'New upload'}
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="size-7"
                      onClick={() => handleRemove(item.key)}
                      disabled={loading}
                      aria-label="Remove file"
                    >
                      <Trash2 className="size-3.5" />
                    </Button>
                  </div>
                ))}
              </div>
            )}

            {error && <InlineError message={error} />}
          </div>

          <DialogFooter>
            <Button variant="outline" onClick={handleClose} disabled={loading}>
              Cancel
            </Button>
            <Button onClick={handleSubmit} disabled={loading || items.length === 0}>
              {loading && <Loader2 className="size-4 animate-spin" />}
              Submit request
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AttachExistingDialog
        open={showExisting}
        onOpenChange={setShowExisting}
        alreadyAttachedIds={attachedIds}
        onConfirm={handleAttachExisting}
      />
    </>
  )
}

// ─── Supervisor decisions row ─────────────────────────────────────────────────

function SupervisorDecisionRow({ d }: { d: DefenseSupervisorDecision }) {
  const icon =
    d.decision === 'ACCEPTED' ? (
      <CheckCircle2 className="size-4 text-status-success-fg" />
    ) : d.decision === 'DENIED' ? (
      <XCircle className="size-4 text-status-error-fg" />
    ) : (
      <Clock className="size-4 text-muted-foreground" />
    )

  return (
    <div className="flex items-center gap-3 rounded-lg border border-border bg-card px-3 py-2">
      <Avatar size="sm">
        <AvatarFallback className="bg-primary/10 text-xs font-medium text-primary">
          {initials(d.supervisor.first_name, d.supervisor.last_name)}
        </AvatarFallback>
      </Avatar>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">
          {d.supervisor.first_name} {d.supervisor.last_name}
        </p>
        <p className="text-xs text-muted-foreground">
          {d.decision === 'PENDING'
            ? 'Awaiting decision'
            : `${d.decision === 'ACCEPTED' ? 'Accepted' : 'Denied'}${d.decided_at ? ` · ${formatDateTime(d.decided_at)}` : ''}`}
        </p>
      </div>
      {icon}
    </div>
  )
}

// ─── Defense status card ──────────────────────────────────────────────────────

function DefenseStatusCard({ defense }: { defense: DefenseDetail }) {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
        <div>
          <CardTitle className="text-base">Defense status</CardTitle>
          <p className="mt-0.5 text-xs text-muted-foreground">
            Requested {formatDateTime(defense.requested_at)} by{' '}
            {defense.requested_by.first_name} {defense.requested_by.last_name}
          </p>
        </div>
        <StatusBadge status={defense.status} />
      </CardHeader>

      <CardContent className="space-y-5">
        {/* Scheduling */}
        {defense.status === 'SCHEDULED' || defense.status === 'COMPLETED' ? (
          <div className="grid gap-3 rounded-lg border border-border bg-muted/30 p-3 sm:grid-cols-2">
            <div className="flex items-center gap-2 text-sm">
              <CalendarClock className="size-4 shrink-0 text-muted-foreground" />
              <span className="text-foreground">
                {defense.scheduled_at ? formatDateTime(defense.scheduled_at) : '—'}
              </span>
            </div>
            <div className="flex items-center gap-2 text-sm">
              <MapPin className="size-4 shrink-0 text-muted-foreground" />
              <span className="text-foreground">{defense.location || '—'}</span>
            </div>
          </div>
        ) : null}

        {/* PV summary */}
        {defense.status === 'COMPLETED' && (
          <div className="space-y-1.5 rounded-lg border border-status-success-border bg-status-success-bg p-3">
            <p className="text-xs font-semibold uppercase tracking-wide text-status-success-fg">
              Defense complete
            </p>
            {defense.final_grade && (
              <p className="text-sm text-foreground">
                Final grade: <span className="font-semibold">{defense.final_grade}</span> / 20
              </p>
            )}
            {defense.deliberation && (
              <p className="whitespace-pre-line text-sm text-foreground">
                {defense.deliberation}
              </p>
            )}
            {defense.pv_file_url && (
              <a
                href={buildFileUrl(defense.pv_file_url)}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
              >
                <FileText className="size-3.5" />
                Download PV
              </a>
            )}
          </div>
        )}

        {/* Supervisor decisions */}
        <div className="space-y-2">
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
            <ShieldQuestion className="size-3.5 text-muted-foreground" />
            Supervisor decisions
          </h3>
          {defense.supervisor_decisions.length === 0 ? (
            <p className="text-sm text-muted-foreground">No supervisor decisions recorded.</p>
          ) : (
            <div className="space-y-1.5">
              {defense.supervisor_decisions.map(d => (
                <SupervisorDecisionRow key={d.id} d={d} />
              ))}
            </div>
          )}
        </div>

        {/* Attached files */}
        <Separator />
        <div className="space-y-2">
          <h3 className="flex items-center gap-1.5 text-sm font-semibold text-foreground">
            <FileText className="size-3.5 text-muted-foreground" />
            Attached files
            <span className="font-normal text-muted-foreground">
              ({defense.attached_files.length})
            </span>
          </h3>
          <div className="space-y-1.5">
            {defense.attached_files.map(af => (
              <div
                key={af.id}
                className="flex items-center gap-2 rounded-lg border border-border bg-card p-2.5"
              >
                <span className="size-6 shrink-0 rounded-md bg-muted text-center text-xs font-medium leading-6 text-muted-foreground">
                  {af.order}
                </span>
                <FileText className="size-4 shrink-0 text-muted-foreground" />
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium text-foreground">
                    {af.deliverable_file.original_filename}
                  </p>
                  <p className="text-xs text-muted-foreground">
                    {formatSize(af.deliverable_file.file_size)}
                  </p>
                </div>
                <a
                  href={buildFileUrl(af.deliverable_file.file_url)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-xs font-medium text-primary hover:underline"
                >
                  Open
                </a>
              </div>
            ))}
          </div>
        </div>
      </CardContent>
    </Card>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function DefenseView() {
  const { user } = useAuth()

  const campaignApi = useApi<CampaignStatus>(() => api.get('/api/campaign/current/'), [])
  const teamApi = useApi<Team>(() => api.get('/api/teams/me/'), [])
  const defenseApi = useApi<DefenseDetail | Record<string, never>>(
    () => api.get('/api/defenses/me/'),
    [],
  )

  const [requestOpen, setRequestOpen] = useState(false)

  // ── Derived ────────────────────────────────────────────────────────────────

  const openPhases = campaignApi.data?.open_phases ?? []
  const team = teamApi.data
  const defense = hasDefense(defenseApi.data) ? defenseApi.data : null

  const isLeader = !!user && team?.active_leader?.user.id === user.id
  const phaseOpen = openPhases.includes('DEFENSE_WINDOW')

  // Per product rule: when the phase isn't open OR the team can't request,
  // the entire feature is hidden. No "you can't because…" enumeration.
  const accessible = phaseOpen && team?.status === 'VALIDATED' && !!team?.selected_subject_id

  // ── Loading ────────────────────────────────────────────────────────────────

  if (campaignApi.isLoading || teamApi.isLoading || defenseApi.isLoading) {
    return (
      <>
        <PageHeader title="Defense" description="Request and track your project's defense." />
        <div className="space-y-3">
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-20 w-full rounded-xl" />
        </div>
      </>
    )
  }

  if (campaignApi.error) {
    return (
      <>
        <PageHeader title="Defense" description="Request and track your project's defense." />
        <InlineError message={campaignApi.error} />
      </>
    )
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <>
      <PageHeader
        title="Defense"
        description="Request and track your project's defense."
        action={
          accessible && !defense && isLeader ? (
            <Button onClick={() => setRequestOpen(true)}>
              <Send className="size-4" />
              Request defense
            </Button>
          ) : undefined
        }
      />

      {!accessible ? (
        <LockedNotice reason="The defense workflow is not available yet." />
      ) : defense ? (
        <DefenseStatusCard defense={defense} />
      ) : (
        <EmptyState
          icon={Users}
          title="No defense yet"
          description={
            isLeader
              ? 'Submit a request with your project files when your team is ready.'
              : 'Only the team leader can submit a defense request.'
          }
        />
      )}

      <RequestDefenseDialog
        open={requestOpen}
        onOpenChange={setRequestOpen}
        onSuccess={() => defenseApi.refetch()}
      />
    </>
  )
}
