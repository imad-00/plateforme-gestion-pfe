'use client'

import { useCallback, useState } from 'react'
import {
  AlertCircle,
  CalendarClock,
  CheckCircle2,
  Clock,
  FileText,
  Lock,
  ShieldQuestion,
  Users,
  XCircle,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type {
  CampaignStatus,
  DefenseDetail,
  DefenseListItem,
  DefenseSupervisorDecisionStatus,
  PaginatedResponse,
} from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { EmptyState } from '@/components/shared/empty-state'
import { StatusBadge } from '@/components/shared/status-badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
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

// ─── Inline error ─────────────────────────────────────────────────────────────

function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

// ─── Decision pill ────────────────────────────────────────────────────────────

function DecisionIcon({ decision }: { decision: DefenseSupervisorDecisionStatus }) {
  if (decision === 'ACCEPTED') return <CheckCircle2 className="size-4 text-status-success-fg" />
  if (decision === 'DENIED') return <XCircle className="size-4 text-status-error-fg" />
  return <Clock className="size-4 text-muted-foreground" />
}

// ─── Request card ─────────────────────────────────────────────────────────────

function RequestCard({
  request,
  currentUserId,
  onAct,
}: {
  request: DefenseListItem
  currentUserId: number
  onAct: (id: string, decision: 'ACCEPTED' | 'DENIED', detail: DefenseDetail) => void
}) {
  // Jury detail endpoint also accepts active supervisors via can_access_defense_files,
  // so it doubles as the supervisor detail view.
  const detailApi = useApi<DefenseDetail>(
    () => api.get(`/api/jury/defenses/${request.id}/`),
    [request.id],
  )

  const detail = detailApi.data
  const attached = detail?.attached_files ?? []

  const myDecision =
    detail?.supervisor_decisions.find(d => d.supervisor.id === currentUserId) ?? null
  const canDecide = request.status === 'REQUESTED' && myDecision?.decision === 'PENDING'

  return (
    <Card>
      <CardContent className="space-y-4 pt-5">
        {/* Header */}
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0">
            <div className="flex items-center gap-2">
              <p className="font-semibold text-foreground">{request.team.name}</p>
              <span className="text-xs text-muted-foreground">{request.team.team_code}</span>
            </div>
            <p className="mt-0.5 text-xs text-muted-foreground">
              Requested {formatDateTime(request.requested_at)}
            </p>
          </div>
          <StatusBadge status={request.status} />
        </div>

        {/* Supervisor decisions */}
        {detailApi.isLoading ? (
          <Skeleton className="h-12 w-full rounded-lg" />
        ) : detail ? (
          <div className="space-y-1.5">
            <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <ShieldQuestion className="size-3.5" />
              Supervisor decisions
            </p>
            <div className="flex flex-wrap gap-2">
              {detail.supervisor_decisions.map(d => (
                <div
                  key={d.id}
                  className="flex items-center gap-2 rounded-lg border border-border bg-muted/40 px-2.5 py-1.5"
                >
                  <Avatar size="sm">
                    <AvatarFallback className="bg-primary/10 text-[10px] font-medium text-primary">
                      {initials(d.supervisor.first_name, d.supervisor.last_name)}
                    </AvatarFallback>
                  </Avatar>
                  <span className="text-xs text-foreground">
                    {d.supervisor.first_name} {d.supervisor.last_name}
                  </span>
                  <DecisionIcon decision={d.decision} />
                </div>
              ))}
            </div>
          </div>
        ) : null}

        {/* Attached files */}
        {attached.length > 0 && (
          <div className="space-y-1.5">
            <p className="flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <FileText className="size-3.5" />
              Attached files <span className="font-normal">({attached.length})</span>
            </p>
            <div className="space-y-1.5">
              {attached.map(af => (
                <div
                  key={af.id}
                  className="flex items-center gap-2 rounded-lg border border-border bg-card p-2"
                >
                  <span className="size-5 shrink-0 rounded-md bg-muted text-center text-[11px] font-medium leading-5 text-muted-foreground">
                    {af.order}
                  </span>
                  <FileText className="size-3.5 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-xs font-medium text-foreground">
                      {af.deliverable_file.original_filename}
                    </p>
                    <p className="text-[11px] text-muted-foreground">
                      {formatSize(af.deliverable_file.file_size)}
                    </p>
                  </div>
                  <a
                    href={buildFileUrl(af.deliverable_file.file_url)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-[11px] font-medium text-primary hover:underline"
                  >
                    Open
                  </a>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Scheduled info (if any) */}
        {(request.status === 'SCHEDULED' || request.status === 'COMPLETED') && request.scheduled_at && (
          <div className="flex items-center gap-2 rounded-lg border border-border bg-muted/30 px-3 py-2 text-sm text-foreground">
            <CalendarClock className="size-4 text-muted-foreground" />
            {formatDateTime(request.scheduled_at)}
            {request.location && <span className="text-muted-foreground">· {request.location}</span>}
          </div>
        )}

        {/* Actions */}
        {canDecide && detail && (
          <div className="flex justify-end gap-2 pt-1">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onAct(request.id, 'DENIED', detail)}
            >
              Deny
            </Button>
            <Button size="sm" onClick={() => onAct(request.id, 'ACCEPTED', detail)}>
              Accept
            </Button>
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Decision dialog ──────────────────────────────────────────────────────────

function DecisionDialog({
  open,
  onOpenChange,
  decision,
  defenseId,
  teamName,
  onSuccess,
}: {
  open: boolean
  onOpenChange: (open: boolean) => void
  decision: 'ACCEPTED' | 'DENIED' | null
  defenseId: string | null
  teamName: string
  onSuccess: () => void
}) {
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  async function handleConfirm() {
    if (!defenseId || !decision) return
    setLoading(true)
    setError(null)
    try {
      const endpoint =
        decision === 'ACCEPTED'
          ? `/api/defenses/${defenseId}/accept/`
          : `/api/defenses/${defenseId}/deny/`
      await api.post(endpoint)
      onSuccess()
      onOpenChange(false)
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setLoading(false)
    }
  }

  if (!decision) return null

  const isDeny = decision === 'DENIED'

  return (
    <ConfirmDialog
      open={open}
      onOpenChange={open => {
        if (!loading) {
          if (!open) setError(null)
          onOpenChange(open)
        }
      }}
      title={isDeny ? `Deny defense for ${teamName}?` : `Accept defense for ${teamName}?`}
      description={
        isDeny
          ? 'Denying this request cancels the entire defense workflow for this team. They can submit a new request later.'
          : 'Accepting confirms your supervisor approval. The defense advances to scheduling once all supervisors accept.'
      }
      confirmLabel={isDeny ? 'Deny request' : 'Accept'}
      destructive={isDeny}
      isLoading={loading}
      error={error}
      onConfirm={handleConfirm}
    />
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function DefenseRequestsView() {
  const { user } = useAuth()
  const campaignApi = useApi<CampaignStatus>(() => api.get('/api/campaign/current/'), [])
  const listApi = useApi<PaginatedResponse<DefenseListItem>>(
    () => api.get('/api/supervision/defense-requests/'),
    [],
  )

  const [pending, setPending] = useState<{
    id: string
    decision: 'ACCEPTED' | 'DENIED'
    teamName: string
  } | null>(null)

  const openPhases = campaignApi.data?.open_phases ?? []
  const phaseOpen = openPhases.includes('DEFENSE_WINDOW')

  const handleAct = useCallback(
    (id: string, decision: 'ACCEPTED' | 'DENIED', detail: DefenseDetail) => {
      setPending({ id, decision, teamName: detail.team.name })
    },
    [],
  )

  if (campaignApi.isLoading) {
    return (
      <>
        <PageHeader
          title="Defense requests"
          description="Review and decide on defense requests from the teams you supervise."
        />
        <Skeleton className="h-32 w-full rounded-xl" />
      </>
    )
  }

  if (!phaseOpen) {
    return (
      <>
        <PageHeader
          title="Defense requests"
          description="Review and decide on defense requests from the teams you supervise."
        />
        <div className="flex items-start gap-2.5 rounded-lg border border-border bg-muted/40 p-4 text-sm text-muted-foreground">
          <Lock className="mt-0.5 size-4 shrink-0" />
          <span>The defense workflow is not open right now.</span>
        </div>
      </>
    )
  }

  const items = listApi.data?.results ?? []

  return (
    <>
      <PageHeader
        title="Defense requests"
        description="Review and decide on defense requests from the teams you supervise."
      />

      {listApi.error && <div className="mb-4"><InlineError message={listApi.error} /></div>}

      {listApi.isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={Users}
          title="No defense requests yet"
          description="Teams you supervise will appear here once they submit a defense request."
        />
      ) : (
        <div className="space-y-3">
          {items.map(item => (
            <RequestCard
              key={item.id}
              request={item}
              currentUserId={user?.id ?? -1}
              onAct={handleAct}
            />
          ))}
        </div>
      )}

      <DecisionDialog
        open={!!pending}
        onOpenChange={open => {
          if (!open) setPending(null)
        }}
        decision={pending?.decision ?? null}
        defenseId={pending?.id ?? null}
        teamName={pending?.teamName ?? ''}
        onSuccess={() => {
          setPending(null)
          listApi.refetch()
        }}
      />
    </>
  )
}
