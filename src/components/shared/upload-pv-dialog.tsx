'use client'

import { useEffect, useRef, useState } from 'react'
import { AlertCircle, FileText, Loader2, Upload } from 'lucide-react'
import { api, ApiClientError } from '@/lib/api-client'
import type { DefenseDetail } from '@/lib/types'
import { Button } from '@/components/ui/button'
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
import { Textarea } from '@/components/ui/textarea'

// Shared by jury PRESIDENT (`/api/jury/defenses/{id}/pv/`) and admin
// (`/api/admin/defenses/{id}/pv/`). Backend validates final_grade ∈ [0, 20] and
// requires a non-blank deliberation + a file; we don't duplicate that here.

interface Props {
  open: boolean
  onOpenChange: (open: boolean) => void
  endpoint: string
  onSuccess: (next: DefenseDetail) => void
}

function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) return err.message
  return err instanceof Error ? err.message : 'An unexpected error occurred.'
}

export function UploadPVDialog({ open, onOpenChange, endpoint, onSuccess }: Props) {
  const [grade, setGrade] = useState('')
  const [deliberation, setDeliberation] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)

  useEffect(() => {
    if (open) {
      setGrade('')
      setDeliberation('')
      setFile(null)
      setError(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    }
  }, [open])

  function handleClose() {
    if (loading) return
    onOpenChange(false)
  }

  async function handleSubmit() {
    const trimmed = deliberation.trim()
    const gradeNum = Number(grade)
    if (!file) {
      setError('Attach the PV document file.')
      return
    }
    if (!trimmed) {
      setError('Write a deliberation.')
      return
    }
    if (!grade || Number.isNaN(gradeNum) || gradeNum < 0 || gradeNum > 20) {
      setError('Final grade must be between 0 and 20.')
      return
    }
    setLoading(true)
    setError(null)
    try {
      const formData = new FormData()
      formData.append('final_grade', String(gradeNum))
      formData.append('deliberation', trimmed)
      formData.append('pv_file', file)
      const next = await api.post<DefenseDetail>(endpoint, formData)
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
      <DialogContent className="max-w-lg">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            <Upload className="size-4 text-primary" />
            Upload PV (procès-verbal)
          </DialogTitle>
          <DialogDescription>
            Record the final grade, deliberation, and PV document. This marks the defense as
            completed.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-4">
          <div className="space-y-1.5">
            <Label htmlFor="pv-grade">Final grade <span className="text-muted-foreground">/ 20</span></Label>
            <Input
              id="pv-grade"
              type="number"
              min={0}
              max={20}
              step="0.25"
              placeholder="e.g. 16.5"
              value={grade}
              onChange={e => setGrade(e.target.value)}
              disabled={loading}
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="pv-deliberation">Deliberation</Label>
            <Textarea
              id="pv-deliberation"
              rows={4}
              placeholder="Jury comments on the defense…"
              value={deliberation}
              onChange={e => setDeliberation(e.target.value)}
              disabled={loading}
              className="resize-none"
            />
          </div>

          <div className="space-y-1.5">
            <Label htmlFor="pv-file">PV document</Label>
            <label
              htmlFor="pv-file"
              className={[
                'flex cursor-pointer items-center gap-3 rounded-lg border-2 border-dashed p-4 text-sm transition-colors',
                file
                  ? 'border-primary/40 bg-primary/5'
                  : 'border-border bg-muted/30 hover:bg-muted/50',
              ].join(' ')}
            >
              <FileText className={file ? 'size-5 text-primary' : 'size-5 text-muted-foreground'} />
              {file ? (
                <div className="min-w-0">
                  <p className="truncate text-sm font-medium text-primary">{file.name}</p>
                  <p className="text-xs text-muted-foreground">
                    {file.size < 1_048_576
                      ? `${(file.size / 1024).toFixed(1)} KB`
                      : `${(file.size / 1_048_576).toFixed(1)} MB`}
                  </p>
                </div>
              ) : (
                <span className="text-muted-foreground">Click to attach the PV file</span>
              )}
              <input
                id="pv-file"
                ref={fileInputRef}
                type="file"
                className="sr-only"
                onChange={e => setFile(e.target.files?.[0] ?? null)}
              />
            </label>
          </div>

          {error && (
            <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </div>

        <DialogFooter>
          <Button variant="outline" onClick={handleClose} disabled={loading}>
            Cancel
          </Button>
          <Button onClick={handleSubmit} disabled={loading}>
            {loading && <Loader2 className="size-4 animate-spin" />}
            Submit PV
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
