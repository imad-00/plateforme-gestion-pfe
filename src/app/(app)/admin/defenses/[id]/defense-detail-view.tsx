'use client'

import { useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import {
  AlertCircle,
  ArrowLeft,
  CalendarClock,
  CheckCircle2,
  Clock,
  Edit3,
  FileText,
  Files,
  Gavel,
  Loader2,
  Lock,
  MapPin,
  Plus,
  ShieldQuestion,
  Trash2,
  Upload,
  XCircle,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type {
  CampaignStatus,
  DefenseDetail,
  DefenseJuryAssignment,
  DefenseSupervisorDecision,
  DeliverableFile,
  PaginatedResponse,
} from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { StatusBadge } from '@/components/shared/status-badge'
import { UploadPVDialog } from '@/components/shared/upload-pv-dialog'
import { UserPicker, type PickerUser } from '@/components/shared/user-picker'
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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'

// ─── Constants ────────────────────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildFileUrl(path: string): string {
  return path.startsWith('http') ? path : `${API_BASE}${path}`
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1_048_576).toFixed(1)} MB`
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
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

// Convert an ISO datetime string to the local-time format expected by
// <input type="datetime-local"> (YYYY-MM-DDTHH:MM, no seconds, no offset).
function toLocalInput(iso: string | null): string {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

// Convert a datetime-local input value to ISO (Date treats no-offset input as local).
function fromLocalInput(local: string): string {
  return new Date(local).toISOString()
}

function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

// ─── Schedule / jury form fields ──────────────────────────────────────────────

interface JuryFormValue {
  president: PickerUser[]
  examiners: PickerUser[]
  guests: PickerUser[]
}

function JuryFields({
  value,
  onChange,
  supervisorIds,
  disabled = false,
}: {
  value: JuryFormValue
  onChange: (next: JuryFormValue) => void
  supervisorIds: number[]
  disabled?: boolean
}) {
  // Cross-field exclusion: a picked president shouldn't appear in examiners,
  // and vice versa. Supervisors are excluded everywhere (they auto-join as GUEST
  // and the backend rejects them as PRESIDENT/EXAMINER).
  const presidentIds = value.president.map(u => u.id)
  const examinerIds = value.examiners.map(u => u.id)
  const guestIds = value.guests.map(u => u.id)

  return (
    <div className="space-y-4">
      <div className="space-y-1.5">
        <Label>President</Label>
        <p className="text-xs text-muted-foreground">
          Exactly one. Supervisors of this team cannot be president.
        </p>
        <UserPicker
          value={value.president}
          onChange={next => onChange({ ...value, president: next })}
          multi={false}
          excludeIds={[...supervisorIds, ...examinerIds, ...guestIds]}
          placeholder="Search teachers…"
          disabled={disabled}
        />
      </div>

      <div className="space-y-1.5">
        <Label>Examiners</Label>
        <p className="text-xs text-muted-foreground">At least one. Supervisors cannot be examiners.</p>
        <UserPicker
          value={value.examiners}
          onChange={next => onChange({ ...value, examiners: next })}
          multi
          excludeIds={[...supervisorIds, ...presidentIds, ...guestIds]}
          placeholder="Search teachers…"
          disabled={disabled}
        />
      </div>

      <div className="space-y-1.5">
        <Label>Additional guests <span className="font-normal text-muted-foreground">(optional)</span></Label>
        <p className="text-xs text-muted-foreground">
          Team supervisors are added automatically — only list extras here.
        </p>
        <UserPicker
          value={value.guests}
          onChange={next => onChange({ ...value, guests: next })}
          multi
          excludeIds={[...supervisorIds, ...presidentIds, ...examinerIds]}
          placeholder="Search teachers…"
          disabled={disabled}
        />
      </div>
    </div>
  )
}

function emptyJuryForm(): JuryFormValue {
  return { president: [], examiners: [], guests: [] }
}

function juryFromAssignments(assignments: DefenseJuryAssignment[], supervisorIds: number[]): JuryFormValue {
  const supSet = new Set(supervisorIds)
  const form = emptyJuryForm()
  for (const a of assignments) {
    const pu: PickerUser = {
      id: a.user.id,
      first_name: a.user.first_name,
      last_name: a.user.last_name,
      matricule: a.user.matricule,
    }
    if (a.role === 'PRESIDENT') form.president = [pu]
    else if (a.role === 'EXAMINER') form.examiners.push(pu)
    else if (a.role === 'GUEST' && !supSet.has(a.user.id)) form.guests.push(pu)
  }
  return form
}

function isJuryFormValid(form: JuryFormValue): boolean {
  return form.president.length === 1 && form.examiners.length >= 1
}

// ─── Schedule dialog ──────────────────────────────────────────────────────────

function ScheduleDialog({
  open,
  onOpenChange,
  defense,
  onSuccess,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  defense: DefenseDetail
  onSuccess: (next: DefenseDetail) => void
}) {
  const supervisorIds = defense.supervisor_decisions.map(d => d.supervisor.id)
  const [datetime, setDatetime] = useState('')
  const [location, setLocation] = useState('')
  const [jury, setJury] = useState<JuryFormValue>(emptyJuryForm())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Reset whenever the dialog opens so a fresh form appears.
  useEffect(() => {
    if (open) {
      setDatetime('')
      setLocation('')
      setJury(emptyJuryForm())
      setError(null)
    }
  }, [open])

  function handleClose() {
    if (loading) return
    onOpenChange(false)
  }

  async function handleSubmit() {
    if (!datetime || !isJuryFormValid(jury)) return
    setLoading(true)
    setError(null)
    try {
      const next = await api.post<DefenseDetail>(
        `/api/admin/defenses/${defense.id}/schedule/`,
        {
          scheduled_at: fromLocalInput(datetime),
          location: location.trim(),
          president_user_id: jury.president[0].id,
          examiner_user_ids: jury.examiners.map(u => u.id),
          guest_user_ids: jury.guests.map(u => u.id),
        },
      )
      onSuccess(next)
      onOpenChange(false)
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const canSubmit = !!datetime && isJuryFormValid(jury) && !loading

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <CalendarClock className="size-4 text-primary" />
            Schedule defense
          </DialogTitle>
          <DialogDescription>
            Pick a date, location, and the jury for this defense. Active team supervisors are
            added automatically as guests.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2">
            <div className="space-y-1.5">
              <Label htmlFor="schedule-datetime">Date & time</Label>
              <Input
                id="schedule-datetime"
                type="datetime-local"
                value={datetime}
                onChange={e => setDatetime(e.target.value)}
                disabled={loading}
              />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="schedule-location">Location</Label>
              <Input
                id="schedule-location"
                placeholder="Room or address"
                value={location}
                onChange={e => setLocation(e.target.value)}
                disabled={loading}
              />
            </div>
          </div>

          <Separator />

          <JuryFields
            value={jury}
            onChange={setJury}
            supervisorIds={supervisorIds}
            disabled={loading}
          />

          {error && <InlineError message={error} />}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!canSubmit}>
            {loading && <Loader2 className="size-4 animate-spin" />}
            Schedule
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Reschedule dialog ────────────────────────────────────────────────────────

function RescheduleDialog({
  open,
  onOpenChange,
  defense,
  onSuccess,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  defense: DefenseDetail
  onSuccess: (next: DefenseDetail) => void
}) {
  const [datetime, setDatetime] = useState('')
  const [location, setLocation] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setDatetime(toLocalInput(defense.scheduled_at))
      setLocation(defense.location)
      setError(null)
    }
  }, [open, defense.scheduled_at, defense.location])

  function handleClose() {
    if (loading) return
    onOpenChange(false)
  }

  async function handleSubmit() {
    const body: Record<string, string> = {}
    if (datetime && datetime !== toLocalInput(defense.scheduled_at)) {
      body.scheduled_at = fromLocalInput(datetime)
    }
    if (location !== defense.location) body.location = location.trim()
    if (Object.keys(body).length === 0) {
      setError('Change date, location, or both to reschedule.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const next = await api.post<DefenseDetail>(
        `/api/admin/defenses/${defense.id}/reschedule/`,
        body,
      )
      onSuccess(next)
      onOpenChange(false)
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Edit3 className="size-4 text-primary" />
            Reschedule defense
          </DialogTitle>
          <DialogDescription>
            Update the date, time, or location. Jury and attached files stay unchanged.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="reschedule-datetime">Date & time</Label>
            <Input
              id="reschedule-datetime"
              type="datetime-local"
              value={datetime}
              onChange={e => setDatetime(e.target.value)}
              disabled={loading}
            />
          </div>
          <div className="space-y-1.5">
            <Label htmlFor="reschedule-location">Location</Label>
            <Input
              id="reschedule-location"
              value={location}
              onChange={e => setLocation(e.target.value)}
              disabled={loading}
            />
          </div>

          {error && <InlineError message={error} />}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading && <Loader2 className="size-4 animate-spin" />}
            Save
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Jury edit dialog ─────────────────────────────────────────────────────────

function JuryDialog({
  open,
  onOpenChange,
  defense,
  onSuccess,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  defense: DefenseDetail
  onSuccess: (next: DefenseDetail) => void
}) {
  const supervisorIds = defense.supervisor_decisions.map(d => d.supervisor.id)
  const [jury, setJury] = useState<JuryFormValue>(emptyJuryForm())
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (open) {
      setJury(juryFromAssignments(defense.jury_assignments, supervisorIds))
      setError(null)
    }
    // supervisorIds derived from defense — safe to omit
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, defense.jury_assignments])

  function handleClose() {
    if (loading) return
    onOpenChange(false)
  }

  async function handleSubmit() {
    if (!isJuryFormValid(jury)) return
    setLoading(true)
    setError(null)
    try {
      const next = await api.post<DefenseDetail>(
        `/api/admin/defenses/${defense.id}/jury/`,
        {
          // Backend's UpdateJurySerializer also requires scheduled_at and location
          // because it extends ScheduleDefenseSerializer. Keep the existing values.
          scheduled_at: defense.scheduled_at ?? new Date().toISOString(),
          location: defense.location,
          president_user_id: jury.president[0].id,
          examiner_user_ids: jury.examiners.map(u => u.id),
          guest_user_ids: jury.guests.map(u => u.id),
        },
      )
      onSuccess(next)
      onOpenChange(false)
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent className="max-w-xl">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Gavel className="size-4 text-primary" />
            Edit jury
          </DialogTitle>
          <DialogDescription>
            Adjust the president, examiners, or additional guests.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <JuryFields
            value={jury}
            onChange={setJury}
            supervisorIds={supervisorIds}
            disabled={loading}
          />

          {error && <InlineError message={error} />}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={!isJuryFormValid(jury) || loading}>
            {loading && <Loader2 className="size-4 animate-spin" />}
            Save jury
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Attach existing files sub-modal (admin-side) ─────────────────────────────
// Uses GET /api/admin/teams/<team_code>/files/ — admin-only endpoint added so
// admins can pick from a team's deliverable files without supervising the team.

function AttachExistingDialog({
  open,
  onOpenChange,
  teamCode,
  alreadyAttachedIds,
  onConfirm,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  teamCode: string
  alreadyAttachedIds: Set<string>
  onConfirm: (files: DeliverableFile[]) => void
}) {
  const filesApi = useApi<PaginatedResponse<DeliverableFile>>(
    () => api.get(`/api/admin/teams/${teamCode}/files/?page_size=100`),
    [open, teamCode],
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
          <DialogTitle>Attach team files</DialogTitle>
          <DialogDescription>
            Select deliverable files belonging to this team to attach to the defense.
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
              No additional team files available.
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

// ─── Update files dialog (admin) ──────────────────────────────────────────────

interface FileRow {
  // For already-attached or existing-team-file rows: present
  attachmentId?: string
  // The deliverable_file id (always meaningful except for pc-new where it's a synthetic uuid)
  deliverableId: string
  // For pending-from-PC uploads: the File handle
  newFile?: File
  displayName: string
  sizeBytes: number
  kind: 'attached' | 'existing-new' | 'pc-new'
}

function UpdateFilesDialog({
  open,
  onOpenChange,
  defense,
  onSuccess,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  defense: DefenseDetail
  onSuccess: (next: DefenseDetail) => void
}) {
  const [rows, setRows] = useState<FileRow[]>([])
  const [removedIds, setRemovedIds] = useState<string[]>([])
  const [showExisting, setShowExisting] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) {
      const seeded: FileRow[] = defense.attached_files
        .slice()
        .sort((a, b) => a.order - b.order)
        .map(af => ({
          attachmentId: af.id,
          deliverableId: af.deliverable_file.id,
          displayName: af.deliverable_file.original_filename,
          sizeBytes: af.deliverable_file.file_size,
          kind: 'attached',
        }))
      setRows(seeded)
      setRemovedIds([])
      setError(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }, [open, defense.attached_files])

  function handleClose() {
    if (loading) return
    onOpenChange(false)
  }

  function addNewFiles(fileList: FileList | null) {
    if (!fileList) return
    const additions: FileRow[] = Array.from(fileList).map(file => ({
      deliverableId: crypto.randomUUID(), // synthetic — replaced server-side on upload
      newFile: file,
      displayName: file.name,
      sizeBytes: file.size,
      kind: 'pc-new',
    }))
    setRows(prev => [...prev, ...additions])
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  function addExistingFiles(files: DeliverableFile[]) {
    const additions: FileRow[] = files.map(f => ({
      deliverableId: f.id,
      displayName: f.original_filename,
      sizeBytes: f.file_size,
      kind: 'existing-new',
    }))
    setRows(prev => [...prev, ...additions])
  }

  function removeRow(index: number) {
    setRows(prev => {
      const row = prev[index]
      // Track attachment ids that were initially seeded but now removed so we
      // can send them to the backend's remove_ids list.
      if (row.attachmentId) {
        setRemovedIds(ids => [...ids, row.attachmentId!])
      }
      return prev.filter((_, i) => i !== index)
    })
  }

  function move(index: number, delta: number) {
    setRows(prev => {
      const next = prev.slice()
      const j = index + delta
      if (j < 0 || j >= next.length) return prev
      ;[next[index], next[j]] = [next[j], next[index]]
      return next
    })
  }

  async function handleSubmit() {
    if (rows.length === 0) {
      setError('At least one file must remain attached.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const formData = new FormData()
      const existingNewIds = rows
        .filter(r => r.kind === 'existing-new')
        .map(r => r.deliverableId)
      if (existingNewIds.length > 0) {
        formData.append('existing_file_ids', JSON.stringify(existingNewIds))
      }
      if (removedIds.length > 0) {
        formData.append('remove_ids', JSON.stringify(removedIds))
      }
      rows.filter(r => r.kind === 'pc-new').forEach(r => formData.append('files', r.newFile!))

      const next = await api.post<DefenseDetail>(
        `/api/admin/defenses/${defense.id}/files/`,
        formData,
      )
      onSuccess(next)
      onOpenChange(false)
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setLoading(false)
    }
  }

  const attachedDeliverableIds = useMemo(
    () => new Set(rows.map(r => r.deliverableId)),
    [rows],
  )

  return (
    <>
      <Dialog open={open} onOpenChange={handleClose}>
        <DialogContent className="max-w-xl">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2">
              <Files className="size-4 text-primary" />
              Edit attached files
            </DialogTitle>
            <DialogDescription>
              Upload new files, attach team deliverables, remove items, or reorder.
              At least one file must stay attached.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-4">
            <label
              htmlFor="admin-defense-files"
              className="flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed border-border bg-muted/30 p-5 text-center transition-colors hover:bg-muted/50"
            >
              <Upload className="size-5 text-muted-foreground" />
              <div>
                <p className="text-sm font-medium text-foreground">Upload new files</p>
                <p className="text-xs text-muted-foreground">Click to choose</p>
              </div>
              <input
                id="admin-defense-files"
                ref={fileInputRef}
                type="file"
                multiple
                className="sr-only"
                onChange={e => addNewFiles(e.target.files)}
              />
            </label>

            <Button
              type="button"
              variant="outline"
              className="w-full"
              onClick={() => setShowExisting(true)}
              disabled={loading}
            >
              <Plus className="size-4" />
              Attach team files
            </Button>

            {rows.length > 0 && (
              <div className="space-y-1.5">
                <p className="text-xs font-medium text-muted-foreground">
                  Attached files <span className="font-normal">({rows.length})</span>
                </p>
                {rows.map((row, index) => (
                  <div
                    key={row.attachmentId ?? row.deliverableId}
                    className="flex items-center gap-2 rounded-lg border border-border bg-card p-2.5"
                  >
                    <span className="size-6 shrink-0 rounded-md bg-muted text-center text-xs font-medium leading-6 text-muted-foreground">
                      {index + 1}
                    </span>
                    <FileText className="size-4 shrink-0 text-muted-foreground" />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-foreground">
                        {row.displayName}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {formatSize(row.sizeBytes)} ·{' '}
                        {row.kind === 'attached'
                          ? 'Currently attached'
                          : row.kind === 'existing-new'
                            ? 'Existing deliverable'
                            : 'New upload'}
                      </p>
                    </div>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="size-7"
                      onClick={() => move(index, -1)}
                      disabled={index === 0 || loading}
                      aria-label="Move up"
                    >
                      ↑
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="size-7"
                      onClick={() => move(index, 1)}
                      disabled={index === rows.length - 1 || loading}
                      aria-label="Move down"
                    >
                      ↓
                    </Button>
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      className="size-7"
                      onClick={() => removeRow(index)}
                      disabled={loading}
                      aria-label="Remove"
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
            <Button onClick={handleSubmit} disabled={loading || rows.length === 0}>
              {loading && <Loader2 className="size-4 animate-spin" />}
              Save files
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <AttachExistingDialog
        open={showExisting}
        onOpenChange={setShowExisting}
        teamCode={defense.team.team_code}
        alreadyAttachedIds={attachedDeliverableIds}
        onConfirm={addExistingFiles}
      />
    </>
  )
}

// ─── Read-only sections ───────────────────────────────────────────────────────

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

function JuryRow({ a }: { a: DefenseJuryAssignment }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-border bg-card px-3 py-2">
      <Avatar size="sm">
        <AvatarFallback className="bg-primary/10 text-xs font-medium text-primary">
          {initials(a.user.first_name, a.user.last_name)}
        </AvatarFallback>
      </Avatar>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">
          {a.user.first_name} {a.user.last_name}
        </p>
        <p className="text-xs text-muted-foreground">{a.user.matricule}</p>
      </div>
      <StatusBadge status={a.role} />
    </div>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function DefenseDetailView({ defenseId }: { defenseId: string }) {
  useAuth()
  const campaignApi = useApi<CampaignStatus>(() => api.get('/api/campaign/current/'), [])
  const defenseApi = useApi<DefenseDetail>(
    () => api.get(`/api/admin/defenses/${defenseId}/`),
    [defenseId],
  )

  const [scheduleOpen, setScheduleOpen] = useState(false)
  const [rescheduleOpen, setRescheduleOpen] = useState(false)
  const [juryOpen, setJuryOpen] = useState(false)
  const [filesOpen, setFilesOpen] = useState(false)
  const [pvOpen, setPvOpen] = useState(false)

  const openPhases = campaignApi.data?.open_phases ?? []
  const phaseOpen = openPhases.includes('DEFENSE_WINDOW')
  const defense = defenseApi.data

  function applyUpdate() {
    // Each dialog also returns the next defense, but a refetch keeps the cached
    // payload in sync without us needing a setData hook.
    defenseApi.refetch()
  }

  if (defenseApi.isLoading || campaignApi.isLoading) {
    return (
      <>
        <PageHeader title="Defense" description="Workflow details" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </>
    )
  }

  if (defenseApi.error) {
    return (
      <>
        <PageHeader title="Defense" description="Workflow details" />
        <InlineError message={defenseApi.error} />
      </>
    )
  }

  if (!defense) return null

  const canSchedule = phaseOpen && defense.status === 'READY_TO_SCHEDULE'
  const canReschedule = phaseOpen && defense.status === 'SCHEDULED'
  const canEditJury = phaseOpen && defense.status === 'SCHEDULED'
  const canEditFiles =
    phaseOpen && (defense.status === 'READY_TO_SCHEDULE' || defense.status === 'SCHEDULED')
  const canUploadPV = phaseOpen && defense.status === 'SCHEDULED'

  return (
    <>
      <div className="mb-2">
        <Link
          href="/admin/defenses"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Defenses
        </Link>
      </div>
      <PageHeader
        title={defense.team.name}
        description={`${defense.team.team_code} · Requested ${formatDateTime(defense.requested_at)}`}
        action={<StatusBadge status={defense.status} />}
      />

      {!phaseOpen && (
        <div className="mb-4 flex items-start gap-2.5 rounded-lg border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
          <Lock className="mt-0.5 size-4 shrink-0" />
          <span>The defense workflow is not open right now. This is a read-only view.</span>
        </div>
      )}

      <div className="space-y-4">
        {/* ── Schedule overview ── */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
            <CardTitle className="text-base">Schedule</CardTitle>
            <div className="flex gap-2">
              {canSchedule && (
                <Button size="sm" onClick={() => setScheduleOpen(true)}>
                  <CalendarClock className="size-3.5" />
                  Schedule
                </Button>
              )}
              {canReschedule && (
                <Button size="sm" variant="outline" onClick={() => setRescheduleOpen(true)}>
                  <Edit3 className="size-3.5" />
                  Reschedule
                </Button>
              )}
              {canUploadPV && (
                <Button size="sm" onClick={() => setPvOpen(true)}>
                  <Upload className="size-3.5" />
                  Upload PV
                </Button>
              )}
            </div>
          </CardHeader>
          <CardContent>
            {defense.scheduled_at ? (
              <div className="grid gap-3 sm:grid-cols-2">
                <div className="flex items-center gap-2 text-sm">
                  <CalendarClock className="size-4 shrink-0 text-muted-foreground" />
                  <span className="text-foreground">{formatDateTime(defense.scheduled_at)}</span>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <MapPin className="size-4 shrink-0 text-muted-foreground" />
                  <span className="text-foreground">{defense.location || '—'}</span>
                </div>
              </div>
            ) : (
              <p className="text-sm text-muted-foreground">Not yet scheduled.</p>
            )}
          </CardContent>
        </Card>

        {/* ── PV (when complete) ── */}
        {defense.status === 'COMPLETED' && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">PV (procès-verbal)</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
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
            </CardContent>
          </Card>
        )}

        {/* ── Supervisor decisions ── */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-1.5 text-base">
              <ShieldQuestion className="size-4 text-muted-foreground" />
              Supervisor decisions
            </CardTitle>
          </CardHeader>
          <CardContent>
            {defense.supervisor_decisions.length === 0 ? (
              <p className="text-sm text-muted-foreground">No supervisor decisions recorded.</p>
            ) : (
              <div className="space-y-1.5">
                {defense.supervisor_decisions.map(d => (
                  <SupervisorDecisionRow key={d.id} d={d} />
                ))}
              </div>
            )}
          </CardContent>
        </Card>

        {/* ── Jury (when assigned) ── */}
        {(defense.status === 'SCHEDULED' || defense.status === 'COMPLETED') && (
          <Card>
            <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
              <CardTitle className="flex items-center gap-1.5 text-base">
                <Gavel className="size-4 text-muted-foreground" />
                Jury
              </CardTitle>
              {canEditJury && (
                <Button size="sm" variant="outline" onClick={() => setJuryOpen(true)}>
                  <Edit3 className="size-3.5" />
                  Edit jury
                </Button>
              )}
            </CardHeader>
            <CardContent>
              {defense.jury_assignments.length === 0 ? (
                <p className="text-sm text-muted-foreground">No jury assigned.</p>
              ) : (
                <div className="space-y-1.5">
                  {defense.jury_assignments.map(a => (
                    <JuryRow key={a.id} a={a} />
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        )}

        {/* ── Attached files ── */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
            <CardTitle className="flex items-center gap-1.5 text-base">
              <Files className="size-4 text-muted-foreground" />
              Attached files
              <span className="font-normal text-muted-foreground">
                ({defense.attached_files.length})
              </span>
            </CardTitle>
            {canEditFiles && (
              <Button size="sm" variant="outline" onClick={() => setFilesOpen(true)}>
                <Edit3 className="size-3.5" />
                Edit files
              </Button>
            )}
          </CardHeader>
          <CardContent>
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
          </CardContent>
        </Card>
      </div>

      <ScheduleDialog
        open={scheduleOpen}
        onOpenChange={setScheduleOpen}
        defense={defense}
        onSuccess={applyUpdate}
      />
      <RescheduleDialog
        open={rescheduleOpen}
        onOpenChange={setRescheduleOpen}
        defense={defense}
        onSuccess={applyUpdate}
      />
      <JuryDialog
        open={juryOpen}
        onOpenChange={setJuryOpen}
        defense={defense}
        onSuccess={applyUpdate}
      />
      <UpdateFilesDialog
        open={filesOpen}
        onOpenChange={setFilesOpen}
        defense={defense}
        onSuccess={applyUpdate}
      />
      <UploadPVDialog
        open={pvOpen}
        onOpenChange={setPvOpen}
        endpoint={`/api/admin/defenses/${defense.id}/pv/`}
        onSuccess={applyUpdate}
      />
    </>
  )
}
