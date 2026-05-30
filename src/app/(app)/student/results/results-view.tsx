'use client'

import { useState } from 'react'
import {
  AlertCircle,
  BookOpen,
  Clock,
  MessageSquare,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type { Appeal, Assignment, CampaignStatus, SelectionRound, Team } from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { StatusBadge } from '@/components/shared/status-badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import { Textarea } from '@/components/ui/textarea'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) {
    const d = err.data
    const first = Object.values(d).flat().find(v => typeof v === 'string')
    return first ?? err.message
  }
  return err instanceof Error ? err.message : 'An unexpected error occurred.'
}

function formatDate(iso: string) {
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

const ROUND_LABEL: Record<SelectionRound, string> = {
  FIRST: '1st Round',
  SECOND: '2nd Round',
}

// ─── Loading skeleton ─────────────────────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-[148px] w-full rounded-xl" />
      <Skeleton className="h-[220px] w-full rounded-xl" />
    </div>
  )
}

// ─── Phase-gated empty state ──────────────────────────────────────────────────

function NotPublishedState() {
  return (
    <div className="flex flex-col items-center gap-3 py-10 text-center">
      <div className="flex size-11 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <Clock className="size-5" />
      </div>
      <div className="space-y-1">
        <p className="text-sm font-medium text-foreground">Results not published yet</p>
        <p className="max-w-sm text-sm text-muted-foreground">
          Assignment results will appear here once the Results &amp; Appeals phase opens.
        </p>
      </div>
    </div>
  )
}

// ─── Inline error note ────────────────────────────────────────────────────────

function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function ResultsView() {
  const { user } = useAuth()

  const campaignApi = useApi<CampaignStatus>(() => api.get('/api/campaign/current/'), [])
  const teamApi = useApi<Team>(() => api.get('/api/teams/me/'), [])
  const assignmentApi = useApi<Assignment>(() => api.get('/api/assignments/me/'), [])
  // Returns Appeal object or {} when no appeal exists
  const appealApi = useApi<Appeal | Record<string, never>>(() => api.get('/api/appeals/me/'), [])

  const [reason, setReason] = useState('')
  const [confirmOpen, setConfirmOpen] = useState(false)
  const [submitLoading, setSubmitLoading] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)

  // ── Derived ────────────────────────────────────────────────────────────────

  const campaign = campaignApi.data
  const canViewResult = campaign?.actions.can_view_assignment_result ?? false
  const canSubmitAppeal = campaign?.actions.can_submit_appeal ?? false

  const assignment = assignmentApi.data
  const hasAssignment = !!assignment?.subject_id

  // Normalize {} → null
  const rawAppeal = appealApi.data
  const appeal: Appeal | null =
    rawAppeal && 'appeal_id' in rawAppeal ? (rawAppeal as Appeal) : null

  const isLeader = !!user && teamApi.data?.active_leader?.user.id === user.id

  // ── Actions ────────────────────────────────────────────────────────────────

  async function handleSubmitAppeal() {
    if (!reason.trim()) return
    setSubmitLoading(true)
    setSubmitError(null)
    try {
      await api.post('/api/appeals/', { reason: reason.trim() })
      setConfirmOpen(false)
      setReason('')
      appealApi.refetch()
      assignmentApi.refetch()
      teamApi.refetch()
    } catch (err) {
      setSubmitError(extractMessage(err))
    } finally {
      setSubmitLoading(false)
    }
  }

  // ── Loading ────────────────────────────────────────────────────────────────

  if (campaignApi.isLoading || teamApi.isLoading) return <LoadingSkeleton />

  if (campaignApi.error) {
    return <InlineError message={campaignApi.error} />
  }

  // ── Render ─────────────────────────────────────────────────────────────────

  return (
    <>
      <PageHeader
        title="My Results"
        description="View your assignment result and manage your appeal."
      />

      <div className="space-y-4">
        {/* ── Assignment Result ── */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <BookOpen className="size-4 text-muted-foreground" />
              Assignment Result
            </CardTitle>
          </CardHeader>
          <CardContent>
            {!canViewResult ? (
              <NotPublishedState />
            ) : assignmentApi.isLoading ? (
              <div className="space-y-2">
                <Skeleton className="h-5 w-2/3" />
                <Skeleton className="h-4 w-1/2" />
              </div>
            ) : assignmentApi.error ? (
              <InlineError message={assignmentApi.error} />
            ) : !assignment || !hasAssignment ? (
              <div className="flex flex-col items-center gap-3 py-8 text-center">
                <div className="flex size-11 items-center justify-center rounded-full bg-muted text-muted-foreground">
                  <BookOpen className="size-5" />
                </div>
                <div className="space-y-1">
                  <p className="text-sm font-medium text-foreground">No subject assigned</p>
                  <p className="max-w-sm text-sm text-muted-foreground">
                    Your team was not matched to a subject in this selection round.
                  </p>
                </div>
              </div>
            ) : (
              <div className="space-y-3">
                <p className="text-lg font-semibold text-foreground leading-snug">
                  {assignment.subject_title}
                </p>
                <div className="flex flex-wrap items-center gap-2">
                  <span className="inline-flex h-5 items-center rounded-full bg-muted px-2.5 text-xs font-medium text-muted-foreground">
                    {assignment.team_code}
                  </span>
                  <span className="inline-flex h-5 items-center rounded-full bg-primary/10 px-2.5 text-xs font-medium text-primary">
                    {ROUND_LABEL[assignment.selection_round]}
                  </span>
                  <StatusBadge status={assignment.team_status} />
                </div>
              </div>
            )}
          </CardContent>
        </Card>

        {/* ── Appeal ── */}
        {canViewResult && (
          <Card>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base">
                <MessageSquare className="size-4 text-muted-foreground" />
                Appeal
              </CardTitle>
            </CardHeader>
            <CardContent>
              {appealApi.isLoading ? (
                <div className="space-y-2">
                  <Skeleton className="h-4 w-1/3" />
                  <Skeleton className="h-16 w-full" />
                </div>
              ) : appeal ? (
                /* ── Existing appeal ── */
                <div className="space-y-4">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-muted-foreground">Status</span>
                    <StatusBadge status={appeal.status} />
                  </div>

                  <div className="space-y-1">
                    <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                      Your reason
                    </p>
                    <p className="text-sm text-foreground whitespace-pre-wrap">{appeal.reason}</p>
                  </div>

                  <div className="flex flex-wrap gap-x-6 gap-y-1 text-xs text-muted-foreground">
                    <span>Submitted {formatDate(appeal.submitted_at)}</span>
                    {appeal.resolved_at && (
                      <span>Resolved {formatDate(appeal.resolved_at)}</span>
                    )}
                  </div>

                  {appeal.admin_comment && (
                    <div className="rounded-lg border border-border bg-muted/40 p-3 space-y-1">
                      <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide">
                        Admin comment
                      </p>
                      <p className="text-sm text-foreground">{appeal.admin_comment}</p>
                    </div>
                  )}
                </div>
              ) : isLeader && canSubmitAppeal ? (
                /* ── Submit appeal form ── */
                <div className="space-y-4">
                  <p className="text-sm text-muted-foreground">
                    If you believe your assignment was made in error, you can submit an appeal.
                    Submitting will release your current subject assignment and enter your team
                    into the second selection round.
                  </p>

                  <div className="space-y-1.5">
                    <label className="text-sm font-medium text-foreground" htmlFor="appeal-reason">
                      Reason <span className="text-status-error-fg">*</span>
                    </label>
                    <Textarea
                      id="appeal-reason"
                      placeholder="Describe why you are appealing this assignment…"
                      rows={4}
                      value={reason}
                      onChange={e => setReason(e.target.value)}
                      className="resize-none"
                    />
                  </div>

                  {submitError && <InlineError message={submitError} />}

                  <Button
                    onClick={() => setConfirmOpen(true)}
                    disabled={!reason.trim()}
                    variant="outline"
                    className="border-status-error-border text-status-error-fg hover:bg-status-error-bg"
                  >
                    Submit Appeal
                  </Button>
                </div>
              ) : !isLeader ? (
                <p className="text-sm text-muted-foreground">
                  Only the team leader can submit an appeal.
                </p>
              ) : (
                <p className="text-sm text-muted-foreground">
                  The appeal window is not currently open.
                </p>
              )}
            </CardContent>
          </Card>
        )}
      </div>

      {/* ── Confirm submit appeal ── */}
      <ConfirmDialog
        open={confirmOpen}
        onOpenChange={open => {
          if (!submitLoading) {
            setConfirmOpen(open)
            if (!open) setSubmitError(null)
          }
        }}
        title="Submit appeal?"
        description="This will release your current subject assignment and enter your team into the second selection round. This action cannot be undone."
        confirmLabel={submitLoading ? 'Submitting…' : 'Submit Appeal'}
        isLoading={submitLoading}
        onConfirm={handleSubmitAppeal}
      />
    </>
  )
}
