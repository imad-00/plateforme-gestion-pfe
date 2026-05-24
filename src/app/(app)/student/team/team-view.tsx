'use client'

import { useState } from 'react'
import {
  ArrowRightLeft,
  Check,
  Crown,
  Loader2,
  Lock,
  LogOut,
  UserPlus,
  Users,
  X,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api } from '@/lib/api-client'
import { ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type { Participation, ReceivedInvitation, Team } from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { EmptyState } from '@/components/shared/empty-state'
import { StatusBadge } from '@/components/shared/status-badge'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardAction,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
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
import { Skeleton } from '@/components/ui/skeleton'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function initials(first: string, last: string) {
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

function buildInviteBody(value: string): Record<string, string | number> {
  const v = value.trim()
  if (v.includes('@')) return { email: v }
  const n = parseInt(v, 10)
  if (!isNaN(n) && String(n) === v) return { student_id: n }
  return { matricule: v }
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function UserAvatar({ first, last }: { first: string; last: string }) {
  return (
    <Avatar size="sm">
      <AvatarFallback className="bg-primary/10 text-xs font-medium text-primary">
        {initials(first, last)}
      </AvatarFallback>
    </Avatar>
  )
}

function LoadingSkeleton() {
  return (
    <div className="space-y-4">
      <Skeleton className="h-[88px] w-full rounded-xl" />
      <Skeleton className="h-[160px] w-full rounded-xl" />
    </div>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

type ConfirmState = {
  title: string
  description: string
  destructive?: boolean
  confirmLabel?: string
  action: () => Promise<unknown>
}

export function TeamView() {
  const { user } = useAuth()

  const teamApi = useApi<Team>(() => api.get('/api/teams/me/'), [])
  const invitationsApi = useApi<ReceivedInvitation[]>(
    () => api.get('/api/team-invitations/received/'),
    [],
  )

  // Invite dialog
  const [inviteOpen, setInviteOpen] = useState(false)
  const [inviteValue, setInviteValue] = useState('')
  const [inviteLoading, setInviteLoading] = useState(false)
  const [inviteError, setInviteError] = useState<string | null>(null)

  // Confirm dialog
  const [confirm, setConfirm] = useState<ConfirmState | null>(null)
  const [confirmLoading, setConfirmLoading] = useState(false)

  // Inline action spinners (accept invitation buttons)
  const [busyKey, setBusyKey] = useState<string | null>(null)

  // ── Derived state ──────────────────────────────────────────────────────────

  const team = teamApi.data
  const isLeader = !!user && team?.active_leader?.user.id === user.id
  const isForming = team?.status === 'FORMING'
  const receivedInvitations = invitationsApi.data ?? []

  // ── Actions ────────────────────────────────────────────────────────────────

  function refetchAll() {
    teamApi.refetch()
    invitationsApi.refetch()
  }

  async function runConfirm() {
    if (!confirm) return
    setConfirmLoading(true)
    try {
      await confirm.action()
      setConfirm(null)
      refetchAll()
    } finally {
      setConfirmLoading(false)
    }
  }

  async function handleInvite() {
    if (!team || !inviteValue.trim()) return
    setInviteLoading(true)
    setInviteError(null)
    try {
      await api.post(`/api/teams/${team.team_code}/invite/`, buildInviteBody(inviteValue))
      setInviteOpen(false)
      setInviteValue('')
      teamApi.refetch()
    } catch (err) {
      setInviteError(extractMessage(err))
    } finally {
      setInviteLoading(false)
    }
  }

  async function handleAccept(participationId: string) {
    setBusyKey(participationId)
    try {
      await api.post(`/api/team-invitations/${participationId}/accept/`)
      refetchAll()
    } finally {
      setBusyKey(null)
    }
  }

  function closeInvite() {
    if (inviteLoading) return
    setInviteOpen(false)
    setInviteValue('')
    setInviteError(null)
  }

  // ── Loading / error states ─────────────────────────────────────────────────

  if (teamApi.isLoading) {
    return (
      <>
        <PageHeader title="My Team" description="View and manage your project team." />
        <LoadingSkeleton />
      </>
    )
  }

  if (teamApi.error || !team) {
    return (
      <>
        <PageHeader title="My Team" description="View and manage your project team." />
        <EmptyState
          title="Could not load team"
          description={teamApi.error ?? 'No data returned.'}
          action={
            <Button variant="outline" size="sm" onClick={teamApi.refetch}>
              Retry
            </Button>
          }
        />
      </>
    )
  }

  // Leader + all active members in one list for display
  const memberRows: Participation[] = [
    ...(team.active_leader ? [team.active_leader] : []),
    ...team.active_members,
  ]

  return (
    <>
      <PageHeader
        title="My Team"
        description="View and manage your project team."
        action={
          isLeader && isForming ? (
            <Button
              size="sm"
              variant="outline"
              className="gap-1.5 border-status-warning-border text-status-warning-fg hover:bg-status-warning-bg"
              onClick={() =>
                setConfirm({
                  title: 'Lock team?',
                  description:
                    'The team status will change to LOCKED. Membership changes will no longer be possible. This cannot be undone.',
                  destructive: true,
                  confirmLabel: 'Lock Team',
                  action: () => api.post(`/api/teams/${team.team_code}/lock/`),
                })
              }
            >
              <Lock className="size-3.5" />
              Lock Team
            </Button>
          ) : undefined
        }
      />

      <div className="space-y-4">
        {/* ── Team info ── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">{team.name}</CardTitle>
            <CardAction>
              <StatusBadge status={team.status} />
            </CardAction>
            <p className="col-span-2 text-xs text-muted-foreground">
              Code:{' '}
              <span className="font-mono font-medium text-foreground">{team.team_code}</span>
              {' · '}
              {team.active_student_count}{' '}
              {team.active_student_count === 1 ? 'member' : 'members'}
              {team.annual_average && (
                <>
                  {' · '}Average:{' '}
                  <span className="font-medium text-foreground">{team.annual_average}</span>
                </>
              )}
            </p>
          </CardHeader>
        </Card>

        {/* ── Members ── */}
        <Card>
          <CardHeader className="border-b">
            <CardTitle>Members</CardTitle>
            {/* MEMBER leave button lives here so it's always visible */}
            {!isLeader && isForming && (
              <CardAction>
                <Button
                  size="sm"
                  variant="destructive"
                  className="gap-1.5"
                  onClick={() =>
                    setConfirm({
                      title: 'Leave this team?',
                      description:
                        'You will be removed from the team and returned to your solo team. This cannot be undone.',
                      destructive: true,
                      confirmLabel: 'Leave Team',
                      action: () => api.post('/api/teams/leave/'),
                    })
                  }
                >
                  <LogOut className="size-3.5" />
                  Leave Team
                </Button>
              </CardAction>
            )}
          </CardHeader>

          <CardContent className="pt-1">
            {memberRows.length === 0 ? (
              <p className="py-6 text-center text-sm text-muted-foreground">No members yet.</p>
            ) : (
              <ul>
                {memberRows.map((p) => {
                  const isSelf = p.user.id === user?.id
                  const isLeaderRow = p.role === 'LEADER'
                  return (
                    <li
                      key={p.participation_id}
                      className="flex items-center gap-3 border-b border-border py-2.5 last:border-0"
                    >
                      <UserAvatar first={p.user.first_name} last={p.user.last_name} />

                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">
                          {p.user.first_name} {p.user.last_name}
                          {isSelf && (
                            <span className="ml-1.5 text-xs font-normal text-muted-foreground">
                              (you)
                            </span>
                          )}
                        </p>
                        <p className="truncate text-xs text-muted-foreground">
                          {p.user.matricule}
                        </p>
                      </div>

                      <div className="flex shrink-0 items-center gap-2">
                        {isLeaderRow && (
                          <span className="inline-flex h-5 items-center gap-1 rounded-full bg-primary/10 px-2 text-xs font-medium text-primary">
                            <Crown className="size-3" />
                            Leader
                          </span>
                        )}

                        {/* Leader actions on non-leader rows */}
                        {isLeader && !isLeaderRow && isForming && (
                          <>
                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 gap-1 px-2 text-xs text-muted-foreground hover:text-foreground"
                              onClick={() =>
                                setConfirm({
                                  title: 'Transfer leadership?',
                                  description: `${p.user.first_name} ${p.user.last_name} will become the new team leader.`,
                                  confirmLabel: 'Transfer',
                                  action: () =>
                                    api.post(
                                      `/api/teams/${team.team_code}/transfer-leadership/`,
                                      { new_leader_id: p.user.id },
                                    ),
                                })
                              }
                            >
                              <ArrowRightLeft className="size-3" />
                              Transfer
                            </Button>

                            <Button
                              variant="ghost"
                              size="sm"
                              className="h-7 gap-1 px-2 text-xs text-muted-foreground hover:text-status-error-fg"
                              onClick={() =>
                                setConfirm({
                                  title: 'Remove member?',
                                  description: `${p.user.first_name} ${p.user.last_name} will be removed from the team.`,
                                  destructive: true,
                                  confirmLabel: 'Remove',
                                  action: () =>
                                    api.post(
                                      `/api/teams/${team.team_code}/remove-member/`,
                                      { student_id: p.user.id },
                                    ),
                                })
                              }
                            >
                              <X className="size-3" />
                              Remove
                            </Button>
                          </>
                        )}
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </CardContent>
        </Card>

        {/* ── Supervisors ── */}
        {team.active_supervisors.length > 0 && (
          <Card>
            <CardHeader className="border-b">
              <CardTitle>Supervisors</CardTitle>
            </CardHeader>
            <CardContent className="pt-1">
              <ul>
                {team.active_supervisors.map((p) => (
                  <li
                    key={p.participation_id}
                    className="flex items-center gap-3 border-b border-border py-2.5 last:border-0"
                  >
                    <UserAvatar first={p.user.first_name} last={p.user.last_name} />
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">
                        {p.user.first_name} {p.user.last_name}
                      </p>
                      <p className="truncate text-xs text-muted-foreground">{p.user.email}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}

        {/* ── Outgoing invitations (leader, FORMING only) ── */}
        {isLeader && isForming && (
          <Card>
            <CardHeader className="border-b">
              <CardTitle>Pending Invitations</CardTitle>
              <CardAction>
                <Button size="sm" className="gap-1.5" onClick={() => setInviteOpen(true)}>
                  <UserPlus className="size-3.5" />
                  Invite Student
                </Button>
              </CardAction>
            </CardHeader>
            <CardContent className="pt-1">
              {team.pending_invitations.length === 0 ? (
                <p className="py-6 text-center text-sm text-muted-foreground">
                  No pending invitations. Use the button above to invite a student.
                </p>
              ) : (
                <ul>
                  {team.pending_invitations.map((p) => (
                    <li
                      key={p.participation_id}
                      className="flex items-center gap-3 border-b border-border py-2.5 last:border-0"
                    >
                      <UserAvatar first={p.user.first_name} last={p.user.last_name} />
                      <div className="min-w-0 flex-1">
                        <p className="truncate text-sm font-medium">
                          {p.user.first_name} {p.user.last_name}
                        </p>
                        <p className="truncate text-xs text-muted-foreground">
                          {p.user.matricule}
                        </p>
                      </div>
                      <StatusBadge status="PENDING" className="shrink-0" />
                    </li>
                  ))}
                </ul>
              )}
            </CardContent>
          </Card>
        )}

        {/* ── Received invitations ── */}
        {receivedInvitations.length > 0 && (
          <Card>
            <CardHeader className="border-b">
              <CardTitle>Team Invitations</CardTitle>
            </CardHeader>
            <CardContent className="pt-1">
              <ul>
                {receivedInvitations.map((inv) => (
                  <li
                    key={inv.participation_id}
                    className="flex items-center gap-3 border-b border-border py-2.5 last:border-0"
                  >
                    <div className="flex size-6 shrink-0 items-center justify-center rounded-full bg-muted">
                      <Users className="size-3 text-muted-foreground" />
                    </div>

                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium">{inv.team.name}</p>
                      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
                        <span>
                          {inv.team.active_student_count}{' '}
                          {inv.team.active_student_count === 1 ? 'member' : 'members'}
                        </span>
                        <span>·</span>
                        <StatusBadge status={inv.team.status} />
                      </div>
                    </div>

                    <div className="flex shrink-0 items-center gap-2">
                      <Button
                        size="sm"
                        variant="outline"
                        className="h-7 gap-1 px-2.5 text-xs"
                        disabled={busyKey === inv.participation_id}
                        onClick={() => handleAccept(inv.participation_id)}
                      >
                        {busyKey === inv.participation_id ? (
                          <Loader2 className="size-3 animate-spin" />
                        ) : (
                          <Check className="size-3" />
                        )}
                        Accept
                      </Button>

                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 gap-1 px-2.5 text-xs text-muted-foreground hover:text-status-error-fg"
                        onClick={() =>
                          setConfirm({
                            title: 'Decline invitation?',
                            description: `You will decline the invitation to join ${inv.team.name}.`,
                            destructive: true,
                            confirmLabel: 'Decline',
                            action: () =>
                              api.post(
                                `/api/team-invitations/${inv.participation_id}/reject/`,
                              ),
                          })
                        }
                      >
                        <X className="size-3" />
                        Decline
                      </Button>
                    </div>
                  </li>
                ))}
              </ul>
            </CardContent>
          </Card>
        )}
      </div>

      {/* ── Invite dialog ── */}
      <Dialog open={inviteOpen} onOpenChange={(v) => { if (!v) closeInvite() }}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Invite a Student</DialogTitle>
            <DialogDescription>
              Enter the student&apos;s matricule, email address, or numeric ID.
            </DialogDescription>
          </DialogHeader>

          <div className="space-y-1.5">
            <Label htmlFor="invite-input">Student identifier</Label>
            <Input
              id="invite-input"
              placeholder="e.g. STU001 or student@example.com"
              value={inviteValue}
              autoFocus
              disabled={inviteLoading}
              onChange={(e) => {
                setInviteValue(e.target.value)
                setInviteError(null)
              }}
              onKeyDown={(e) => { if (e.key === 'Enter') handleInvite() }}
            />
            {inviteError && (
              <p className="text-xs text-status-error-fg">{inviteError}</p>
            )}
          </div>

          <DialogFooter>
            <Button variant="outline" disabled={inviteLoading} onClick={closeInvite}>
              Cancel
            </Button>
            <Button
              disabled={inviteLoading || !inviteValue.trim()}
              onClick={handleInvite}
            >
              {inviteLoading && <Loader2 className="size-4 animate-spin" />}
              Send Invitation
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      {/* ── Confirm dialog ── */}
      <ConfirmDialog
        open={!!confirm}
        onOpenChange={(v) => { if (!v) setConfirm(null) }}
        title={confirm?.title ?? ''}
        description={confirm?.description ?? ''}
        confirmLabel={confirm?.confirmLabel}
        destructive={confirm?.destructive}
        isLoading={confirmLoading}
        onConfirm={runConfirm}
      />
    </>
  )
}
