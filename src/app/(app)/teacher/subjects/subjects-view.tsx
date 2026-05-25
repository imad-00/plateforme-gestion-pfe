'use client'

import { useState } from 'react'
import {
  AlertCircle,
  BookOpen,
  Clock,
  Loader2,
  Plus,
  X,
} from 'lucide-react'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type {
  CampaignStatus,
  PaginatedResponse,
  Subject,
  SubjectType,
} from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { EmptyState } from '@/components/shared/empty-state'
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
import { Textarea } from '@/components/ui/textarea'

// ─── Types ────────────────────────────────────────────────────────────────────

interface SubjectFormState {
  subject_code: string
  title: string
  description: string
  subject_type: SubjectType | ''
}

const EMPTY_FORM: SubjectFormState = {
  subject_code: '',
  title: '',
  description: '',
  subject_type: '',
}

type ConfirmState = {
  title: string
  description: string
  confirmLabel: string
  action: () => Promise<unknown>
}

// ─── Helpers ──────────────────────────────────────────────────────────────────

function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) {
    const d = err.data
    const first = Object.values(d).flat().find(v => typeof v === 'string')
    return first ?? err.message
  }
  return err instanceof Error ? err.message : 'An unexpected error occurred.'
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

function isFormValid(f: SubjectFormState): boolean {
  return !!f.title.trim() && !!f.description.trim() && !!f.subject_type
}

// ─── Type badge ───────────────────────────────────────────────────────────────

const TYPE_CONFIG: Record<SubjectType, { label: string; className: string }> = {
  RESEARCH_PROJECT: {
    label: 'Research',
    className: 'bg-primary/10 text-primary border-primary/20',
  },
  APPLIED_PROJECT: {
    label: 'Applied',
    className: 'bg-violet-50 text-violet-700 border-violet-200',
  },
  STARTUP_PROJECT: {
    label: 'Startup',
    className: 'bg-status-success-bg text-status-success-fg border-status-success-border',
  },
}

function TypeBadge({ type }: { type: SubjectType }) {
  const { label, className } = TYPE_CONFIG[type]
  return (
    <span
      className={`inline-flex h-5 items-center rounded-full border px-2.5 text-xs font-medium ${className}`}
    >
      {label}
    </span>
  )
}

// ─── Shared form fields ───────────────────────────────────────────────────────

function SubjectFormFields({
  form,
  onChange,
  disabled = false,
}: {
  form: SubjectFormState
  onChange: (f: SubjectFormState) => void
  disabled?: boolean
}) {
  return (
    <div className="space-y-4">
      <div className="grid grid-cols-2 gap-4">
        <div className="space-y-1.5">
          <Label htmlFor="sf-code">
            Code{' '}
            <span className="font-normal text-muted-foreground">(optional)</span>
          </Label>
          <Input
            id="sf-code"
            placeholder="e.g. CS-2025-01"
            value={form.subject_code}
            onChange={e => onChange({ ...form, subject_code: e.target.value })}
            disabled={disabled}
          />
        </div>
        <div className="space-y-1.5">
          <Label htmlFor="sf-type">
            Type <span className="text-status-error-fg">*</span>
          </Label>
          <Select
            value={form.subject_type}
            onValueChange={v => onChange({ ...form, subject_type: v as SubjectType })}
            disabled={disabled}
          >
            <SelectTrigger id="sf-type">
              <SelectValue placeholder="Select type…" />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="RESEARCH_PROJECT">Research Project</SelectItem>
              <SelectItem value="APPLIED_PROJECT">Applied Project</SelectItem>
              <SelectItem value="STARTUP_PROJECT">Startup Project</SelectItem>
            </SelectContent>
          </Select>
        </div>
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="sf-title">
          Title <span className="text-status-error-fg">*</span>
        </Label>
        <Input
          id="sf-title"
          placeholder="Subject title"
          value={form.title}
          onChange={e => onChange({ ...form, title: e.target.value })}
          disabled={disabled}
        />
      </div>

      <div className="space-y-1.5">
        <Label htmlFor="sf-description">
          Description <span className="text-status-error-fg">*</span>
        </Label>
        <Textarea
          id="sf-description"
          placeholder="Describe the project objectives, methodology, and expected outcomes…"
          rows={5}
          value={form.description}
          onChange={e => onChange({ ...form, description: e.target.value })}
          disabled={disabled}
          className="resize-none"
        />
      </div>
    </div>
  )
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

// ─── Phase notice ─────────────────────────────────────────────────────────────

function PhaseNotice() {
  return (
    <div className="flex items-start gap-2.5 rounded-lg border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
      <Clock className="mt-0.5 size-4 shrink-0" />
      <span>
        Subject proposals are only accepted during the{' '}
        <span className="font-medium text-foreground">Subject Management</span> phase.
        Your existing subjects are still visible below.
      </span>
    </div>
  )
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="space-y-3">
      <Skeleton className="h-[108px] w-full rounded-xl" />
      <Skeleton className="h-[108px] w-full rounded-xl" />
      <Skeleton className="h-[108px] w-full rounded-xl" />
    </div>
  )
}

// ─── Subject card ─────────────────────────────────────────────────────────────

function SubjectCard({
  subject,
  onEdit,
  onSubmit,
  onResubmit,
}: {
  subject: Subject
  onEdit: (s: Subject) => void
  onSubmit: (s: Subject) => void
  onResubmit: (s: Subject) => void
}) {
  const canEdit = subject.status === 'DRAFT' || subject.status === 'REJECTED'
  const canSubmit = subject.status === 'DRAFT'
  const canResubmit = subject.status === 'REJECTED'

  return (
    <Card>
      <CardContent className="space-y-3 pt-5">
        {/* ── Header ── */}
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 space-y-0.5">
            {subject.subject_code && (
              <p className="font-mono text-xs text-muted-foreground">{subject.subject_code}</p>
            )}
            <p className="text-sm font-semibold leading-snug text-foreground">{subject.title}</p>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <TypeBadge type={subject.subject_type} />
            <StatusBadge status={subject.status} />
          </div>
        </div>

        {/* ── Description ── */}
        <p className="line-clamp-2 text-sm text-muted-foreground">{subject.description}</p>

        {/* ── Rejection reason ── */}
        {subject.status === 'REJECTED' && subject.rejection_reason && (
          <div className="space-y-0.5 rounded-lg border border-status-error-border bg-status-error-bg p-3">
            <p className="text-xs font-medium text-status-error-fg">Rejection reason</p>
            <p className="text-sm text-status-error-fg">{subject.rejection_reason}</p>
          </div>
        )}

        {/* ── Meta ── */}
        <p className="text-xs text-muted-foreground">
          {subject.submitted_at
            ? `Submitted ${formatDate(subject.submitted_at)}`
            : `Created ${formatDate(subject.created_at)}`}
          {subject.reviewed_at && ` · Reviewed ${formatDate(subject.reviewed_at)}`}
          {subject.assigned_to_team && (
            <> · Assigned to <span className="font-mono">{subject.assigned_to_team}</span></>
          )}
        </p>

        {/* ── Actions ── */}
        {(canEdit || canSubmit || canResubmit) && (
          <div className="flex flex-wrap gap-2 pt-1">
            {canEdit && (
              <Button variant="outline" size="sm" onClick={() => onEdit(subject)}>
                Edit
              </Button>
            )}
            {canSubmit && (
              <Button size="sm" onClick={() => onSubmit(subject)}>
                Submit for Review
              </Button>
            )}
            {canResubmit && (
              <Button size="sm" onClick={() => onResubmit(subject)}>
                Resubmit
              </Button>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function TeacherSubjectsView() {
  const campaignApi = useApi<CampaignStatus>(() => api.get('/api/campaign/current/'), [])
  const subjectsApi = useApi<PaginatedResponse<Subject>>(
    () => api.get('/api/teacher/subjects/'),
    [],
  )

  // Create form
  const [createOpen, setCreateOpen] = useState(false)
  const [createForm, setCreateForm] = useState<SubjectFormState>(EMPTY_FORM)
  const [createLoading, setCreateLoading] = useState(false)
  const [createError, setCreateError] = useState<string | null>(null)

  // Edit dialog
  const [editSubject, setEditSubject] = useState<Subject | null>(null)
  const [editForm, setEditForm] = useState<SubjectFormState>(EMPTY_FORM)
  const [editLoading, setEditLoading] = useState(false)
  const [editError, setEditError] = useState<string | null>(null)

  // Confirm dialog
  const [confirm, setConfirm] = useState<ConfirmState | null>(null)
  const [confirmLoading, setConfirmLoading] = useState(false)

  // ── Derived ────────────────────────────────────────────────────────────────

  const canPropose =
    !campaignApi.isLoading &&
    (campaignApi.data?.open_phases ?? []).includes('SUBJECT_MANAGEMENT')

  const subjects = subjectsApi.data?.results ?? []

  // ── Actions ────────────────────────────────────────────────────────────────

  function openEdit(subject: Subject) {
    setEditSubject(subject)
    setEditForm({
      subject_code: subject.subject_code ?? '',
      title: subject.title,
      description: subject.description,
      subject_type: subject.subject_type,
    })
    setEditError(null)
  }

  function closeEdit() {
    if (editLoading) return
    setEditSubject(null)
    setEditError(null)
  }

  function handleSubmit(subject: Subject) {
    setConfirm({
      title: 'Submit for review?',
      description: `"${subject.title}" will be sent to the administration for review. You won't be able to edit it while it's under review.`,
      confirmLabel: 'Submit',
      action: () => api.post(`/api/teacher/subjects/${subject.id}/submit/`),
    })
  }

  function handleResubmit(subject: Subject) {
    setConfirm({
      title: 'Resubmit for review?',
      description: `"${subject.title}" will be sent to the administration for review again.`,
      confirmLabel: 'Resubmit',
      action: () => api.post(`/api/teacher/subjects/${subject.id}/resubmit/`),
    })
  }

  async function handleCreate() {
    if (!isFormValid(createForm)) return
    setCreateLoading(true)
    setCreateError(null)
    try {
      await api.post('/api/teacher/subjects/', {
        title: createForm.title.trim(),
        description: createForm.description.trim(),
        subject_type: createForm.subject_type,
        ...(createForm.subject_code.trim()
          ? { subject_code: createForm.subject_code.trim() }
          : {}),
      })
      setCreateOpen(false)
      setCreateForm(EMPTY_FORM)
      subjectsApi.refetch()
    } catch (err) {
      setCreateError(extractMessage(err))
    } finally {
      setCreateLoading(false)
    }
  }

  async function handleEdit() {
    if (!editSubject || !isFormValid(editForm)) return
    setEditLoading(true)
    setEditError(null)
    try {
      await api.patch(`/api/teacher/subjects/${editSubject.id}/`, {
        title: editForm.title.trim(),
        description: editForm.description.trim(),
        subject_type: editForm.subject_type,
        subject_code: editForm.subject_code.trim() || null,
      })
      setEditSubject(null)
      subjectsApi.refetch()
    } catch (err) {
      setEditError(extractMessage(err))
    } finally {
      setEditLoading(false)
    }
  }

  async function runConfirm() {
    if (!confirm) return
    setConfirmLoading(true)
    try {
      await confirm.action()
      setConfirm(null)
      subjectsApi.refetch()
    } catch (err) {
      // Surface errors in the confirm dialog via confirmError if needed;
      // for simplicity, close and let the list refetch show the unchanged state
      console.error(extractMessage(err))
      setConfirm(null)
    } finally {
      setConfirmLoading(false)
    }
  }

  // ── Loading ────────────────────────────────────────────────────────────────

  if (campaignApi.isLoading) {
    return (
      <>
        <PageHeader
          title="My Subjects"
          description="Propose and manage your project subjects."
        />
        <LoadingSkeleton />
      </>
    )
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <>
      <PageHeader
        title="My Subjects"
        description="Propose and manage your project subjects."
        action={
          <Button
            disabled={!canPropose || createOpen}
            onClick={() => setCreateOpen(true)}
          >
            <Plus className="size-4" />
            Propose Subject
          </Button>
        }
      />

      <div className="space-y-4">
        {/* ── Phase notice ── */}
        {!canPropose && <PhaseNotice />}

        {/* ── Create form ── */}
        {createOpen && canPropose && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center justify-between text-base">
                New Subject
                <Button
                  variant="ghost"
                  size="icon"
                  className="-mr-1 size-7"
                  onClick={() => {
                    setCreateOpen(false)
                    setCreateForm(EMPTY_FORM)
                    setCreateError(null)
                  }}
                  disabled={createLoading}
                >
                  <X className="size-4" />
                </Button>
              </CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <SubjectFormFields
                form={createForm}
                onChange={setCreateForm}
                disabled={createLoading}
              />
              {createError && <InlineError message={createError} />}
              <div className="flex gap-2">
                <Button
                  variant="outline"
                  onClick={() => {
                    setCreateOpen(false)
                    setCreateForm(EMPTY_FORM)
                    setCreateError(null)
                  }}
                  disabled={createLoading}
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleCreate}
                  disabled={createLoading || !isFormValid(createForm)}
                >
                  {createLoading && <Loader2 className="size-4 animate-spin" />}
                  Save as Draft
                </Button>
              </div>
            </CardContent>
          </Card>
        )}

        {/* ── Subjects list ── */}
        {subjectsApi.isLoading ? (
          <LoadingSkeleton />
        ) : subjectsApi.error ? (
          <InlineError message={subjectsApi.error} />
        ) : subjects.length === 0 ? (
          <EmptyState
            icon={BookOpen}
            title="No subjects yet"
            description={
              canPropose
                ? 'Click “Propose Subject” to create your first subject.'
                : "No subjects have been proposed yet."
            }
          />
        ) : (
          <div className="space-y-3">
            {subjects.map(s => (
              <SubjectCard
                key={s.id}
                subject={s}
                onEdit={openEdit}
                onSubmit={handleSubmit}
                onResubmit={handleResubmit}
              />
            ))}
          </div>
        )}
      </div>

      {/* ── Edit dialog ── */}
      <Dialog open={!!editSubject} onOpenChange={open => { if (!open) closeEdit() }}>
        <DialogContent className="max-w-lg">
          <DialogHeader>
            <DialogTitle>Edit Subject</DialogTitle>
            <DialogDescription>
              Update the subject details. Only DRAFT and REJECTED subjects can be edited.
            </DialogDescription>
          </DialogHeader>
          <SubjectFormFields
            form={editForm}
            onChange={setEditForm}
            disabled={editLoading}
          />
          {editError && <InlineError message={editError} />}
          <DialogFooter>
            <Button variant="outline" onClick={closeEdit} disabled={editLoading}>
              Cancel
            </Button>
            <Button
              onClick={handleEdit}
              disabled={editLoading || !isFormValid(editForm)}
            >
              {editLoading && <Loader2 className="size-4 animate-spin" />}
              Save Changes
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Confirm dialog ── */}
      <ConfirmDialog
        open={!!confirm}
        onOpenChange={open => { if (!open && !confirmLoading) setConfirm(null) }}
        title={confirm?.title ?? ''}
        description={confirm?.description ?? ''}
        confirmLabel={confirmLoading ? 'Processing…' : (confirm?.confirmLabel ?? 'Confirm')}
        isLoading={confirmLoading}
        onConfirm={runConfirm}
      />
    </>
  )
}
