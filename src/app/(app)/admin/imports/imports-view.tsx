'use client'

import { useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import {
  AlertCircle,
  AlertTriangle,
  ArrowLeft,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Download,
  FileUp,
  Loader2,
  Upload,
  XCircle,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import type {
  ImportConfirmResponse,
  ImportRowError,
  ImportType,
  UserImportBatch,
} from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Label } from '@/components/ui/label'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1_048_576).toFixed(1)} MB`
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

// Group row-error entries by row so a single row with three field errors
// renders as one collapsible block instead of three.
function groupByRow(items: ImportRowError[]): Map<number | 'file', ImportRowError[]> {
  const map = new Map<number | 'file', ImportRowError[]>()
  for (const item of items) {
    const key = item.row === null ? 'file' : item.row
    if (!map.has(key)) map.set(key, [])
    map.get(key)!.push(item)
  }
  return map
}

// ─── Issue group (errors or warnings, grouped by row) ─────────────────────────

function IssueGroup({
  title,
  items,
  tone,
}: {
  title: string
  items: ImportRowError[]
  tone: 'error' | 'warning'
}) {
  const [open, setOpen] = useState(true)
  if (items.length === 0) return null

  const grouped = groupByRow(items)
  const Icon = tone === 'error' ? XCircle : AlertTriangle
  const wrapperClass =
    tone === 'error'
      ? 'border-status-error-border bg-status-error-bg/30'
      : 'border-status-warning-border bg-status-warning-bg/30'
  const iconClass = tone === 'error' ? 'text-status-error-fg' : 'text-status-warning-fg'

  return (
    <div className={`space-y-2 rounded-lg border p-3 ${wrapperClass}`}>
      <button
        type="button"
        onClick={() => setOpen(v => !v)}
        className="flex w-full items-center justify-between text-sm font-medium text-foreground"
      >
        <span className="flex items-center gap-2">
          <Icon className={`size-4 ${iconClass}`} />
          {title}
          <span className="font-normal text-muted-foreground">({items.length})</span>
        </span>
        {open ? <ChevronDown className="size-3.5" /> : <ChevronRight className="size-3.5" />}
      </button>
      {open && (
        <div className="space-y-1.5">
          {Array.from(grouped.entries())
            .sort((a, b) => {
              if (a[0] === 'file') return -1
              if (b[0] === 'file') return 1
              return (a[0] as number) - (b[0] as number)
            })
            .map(([key, errors]) => (
              <div
                key={String(key)}
                className="rounded-md border border-border bg-card/60 p-2.5 text-xs"
              >
                <p className="mb-1 font-semibold text-foreground">
                  {key === 'file' ? 'File-level' : `Row ${key}`}
                </p>
                <ul className="space-y-1">
                  {errors.map((err, i) => (
                    <li key={i} className="text-foreground">
                      {err.field && (
                        <span className="font-mono text-muted-foreground">{err.field}: </span>
                      )}
                      <span className="font-medium">{err.code}</span> — {err.message}
                    </li>
                  ))}
                </ul>
              </div>
            ))}
        </div>
      )}
    </div>
  )
}

// ─── Phase 1: upload ──────────────────────────────────────────────────────────

function UploadPhase({
  onPreview,
}: {
  onPreview: (batch: UserImportBatch) => void
}) {
  const [importType, setImportType] = useState<ImportType>('STUDENTS')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  async function handleSubmit() {
    if (!file) {
      setError('Pick a CSV or XLSX file to import.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('import_type', importType)
      const batch = await api.post<UserImportBatch>(
        '/api/admin/imports/users/preview/',
        formData,
      )
      onPreview(batch)
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setLoading(false)
    }
  }

  async function handleTemplateDownload() {
    try {
      await api.download(
        `/api/admin/imports/users/template/?import_type=${importType}`,
        `${importType.toLowerCase()}_template.csv`,
      )
    } catch (err) {
      setError(extractMessage(err))
    }
  }

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-base">Upload</CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Import type */}
        <div className="space-y-1.5">
          <Label>Import type</Label>
          <div className="flex flex-wrap gap-2">
            {(['STUDENTS', 'TEACHERS'] as ImportType[]).map(t => (
              <button
                key={t}
                type="button"
                onClick={() => setImportType(t)}
                className={[
                  'rounded-lg border px-3 py-2 text-sm transition-colors',
                  importType === t
                    ? 'border-primary/40 bg-primary/5 text-primary'
                    : 'border-border bg-card text-foreground hover:bg-muted/40',
                ].join(' ')}
              >
                {t === 'STUDENTS' ? 'Students' : 'Teachers'}
              </button>
            ))}
          </div>
        </div>

        {/* Template download */}
        <Button type="button" variant="outline" size="sm" onClick={handleTemplateDownload}>
          <Download className="size-3.5" />
          Download {importType.toLowerCase()} template
        </Button>

        {importType === 'STUDENTS' && (
          <p className="text-xs text-muted-foreground">
            Students are always imported into the current active academic year. The template
            no longer includes an academic year column.
          </p>
        )}

        {/* File picker */}
        <div className="space-y-1.5">
          <Label>File</Label>
          <label
            htmlFor="import-file"
            className={[
              'flex cursor-pointer flex-col items-center gap-2 rounded-lg border-2 border-dashed p-6 text-center transition-colors',
              file
                ? 'border-primary/40 bg-primary/5'
                : 'border-border bg-muted/30 hover:bg-muted/50',
            ].join(' ')}
          >
            <Upload className={file ? 'size-6 text-primary' : 'size-6 text-muted-foreground'} />
            {file ? (
              <div>
                <p className="text-sm font-medium text-primary">{file.name}</p>
                <p className="text-xs text-muted-foreground">{formatSize(file.size)}</p>
              </div>
            ) : (
              <div>
                <p className="text-sm font-medium text-foreground">
                  Click to attach CSV or XLSX
                </p>
                <p className="text-xs text-muted-foreground">
                  Max 5 MB · up to 1000 rows
                </p>
              </div>
            )}
            <input
              id="import-file"
              ref={fileInputRef}
              type="file"
              accept=".csv,.xlsx"
              className="sr-only"
              onChange={e => setFile(e.target.files?.[0] ?? null)}
            />
          </label>
        </div>

        {error && <InlineError message={error} />}

        <Button onClick={handleSubmit} disabled={loading || !file}>
          {loading ? <Loader2 className="size-4 animate-spin" /> : <FileUp className="size-4" />}
          Preview import
        </Button>
      </CardContent>
    </Card>
  )
}

// ─── Phase 2: preview ─────────────────────────────────────────────────────────

function PreviewPhase({
  batch,
  onConfirmed,
  onBack,
}: {
  batch: UserImportBatch
  onConfirmed: (result: ImportConfirmResponse) => void
  onBack: () => void
}) {
  const [allowPartial, setAllowPartial] = useState(false)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const hasErrors = batch.errors.length > 0
  const hasValidRows = batch.valid_rows > 0
  const canConfirmStrict = !hasErrors && hasValidRows
  // Partial only makes sense when some rows are valid and at least one is invalid.
  const canConfirmPartial = hasErrors && hasValidRows

  async function handleConfirm() {
    setLoading(true)
    setError(null)
    try {
      const result = await api.post<ImportConfirmResponse>(
        '/api/admin/imports/users/confirm/',
        { batch_id: batch.id, confirm: true, allow_partial: allowPartial },
      )
      onConfirmed(result)
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <Button variant="ghost" size="sm" onClick={onBack}>
          <ArrowLeft className="size-3.5" />
          Back to upload
        </Button>
        <p className="text-xs text-muted-foreground">
          Batch #{batch.id} · {batch.original_filename}
        </p>
      </div>

      {/* Counters */}
      <div className="grid gap-2 sm:grid-cols-3">
        <CounterCard label="Total rows" value={batch.total_rows} tone="neutral" />
        <CounterCard label="Valid" value={batch.valid_rows} tone="success" />
        <CounterCard label="Invalid" value={batch.invalid_rows} tone="error" />
      </div>

      {/* Errors */}
      <IssueGroup title="Errors" items={batch.errors} tone="error" />
      {/* Warnings */}
      <IssueGroup title="Warnings" items={batch.warnings} tone="warning" />

      {/* Confirm */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">Confirm import</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {!hasValidRows ? (
            <p className="text-sm text-muted-foreground">
              No valid rows in this file — nothing to import.
            </p>
          ) : (
            <>
              {hasErrors && (
                <label className="flex cursor-pointer items-start gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={allowPartial}
                    onChange={e => setAllowPartial(e.target.checked)}
                    disabled={loading}
                    className="mt-0.5 size-4 shrink-0 accent-primary"
                  />
                  <span className="text-foreground">
                    Skip invalid rows and import the valid ones anyway.
                  </span>
                </label>
              )}

              {error && <InlineError message={error} />}

              <Button
                onClick={handleConfirm}
                disabled={
                  loading ||
                  (hasErrors && !allowPartial) ||
                  (!canConfirmStrict && !canConfirmPartial)
                }
              >
                {loading && <Loader2 className="size-4 animate-spin" />}
                {hasErrors
                  ? `Import ${batch.valid_rows} valid row${batch.valid_rows === 1 ? '' : 's'}`
                  : `Import all ${batch.valid_rows} row${batch.valid_rows === 1 ? '' : 's'}`}
              </Button>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  )
}

function CounterCard({
  label,
  value,
  tone,
}: {
  label: string
  value: number
  tone: 'neutral' | 'success' | 'error'
}) {
  const toneClass =
    tone === 'success'
      ? 'border-status-success-border bg-status-success-bg/30 text-status-success-fg'
      : tone === 'error'
        ? 'border-status-error-border bg-status-error-bg/30 text-status-error-fg'
        : 'border-border bg-card text-foreground'
  return (
    <div className={`rounded-lg border p-3 ${toneClass}`}>
      <p className="text-xs">{label}</p>
      <p className="text-2xl font-semibold">{value}</p>
    </div>
  )
}

// ─── Phase 3: success ─────────────────────────────────────────────────────────

function SuccessPhase({
  result,
  onRestart,
}: {
  result: ImportConfirmResponse
  onRestart: () => void
}) {
  const [showCreated, setShowCreated] = useState(false)

  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex items-center gap-2 text-base">
          <CheckCircle2 className="size-5 text-status-success-fg" />
          Import complete
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="grid gap-2 sm:grid-cols-3">
          <CounterCard label="Created" value={result.created_count} tone="success" />
          <CounterCard label="Skipped" value={result.skipped_count} tone="neutral" />
          <CounterCard label="Errored" value={result.error_count} tone="error" />
        </div>

        {result.created_users.length > 0 && (
          <div className="space-y-2">
            <button
              type="button"
              onClick={() => setShowCreated(v => !v)}
              className="flex items-center gap-1.5 text-sm font-medium text-foreground"
            >
              {showCreated ? (
                <ChevronDown className="size-3.5" />
              ) : (
                <ChevronRight className="size-3.5" />
              )}
              Created users ({result.created_users.length})
            </button>
            {showCreated && (
              <ul className="space-y-1 rounded-lg border border-border bg-card p-3 text-xs">
                {result.created_users.map(u => (
                  <li key={u.id} className="flex items-center gap-3">
                    <span className="font-mono text-muted-foreground">{u.matricule}</span>
                    <span className="text-foreground">
                      {u.full_name || u.email}
                    </span>
                    <span className="text-muted-foreground">{u.email}</span>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}

        <p className="text-xs text-muted-foreground">
          Imported users were assigned random passwords and must reset on first login. They
          cannot sign in until they use the forgot-password flow.
        </p>

        <Button onClick={onRestart}>Start another import</Button>
      </CardContent>
    </Card>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

type Phase =
  | { kind: 'upload' }
  | { kind: 'preview'; batch: UserImportBatch }
  | { kind: 'success'; result: ImportConfirmResponse }

export function ImportsView() {
  useAuth()
  const [phase, setPhase] = useState<Phase>({ kind: 'upload' })

  const description = useMemo(() => {
    if (phase.kind === 'upload') return 'Bulk-create students or teachers from a CSV/XLSX file.'
    if (phase.kind === 'preview')
      return 'Review what would be created. Nothing is written until you confirm.'
    return 'Import finished. New users must reset their password before they can sign in.'
  }, [phase])

  return (
    <>
      <div className="mb-2">
        <Link
          href="/admin/users"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Users
        </Link>
      </div>
      <PageHeader title="Bulk import users" description={description} />

      {phase.kind === 'upload' && (
        <UploadPhase
          onPreview={batch => setPhase({ kind: 'preview', batch })}
        />
      )}

      {phase.kind === 'preview' && (
        <PreviewPhase
          batch={phase.batch}
          onBack={() => setPhase({ kind: 'upload' })}
          onConfirmed={result => setPhase({ kind: 'success', result })}
        />
      )}

      {phase.kind === 'success' && (
        <SuccessPhase
          result={phase.result}
          onRestart={() => setPhase({ kind: 'upload' })}
        />
      )}
    </>
  )
}
