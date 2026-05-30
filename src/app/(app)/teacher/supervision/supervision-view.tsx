'use client'

import { useState } from 'react'
import {
  AlertCircle,
  ChevronDown,
  ChevronUp,
  Download,
  FileText,
  Loader2,
  MessageSquare,
  Users,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import { buildFileUrl } from '@/lib/config'
import { useApi } from '@/hooks/use-api'
import type {
  DeliverableFile,
  DeliverableFileComment,
  MemberSummary,
  PaginatedResponse,
  ReviewStatus,
  SupervisionTeam,
} from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { EmptyState } from '@/components/shared/empty-state'
import { StatusBadge } from '@/components/shared/status-badge'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

// ─── Constants ────────────────────────────────────────────────────────────────

const REVIEW_OPTIONS: { value: ReviewStatus; label: string }[] = [
  { value: 'ACCEPTED', label: 'Accepted' },
  { value: 'NEEDS_REVISION', label: 'Needs Revision' },
  { value: 'REJECTED', label: 'Rejected' },
]

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

function memberInitials(m: MemberSummary): string {
  return initials(m.first_name, m.last_name)
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
      <Skeleton className="h-[112px] w-full rounded-xl" />
      <Skeleton className="h-[112px] w-full rounded-xl" />
      <Skeleton className="h-[112px] w-full rounded-xl" />
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

// ─── Supervisor file card ─────────────────────────────────────────────────────

interface ReviewConfirmState {
  status: ReviewStatus
  comment: string
}

function SupervisorFileCard({
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

  const [reviewStatus, setReviewStatus] = useState<ReviewStatus | ''>('')
  const [reviewComment, setReviewComment] = useState('')
  const [reviewConfirm, setReviewConfirm] = useState<ReviewConfirmState | null>(null)
  const [reviewLoading, setReviewLoading] = useState(false)
  const [reviewError, setReviewError] = useState<string | null>(null)

  function openReviewConfirm() {
    if (!reviewStatus) return
    setReviewConfirm({ status: reviewStatus, comment: reviewComment })
  }

  async function handleReview() {
    if (!reviewConfirm) return
    setReviewLoading(true)
    setReviewError(null)
    try {
      await api.post(`/api/deliverable-files/${file.id}/review/`, {
        review_status: reviewConfirm.status,
        ...(reviewConfirm.comment.trim() ? { review_comment: reviewConfirm.comment.trim() } : {}),
      })
      setReviewConfirm(null)
      setReviewStatus('')
      setReviewComment('')
      onRefetch()
    } catch (err) {
      setReviewError(extractMessage(err))
      setReviewConfirm(null)
    } finally {
      setReviewLoading(false)
    }
  }

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
    <>
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

          {/* ── Existing review ── */}
          {file.review_comment && (
            <div className="space-y-1 rounded-lg border border-border bg-muted/40 p-3">
              <p className="text-xs font-medium uppercase tracking-wide text-muted-foreground">
                Your review
              </p>
              <p className="text-sm text-foreground">{file.review_comment}</p>
              {file.reviewed_at && (
                <p className="text-xs text-muted-foreground">{formatDate(file.reviewed_at)}</p>
              )}
            </div>
          )}

          {/* ── Review form ── */}
          <Separator />
          <div className="space-y-2">
            <p className="text-xs font-medium text-muted-foreground">Submit review</p>
            <Select
              value={reviewStatus}
              onValueChange={v => setReviewStatus(v as ReviewStatus)}
            >
              <SelectTrigger className="h-8 text-sm">
                <SelectValue placeholder="Select a verdict…" />
              </SelectTrigger>
              <SelectContent>
                {REVIEW_OPTIONS.map(opt => (
                  <SelectItem key={opt.value} value={opt.value}>
                    {opt.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Textarea
              placeholder="Review comment (optional)…"
              rows={2}
              value={reviewComment}
              onChange={e => setReviewComment(e.target.value)}
              className="resize-none text-sm"
            />
            {reviewError && <p className="text-xs text-status-error-fg">{reviewError}</p>}
            <Button
              size="sm"
              disabled={!reviewStatus || reviewLoading}
              onClick={openReviewConfirm}
            >
              {reviewLoading && <Loader2 className="size-3.5 animate-spin" />}
              Submit Review
            </Button>
          </div>

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

      <ConfirmDialog
        open={reviewConfirm !== null}
        onOpenChange={open => { if (!open) setReviewConfirm(null) }}
        title="Submit Review"
        description={`Mark this file as "${REVIEW_OPTIONS.find(o => o.value === reviewConfirm?.status)?.label ?? ''}"${reviewConfirm?.comment ? ` with comment: "${reviewConfirm.comment}"` : ''}. The student will see this decision.`}
        confirmLabel="Submit"
        isLoading={reviewLoading}
        onConfirm={handleReview}
      />
    </>
  )
}

// ─── Team files panel ─────────────────────────────────────────────────────────

function TeamFilesPanel({ teamCode }: { teamCode: string }) {
  const filesApi = useApi<PaginatedResponse<DeliverableFile>>(
    () => api.get(`/api/supervision/teams/${teamCode}/files/`),
    [teamCode],
  )

  const files = filesApi.data?.results ?? []

  if (filesApi.isLoading) {
    return (
      <div className="space-y-3 px-4 pb-4">
        <Skeleton className="h-[100px] w-full rounded-xl" />
        <Skeleton className="h-[100px] w-full rounded-xl" />
      </div>
    )
  }

  if (filesApi.error) {
    return (
      <div className="px-4 pb-4">
        <InlineError message={filesApi.error} />
      </div>
    )
  }

  if (files.length === 0) {
    return (
      <div className="px-4 pb-4">
        <EmptyState
          icon={FileText}
          title="No files yet"
          description="The team hasn't uploaded any deliverables."
        />
      </div>
    )
  }

  return (
    <div className="space-y-3 px-4 pb-4">
      {files.map(file => (
        <SupervisorFileCard
          key={file.id}
          file={file}
          onRefetch={filesApi.refetch}
        />
      ))}
    </div>
  )
}

// ─── Team card ────────────────────────────────────────────────────────────────

function TeamCard({ team }: { team: SupervisionTeam }) {
  const [expanded, setExpanded] = useState(false)

  const filesCount = Number(team.files_count)
  const subjectId = team.selected_subject_id

  return (
    <Card>
      {/* ── Header ── */}
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0 space-y-1">
            <div className="flex flex-wrap items-center gap-2">
              <CardTitle className="text-base">{team.name}</CardTitle>
              <span className="font-mono text-xs text-muted-foreground">{team.team_code}</span>
              <StatusBadge status={team.status} />
            </div>
            <p className="text-xs text-muted-foreground">
              {subjectId
                ? `Subject #${subjectId} assigned`
                : 'No subject assigned yet'}
              {' · '}
              {filesCount === 0
                ? 'No files uploaded'
                : `${filesCount} file${filesCount === 1 ? '' : 's'} uploaded`}
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            className="shrink-0"
            onClick={() => setExpanded(v => !v)}
          >
            {expanded ? (
              <>
                <ChevronUp className="size-4" />
                Hide Files
              </>
            ) : (
              <>
                <ChevronDown className="size-4" />
                View Files
              </>
            )}
          </Button>
        </div>
      </CardHeader>

      {/* ── Members ── */}
      <CardContent className="pt-0">
        {team.members_summary.length > 0 && (
          <div className="flex flex-wrap items-center gap-2">
            <Users className="size-3.5 shrink-0 text-muted-foreground" />
            {team.members_summary.map(m => (
              <span
                key={m.id}
                className="flex items-center gap-1.5 rounded-full border border-border bg-muted/40 px-2 py-0.5"
              >
                <Avatar size="sm">
                  <AvatarFallback className="size-4 bg-primary/10 text-[9px] font-medium text-primary">
                    {memberInitials(m)}
                  </AvatarFallback>
                </Avatar>
                <span className="text-xs text-foreground">
                  {m.first_name} {m.last_name}
                </span>
              </span>
            ))}
          </div>
        )}
      </CardContent>

      {/* ── Expandable files panel ── */}
      {expanded && (
        <>
          <Separator />
          <div className="pt-4">
            <TeamFilesPanel teamCode={team.team_code} />
          </div>
        </>
      )}
    </Card>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function SupervisionView() {
  useAuth()

  const teamsApi = useApi<PaginatedResponse<SupervisionTeam>>(
    () => api.get('/api/supervision/teams/'),
    [],
  )

  const teams = teamsApi.data?.results ?? []

  return (
    <>
      <PageHeader
        title="Supervision"
        description="Review deliverables and manage your supervised teams."
      />

      {teamsApi.isLoading ? (
        <LoadingSkeleton />
      ) : teamsApi.error ? (
        <InlineError message={teamsApi.error} />
      ) : teams.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No supervised teams"
          description="You are not currently assigned as supervisor to any team."
        />
      ) : (
        <div className="space-y-4">
          {teams.map(team => (
            <TeamCard key={team.team_code} team={team} />
          ))}
        </div>
      )}
    </>
  )
}
