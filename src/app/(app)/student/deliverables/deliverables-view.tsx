'use client'

import { useRef, useState } from 'react'
import {
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Download,
  FileText,
  Loader2,
  Lock,
  MessageSquare,
  Upload,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type {
  CampaignStatus,
  DeliverableFile,
  DeliverableFileComment,
  PaginatedResponse,
  Team,
} from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { EmptyState } from '@/components/shared/empty-state'
import { StatusBadge } from '@/components/shared/status-badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import { buildFileUrl } from '@/lib/config'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1_048_576).toFixed(1)} MB`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

function initials(first: string, last: string): string {
  return `${first[0] ?? ''}${last[0] ?? ''}`.toUpperCase()
}

function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) {
    const d = err.data
    const first = Object.values(d).flat().find(v => typeof v === 'string')
    return first ?? err.message
  }
  return err instanceof Error ? err.message : 'An unexpected error occurred.'
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-[148px] w-full rounded-xl" />
      <Skeleton className="h-[120px] w-full rounded-xl" />
      <Skeleton className="h-[120px] w-full rounded-xl" />
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

// ─── Comment row ──────────────────────────────────────────────────────────────

function CommentRow({ comment }: { comment: DeliverableFileComment }) {
  return (
    <div className="flex gap-2.5">
      <Avatar size="sm">
        <AvatarFallback className="bg-primary/10 text-xs font-medium text-primary">
          {initials(comment.author.first_name, comment.author.last_name)}
        </AvatarFallback>
      </Avatar>
      <div className="min-w-0 space-y-0.5">
        <p className="text-xs">
          <span className="font-medium text-foreground">
            {comment.author.first_name} {comment.author.last_name}
          </span>
          <span className="ml-2 text-muted-foreground">{formatDate(comment.created_at)}</span>
        </p>
        <p className="text-sm text-foreground">{comment.text}</p>
      </div>
    </div>
  )
}

// ─── File card ────────────────────────────────────────────────────────────────

function FileCard({
  file,
  onRefetch,
}: {
  file: DeliverableFile
  onRefetch: () => void
}) {
  const [showComments, setShowComments] = useState(false)
  const [commentText, setCommentText] = useState('')
  const [commentLoading, setCommentLoading] = useState(false)
  const [commentError, setCommentError] = useState<string | null>(null)

  async function handleAddComment() {
    const text = commentText.trim()
    if (!text) return
    setCommentLoading(true)
    setCommentError(null)
    try {
      await api.post(`/api/deliverable-files/${file.id}/comments/`, { text })
      setCommentText('')
      onRefetch()
    } catch (err) {
      setCommentError(extractMessage(err))
    } finally {
      setCommentLoading(false)
    }
  }

  return (
    <Card>
      <CardContent className="space-y-3 pt-5">
        {/* ── Header row ── */}
        <div className="flex items-start justify-between gap-3">
          <div className="flex min-w-0 items-center gap-2">
            <FileText className="size-4 shrink-0 text-muted-foreground" />
            <span className="truncate text-sm font-medium text-foreground">
              {file.original_filename}
            </span>
          </div>
          <div className="flex shrink-0 items-center gap-2">
            <StatusBadge status={file.review_status} />
            <a
              href={buildFileUrl(file.file_url)}
              target="_blank"
              rel="noopener noreferrer"
              download={file.original_filename}
              aria-label={`Download ${file.original_filename}`}
            >
              <Button variant="ghost" size="icon" className="size-7">
                <Download className="size-3.5" />
              </Button>
            </a>
          </div>
        </div>

        {/* ── Meta row ── */}
        <div className="flex flex-wrap gap-x-4 gap-y-0.5 text-xs text-muted-foreground">
          <span>{formatSize(file.file_size)}</span>
          <span>{file.content_type}</span>
          <span>
            {file.uploaded_by.first_name} {file.uploaded_by.last_name}
          </span>
          <span>{formatDate(file.uploaded_at)}</span>
        </div>

        {/* ── Upload comment ── */}
        {file.comment && (
          <p className="text-sm italic text-muted-foreground">&ldquo;{file.comment}&rdquo;</p>
        )}

        {/* ── Review comment ── */}
        {file.review_comment && (
          <div className="space-y-1 rounded-lg border border-border bg-muted/40 p-3">
            <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
              Review comment
            </p>
            <p className="text-sm text-foreground">{file.review_comment}</p>
            {file.reviewed_at && (
              <p className="text-xs text-muted-foreground">
                {file.reviewed_by
                  ? `${file.reviewed_by.first_name} ${file.reviewed_by.last_name} · `
                  : ''}
                {formatDate(file.reviewed_at)}
              </p>
            )}
          </div>
        )}

        {/* ── Comments toggle ── */}
        <Separator />
        <button
          className="flex w-full items-center justify-between text-xs font-medium text-muted-foreground transition-colors hover:text-foreground"
          onClick={() => setShowComments(v => !v)}
          type="button"
        >
          <span className="flex items-center gap-1.5">
            <MessageSquare className="size-3.5" />
            {file.comments.length === 0
              ? 'No comments'
              : `${file.comments.length} comment${file.comments.length === 1 ? '' : 's'}`}
          </span>
          {showComments ? (
            <ChevronUp className="size-3.5" />
          ) : (
            <ChevronDown className="size-3.5" />
          )}
        </button>

        {showComments && (
          <div className="space-y-3 pt-1">
            {file.comments.map(c => (
              <CommentRow key={c.id} comment={c} />
            ))}

            {/* ── Add comment ── */}
            <div className="space-y-2 pt-1">
              <Textarea
                placeholder="Add a comment…"
                rows={2}
                value={commentText}
                onChange={e => setCommentText(e.target.value)}
                className="resize-none text-sm"
              />
              {commentError && (
                <p className="text-xs text-status-error-fg">{commentError}</p>
              )}
              <Button
                size="sm"
                variant="outline"
                disabled={!commentText.trim() || commentLoading}
                onClick={handleAddComment}
              >
                {commentLoading && <Loader2 className="size-3.5 animate-spin" />}
                Post
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Upload not-available notice ──────────────────────────────────────────────

function UploadNotice({ reason }: { reason: string }) {
  return (
    <div className="flex items-start gap-2.5 rounded-lg border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
      <Lock className="mt-0.5 size-4 shrink-0" />
      <span>{reason}</span>
    </div>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function DeliverablesView() {
  useAuth() // ensures redirect on unauthenticated access

  const campaignApi = useApi<CampaignStatus>(() => api.get('/api/campaign/current/'), [])
  const teamApi = useApi<Team>(() => api.get('/api/teams/me/'), [])
  const filesApi = useApi<PaginatedResponse<DeliverableFile>>(() => api.get('/api/deliverable-files/me/'), [])

  const fileInputRef = useRef<HTMLInputElement>(null)
  const [selectedFile, setSelectedFile] = useState<File | null>(null)
  const [uploadComment, setUploadComment] = useState('')
  const [uploadLoading, setUploadLoading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)

  // ── Derived ────────────────────────────────────────────────────────────────

  const openPhases = campaignApi.data?.open_phases ?? []
  const team = teamApi.data

  const uploadBlockReason: string | null = (() => {
    if (!team) return null // still loading
    if (team.status !== 'VALIDATED')
      return 'Your team must be validated before you can upload deliverables.'
    if (!team.selected_subject_id)
      return 'Your team must have an assigned subject before you can upload deliverables.'
    if (!openPhases.includes('WORK_AND_SUPERVISION'))
      return 'Deliverable uploads are only available during the Work & Supervision phase.'
    return null
  })()

  const canUpload = uploadBlockReason === null && !teamApi.isLoading && !campaignApi.isLoading

  // ── Upload ─────────────────────────────────────────────────────────────────

  async function handleUpload() {
    if (!selectedFile) return
    setUploadLoading(true)
    setUploadError(null)
    try {
      const formData = new FormData()
      formData.append('file', selectedFile)
      if (uploadComment.trim()) formData.append('comment', uploadComment.trim())
      await api.post<DeliverableFile>('/api/deliverable-files/upload/', formData)
      // Reset form
      setSelectedFile(null)
      setUploadComment('')
      if (fileInputRef.current) fileInputRef.current.value = ''
      filesApi.refetch()
    } catch (err) {
      setUploadError(extractMessage(err))
    } finally {
      setUploadLoading(false)
    }
  }

  // ── Loading ────────────────────────────────────────────────────────────────

  if (campaignApi.isLoading || teamApi.isLoading) return <LoadingSkeleton />

  if (campaignApi.error) return <InlineError message={campaignApi.error} />

  // ── Render ─────────────────────────────────────────────────────────────────

  const files = filesApi.data?.results ?? []

  return (
    <>
      <PageHeader
        title="Deliverables"
        description="Upload files and track review status for your team's project."
      />

      <div className="space-y-6">
        {/* ── Upload card ── */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Upload className="size-4 text-muted-foreground" />
              Upload File
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            {canUpload ? (
              <>
                {/* File picker */}
                <label
                  htmlFor="file-upload"
                  className={[
                    'flex cursor-pointer flex-col items-center gap-3 rounded-lg border-2 border-dashed p-8 text-center transition-colors',
                    selectedFile
                      ? 'border-primary/40 bg-primary/5'
                      : 'border-border bg-muted/30 hover:bg-muted/50',
                  ].join(' ')}
                >
                  <FileText
                    className={[
                      'size-8',
                      selectedFile ? 'text-primary' : 'text-muted-foreground',
                    ].join(' ')}
                  />
                  {selectedFile ? (
                    <div>
                      <p className="text-sm font-medium text-primary">{selectedFile.name}</p>
                      <p className="text-xs text-muted-foreground">{formatSize(selectedFile.size)}</p>
                    </div>
                  ) : (
                    <div>
                      <p className="text-sm font-medium text-foreground">Click to select a file</p>
                      <p className="text-xs text-muted-foreground">
                        Any file type accepted
                      </p>
                    </div>
                  )}
                  <input
                    id="file-upload"
                    ref={fileInputRef}
                    type="file"
                    className="sr-only"
                    onChange={e => setSelectedFile(e.target.files?.[0] ?? null)}
                  />
                </label>

                {/* Optional comment */}
                <div className="space-y-1.5">
                  <label
                    htmlFor="upload-comment"
                    className="text-sm font-medium text-foreground"
                  >
                    Comment <span className="font-normal text-muted-foreground">(optional)</span>
                  </label>
                  <Textarea
                    id="upload-comment"
                    placeholder="Add a note about this file…"
                    rows={2}
                    value={uploadComment}
                    onChange={e => setUploadComment(e.target.value)}
                    className="resize-none"
                  />
                </div>

                {uploadError && <InlineError message={uploadError} />}

                <Button
                  disabled={!selectedFile || uploadLoading}
                  onClick={handleUpload}
                >
                  {uploadLoading ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      Uploading…
                    </>
                  ) : (
                    <>
                      <Upload className="size-4" />
                      Upload
                    </>
                  )}
                </Button>
              </>
            ) : (
              <UploadNotice
                reason={
                  uploadBlockReason ??
                  'Check back when your team has a validated assignment during the Work & Supervision phase.'
                }
              />
            )}
          </CardContent>
        </Card>

        {/* ── Files list ── */}
        <div className="space-y-3">
          <h2 className="text-sm font-semibold text-foreground">
            Uploaded Files
            {files.length > 0 && (
              <span className="ml-2 font-normal text-muted-foreground">({files.length})</span>
            )}
          </h2>

          {filesApi.isLoading ? (
            <div className="space-y-3">
              <Skeleton className="h-[100px] w-full rounded-xl" />
              <Skeleton className="h-[100px] w-full rounded-xl" />
            </div>
          ) : filesApi.error ? (
            <InlineError message={filesApi.error} />
          ) : files.length === 0 ? (
            <EmptyState
              icon={FileText}
              title="No files yet"
              description="Upload a file above to track your project deliverables."
            />
          ) : (
            files.map(file => (
              <FileCard key={file.id} file={file} onRefetch={filesApi.refetch} />
            ))
          )}
        </div>
      </div>
    </>
  )
}
