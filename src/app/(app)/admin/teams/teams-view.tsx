'use client'

import { useEffect, useState } from 'react'
import {
  AlertCircle,
  Crown,
  Loader2,
  MoreHorizontal,
  Search,
  UserMinus,
  UserPlus,
  Users,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type {
  AcademicYear,
  PaginatedResponse,
  Team,
  TeamListItem,
  User,
  WishlistListItem,
} from '@/lib/types'
import { DataTable, type Column } from '@/components/shared/data-table'
import { StatusBadge } from '@/components/shared/status-badge'
import { ConfirmDialog } from '@/components/shared/confirm-dialog'
import { EmptyState } from '@/components/shared/empty-state'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Skeleton } from '@/components/ui/skeleton'

// ─── Constants ────────────────────────────────────────────────────────────────

const ROUND_LABELS: Record<string, string> = {
  FIRST: 'Round 1',
  SECOND: 'Round 2',
}

const STATUS_OPTIONS = [
  { value: 'all', label: 'All statuses' },
  { value: 'FORMING', label: 'Forming' },
  { value: 'LOCKED', label: 'Locked' },
  { value: 'VALIDATED', label: 'Validated' },
  { value: 'DISSOLVED', label: 'Dissolved' },
  { value: 'ARCHIVED', label: 'Archived' },
] as const

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleDateString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
  })
}

function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) {
    const d = err.data as Record<string, unknown>
    const first = Object.values(d).flat().find(v => typeof v === 'string')
    return (first as string | undefined) ?? err.message
  }
  return err instanceof Error ? err.message : 'An unexpected error occurred.'
}

// ─── Shared UI ────────────────────────────────────────────────────────────────

function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

function SectionLabel({ children }: { children: React.ReactNode }) {
  return (
    <p className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
      {children}
    </p>
  )
}

// ─── Team detail dialog ───────────────────────────────────────────────────────
// Accepts only a teamCode and fetches the full detail internally (the list
// endpoint returns a slim shape that omits members, supervisors, etc.).

function TeamDetailDialog({
  teamCode,
  open,
  onOpenChange,
}: {
  teamCode: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const [team, setTeam] = useState<Team | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const wishlistsApi = useApi<PaginatedResponse<WishlistListItem>>(
    () =>
      open && teamCode
        ? api.get(`/api/admin/wishlists/?team_code=${teamCode}&page_size=5`)
        : Promise.resolve<PaginatedResponse<WishlistListItem>>({
            count: 0, next: null, previous: null, results: [],
          }),
    [open, teamCode],
  )

  useEffect(() => {
    if (!open || !teamCode) {
      setTeam(null)
      setError(null)
      return
    }
    setLoading(true)
    setError(null)
    api
      .get<Team>(`/api/admin/teams/${teamCode}/`)
      .then(t => setTeam(t))
      .catch(err => setError(extractMessage(err)))
      .finally(() => setLoading(false))
  }, [open, teamCode])

  const wishlists = wishlistsApi.data?.results ?? []

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-h-[85vh] max-w-2xl overflow-y-auto">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {team ? (
              <>
                <span className="font-mono">{team.team_code}</span>
                <span className="text-muted-foreground">—</span>
                <span>{team.name}</span>
              </>
            ) : (
              <span className="font-mono">{teamCode}</span>
            )}
          </DialogTitle>
        </DialogHeader>

        {loading ? (
          <div className="space-y-3">
            <Skeleton className="h-24 w-full rounded-lg" />
            <Skeleton className="h-20 w-full rounded-lg" />
            <Skeleton className="h-20 w-full rounded-lg" />
          </div>
        ) : error ? (
          <InlineError message={error} />
        ) : team ? (
          <div className="space-y-5 text-sm">
            {/* Metadata */}
            <div className="grid grid-cols-2 gap-x-4 gap-y-3 rounded-lg border border-border p-3 sm:grid-cols-3">
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Status</p>
                <StatusBadge status={team.status} />
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Round</p>
                <p className="font-medium">{ROUND_LABELS[team.selection_round] ?? team.selection_round}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Annual average</p>
                <p className="font-medium">{team.annual_average ?? '—'}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Members</p>
                <p className="font-medium">{team.active_student_count}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Assigned subject ID</p>
                <p className="font-mono font-medium">{team.selected_subject_id ?? '—'}</p>
              </div>
              <div className="space-y-1">
                <p className="text-xs text-muted-foreground">Assignment validated</p>
                <p className="font-medium">{formatDate(team.assignment_validated_at)}</p>
              </div>
              {team.dissolved_at && (
                <div className="space-y-1">
                  <p className="text-xs text-muted-foreground">Dissolved</p>
                  <p className="font-medium text-status-error-fg">{formatDate(team.dissolved_at)}</p>
                </div>
              )}
            </div>

            {/* Members */}
            <div className="space-y-2">
              <SectionLabel>Members ({team.active_student_count})</SectionLabel>
              {team.active_members.length === 0 ? (
                <p className="text-muted-foreground">No active members.</p>
              ) : (
                <div className="divide-y divide-border rounded-lg border border-border">
                  {team.active_members.map(p => (
                    <div
                      key={p.participation_id}
                      className="flex items-center justify-between px-3 py-2"
                    >
                      <div>
                        <p className="font-medium">
                          {p.user.first_name} {p.user.last_name}
                          {p.participation_id === team.active_leader?.participation_id && (
                            <span className="ml-1.5 text-xs font-normal text-primary">
                              Leader
                            </span>
                          )}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {p.user.matricule} · {p.user.email}
                        </p>
                      </div>
                      <StatusBadge status={p.status} />
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Supervisors */}
            <div className="space-y-2">
              <SectionLabel>Supervisors ({team.active_supervisors.length})</SectionLabel>
              {team.active_supervisors.length === 0 ? (
                <p className="text-muted-foreground">No supervisors assigned.</p>
              ) : (
                <div className="divide-y divide-border rounded-lg border border-border">
                  {team.active_supervisors.map(p => (
                    <div key={p.participation_id} className="px-3 py-2">
                      <p className="font-medium">
                        {p.user.first_name} {p.user.last_name}
                      </p>
                      <p className="text-xs text-muted-foreground">
                        {p.user.matricule} · {p.user.email}
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Pending invitations */}
            {team.pending_invitations.length > 0 && (
              <div className="space-y-2">
                <SectionLabel>
                  Pending Invitations ({team.pending_invitations.length})
                </SectionLabel>
                <div className="divide-y divide-border rounded-lg border border-border">
                  {team.pending_invitations.map(p => (
                    <div key={p.participation_id} className="px-3 py-2">
                      <p className="font-medium">
                        {p.user.first_name} {p.user.last_name}
                      </p>
                      <p className="text-xs text-muted-foreground">{p.user.matricule}</p>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Wishlists */}
            <div className="space-y-2">
              <SectionLabel>Wishlists</SectionLabel>
              {wishlistsApi.isLoading ? (
                <Skeleton className="h-10 w-full rounded-lg" />
              ) : wishlists.length === 0 ? (
                <p className="text-muted-foreground">No wishlists submitted.</p>
              ) : (
                <div className="divide-y divide-border rounded-lg border border-border">
                  {wishlists.map(w => (
                    <div
                      key={w.wishlist_id}
                      className="flex items-center justify-between px-3 py-2"
                    >
                      <div>
                        <p className="font-medium">
                          {ROUND_LABELS[w.selection_round] ?? w.selection_round}
                        </p>
                        <p className="text-xs text-muted-foreground">
                          {w.item_count} items · submitted {formatDate(w.submitted_at)}
                        </p>
                      </div>
                      <StatusBadge status={w.status} />
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        ) : null}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)}>
            Close
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Manage supervisors dialog ────────────────────────────────────────────────

function ManageSupervisorsDialog({
  teamCode,
  open,
  onOpenChange,
  onSuccess,
}: {
  teamCode: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}) {
  const [team, setTeam] = useState<Team | null>(null)
  const [teamLoading, setTeamLoading] = useState(false)
  const [teamError, setTeamError] = useState<string | null>(null)
  const [selectedUserId, setSelectedUserId] = useState('')
  const [actionLoading, setActionLoading] = useState(false)
  const [actionError, setActionError] = useState<string | null>(null)

  const teachersApi = useApi<PaginatedResponse<User>>(
    () =>
      open
        ? api.get(
            '/api/admin/users/?business_identity=TEACHER&account_status=ACTIVE&page_size=100',
          )
        : Promise.resolve<PaginatedResponse<User>>({
            count: 0, next: null, previous: null, results: [],
          }),
    [open],
  )
  const extSupsApi = useApi<PaginatedResponse<User>>(
    () =>
      open
        ? api.get(
            '/api/admin/users/?business_identity=EXTERNAL_SUPERVISOR&account_status=ACTIVE&page_size=100',
          )
        : Promise.resolve<PaginatedResponse<User>>({
            count: 0, next: null, previous: null, results: [],
          }),
    [open],
  )

  async function loadTeam() {
    if (!teamCode) return
    setTeamLoading(true)
    setTeamError(null)
    try {
      const t = await api.get<Team>(`/api/admin/teams/${teamCode}/`)
      setTeam(t)
    } catch (err) {
      setTeamError(extractMessage(err))
    } finally {
      setTeamLoading(false)
    }
  }

  useEffect(() => {
    if (open && teamCode) {
      loadTeam()
      setActionError(null)
      setSelectedUserId('')
    } else {
      setTeam(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, teamCode])

  async function handleAdd() {
    if (!teamCode || !selectedUserId) return
    setActionLoading(true)
    setActionError(null)
    try {
      await api.post(`/api/admin/teams/${teamCode}/supervisors/`, {
        user_id: Number(selectedUserId),
      })
      setSelectedUserId('')
      await loadTeam()
      onSuccess()
    } catch (err) {
      setActionError(extractMessage(err))
    } finally {
      setActionLoading(false)
    }
  }

  async function handleRemove(userId: number) {
    if (!teamCode) return
    setActionLoading(true)
    setActionError(null)
    try {
      await api.post(`/api/admin/teams/${teamCode}/supervisors/remove/`, { user_id: userId })
      await loadTeam()
      onSuccess()
    } catch (err) {
      setActionError(extractMessage(err))
    } finally {
      setActionLoading(false)
    }
  }

  const currentSupervisorIds = new Set(team?.active_supervisors.map(s => s.user.id) ?? [])
  const allEligible = [
    ...(teachersApi.data?.results ?? []),
    ...(extSupsApi.data?.results ?? []),
  ]
  const availableToAdd = allEligible.filter(u => !currentSupervisorIds.has(u.id))
  const eligibleLoading = teachersApi.isLoading || extSupsApi.isLoading

  return (
    <Dialog open={open} onOpenChange={actionLoading ? undefined : onOpenChange}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>
            Manage Supervisors
            {teamCode && (
              <span className="ml-2 font-mono text-sm font-normal text-muted-foreground">
                {teamCode}
              </span>
            )}
          </DialogTitle>
        </DialogHeader>

        {teamLoading ? (
          <div className="space-y-2">
            <Skeleton className="h-10 w-full rounded-lg" />
            <Skeleton className="h-10 w-full rounded-lg" />
          </div>
        ) : teamError ? (
          <InlineError message={teamError} />
        ) : (
          <div className="space-y-5">
            <div className="space-y-2">
              <SectionLabel>Current Supervisors</SectionLabel>
              {(team?.active_supervisors.length ?? 0) === 0 ? (
                <p className="text-sm text-muted-foreground">No supervisors assigned yet.</p>
              ) : (
                <div className="divide-y divide-border rounded-lg border border-border">
                  {team?.active_supervisors.map(p => (
                    <div
                      key={p.participation_id}
                      className="flex items-center justify-between px-3 py-2"
                    >
                      <div>
                        <p className="text-sm font-medium">
                          {p.user.first_name} {p.user.last_name}
                        </p>
                        <p className="text-xs text-muted-foreground">{p.user.matricule}</p>
                      </div>
                      <Button
                        variant="ghost"
                        size="sm"
                        className="text-status-error-fg hover:text-status-error-fg"
                        disabled={actionLoading}
                        onClick={() => handleRemove(p.user.id)}
                      >
                        <UserMinus className="size-4" />
                        Remove
                      </Button>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="space-y-2">
              <SectionLabel>Add Supervisor</SectionLabel>
              {eligibleLoading ? (
                <Skeleton className="h-9 w-full rounded-md" />
              ) : availableToAdd.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  All eligible teachers and supervisors are already assigned.
                </p>
              ) : (
                <div className="flex gap-2">
                  <Select
                    value={selectedUserId}
                    onValueChange={setSelectedUserId}
                    disabled={actionLoading}
                  >
                    <SelectTrigger className="flex-1">
                      <SelectValue placeholder="Select teacher or supervisor…" />
                    </SelectTrigger>
                    <SelectContent>
                      {availableToAdd.map(u => (
                        <SelectItem key={u.id} value={String(u.id)}>
                          {u.first_name} {u.last_name} ({u.matricule})
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                  <Button
                    size="sm"
                    disabled={!selectedUserId || actionLoading}
                    onClick={handleAdd}
                  >
                    {actionLoading ? (
                      <Loader2 className="size-4 animate-spin" />
                    ) : (
                      <UserPlus className="size-4" />
                    )}
                    Add
                  </Button>
                </div>
              )}
            </div>

            {actionError && <InlineError message={actionError} />}
          </div>
        )}

        <DialogFooter>
          <Button variant="outline" onClick={() => onOpenChange(false)} disabled={actionLoading}>
            Done
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Manage members dialog ────────────────────────────────────────────────────
// Lets admin promote a non-leader to leader (transfer-leadership) and remove
// any non-leader member. To remove the current leader, admin must first promote
// someone else — keeps the destructive flow explicit and avoids ambiguity about
// which call to make to the backend.

function ManageMembersDialog({
  teamCode,
  open,
  onOpenChange,
  onSuccess,
}: {
  teamCode: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
  onSuccess: () => void
}) {
  const [team, setTeam] = useState<Team | null>(null)
  const [teamLoading, setTeamLoading] = useState(false)
  const [teamError, setTeamError] = useState<string | null>(null)
  const [busyParticipationId, setBusyParticipationId] = useState<string | null>(null)
  const [actionError, setActionError] = useState<string | null>(null)
  const [confirmRemove, setConfirmRemove] = useState<{
    studentId: number
    label: string
  } | null>(null)
  const [removeLoading, setRemoveLoading] = useState(false)
  const [removeError, setRemoveError] = useState<string | null>(null)

  async function loadTeam() {
    if (!teamCode) return
    setTeamLoading(true)
    setTeamError(null)
    try {
      const t = await api.get<Team>(`/api/admin/teams/${teamCode}/`)
      setTeam(t)
    } catch (err) {
      setTeamError(extractMessage(err))
    } finally {
      setTeamLoading(false)
    }
  }

  useEffect(() => {
    if (open && teamCode) {
      loadTeam()
      setActionError(null)
    } else {
      setTeam(null)
      setConfirmRemove(null)
      setRemoveError(null)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, teamCode])

  async function handlePromote(participationId: string, userId: number) {
    if (!teamCode) return
    setBusyParticipationId(participationId)
    setActionError(null)
    try {
      await api.post(`/api/admin/teams/${teamCode}/transfer-leadership/`, {
        new_leader_id: userId,
      })
      await loadTeam()
      onSuccess()
    } catch (err) {
      setActionError(extractMessage(err))
    } finally {
      setBusyParticipationId(null)
    }
  }

  async function handleRemove() {
    if (!teamCode || !confirmRemove) return
    setRemoveLoading(true)
    setRemoveError(null)
    try {
      await api.post(`/api/admin/teams/${teamCode}/remove-member/`, {
        student_id: confirmRemove.studentId,
        dissolve_if_needed: false,
      })
      setConfirmRemove(null)
      await loadTeam()
      onSuccess()
    } catch (err) {
      setRemoveError(extractMessage(err))
    } finally {
      setRemoveLoading(false)
    }
  }

  const members = team?.active_members ?? []
  const leaderParticipationId = team?.active_leader?.participation_id ?? null
  const anyBusy = busyParticipationId !== null

  return (
    <>
      <Dialog open={open} onOpenChange={anyBusy ? undefined : onOpenChange}>
        <DialogContent className="max-w-md">
          <DialogHeader>
            <DialogTitle>
              Manage Members
              {teamCode && (
                <span className="ml-2 font-mono text-sm font-normal text-muted-foreground">
                  {teamCode}
                </span>
              )}
            </DialogTitle>
          </DialogHeader>

          {teamLoading ? (
            <div className="space-y-2">
              <Skeleton className="h-12 w-full rounded-lg" />
              <Skeleton className="h-12 w-full rounded-lg" />
            </div>
          ) : teamError ? (
            <InlineError message={teamError} />
          ) : (
            <div className="space-y-3">
              <p className="text-xs text-muted-foreground">
                To remove the current leader, promote another member first.
              </p>

              {members.length === 0 ? (
                <p className="text-sm text-muted-foreground">No active members.</p>
              ) : (
                <div className="divide-y divide-border rounded-lg border border-border">
                  {members.map(p => {
                    const isLeader = p.participation_id === leaderParticipationId
                    const isBusy = busyParticipationId === p.participation_id
                    return (
                      <div
                        key={p.participation_id}
                        className="flex items-center justify-between gap-2 px-3 py-2"
                      >
                        <div className="min-w-0 flex-1">
                          <p className="truncate text-sm font-medium">
                            {p.user.first_name} {p.user.last_name}
                            {isLeader && (
                              <span className="ml-1.5 text-xs font-normal text-primary">
                                Leader
                              </span>
                            )}
                          </p>
                          <p className="truncate text-xs text-muted-foreground">
                            {p.user.matricule}
                          </p>
                        </div>
                        <div className="flex shrink-0 gap-1">
                          {!isLeader && (
                            <Button
                              variant="ghost"
                              size="sm"
                              disabled={anyBusy}
                              onClick={() => handlePromote(p.participation_id, p.user.id)}
                              title="Promote to team leader"
                            >
                              {isBusy ? (
                                <Loader2 className="size-4 animate-spin" />
                              ) : (
                                <Crown className="size-4" />
                              )}
                              Make Leader
                            </Button>
                          )}
                          {!isLeader && (
                            <Button
                              variant="ghost"
                              size="sm"
                              className="text-status-error-fg hover:text-status-error-fg"
                              disabled={anyBusy}
                              onClick={() => {
                                setRemoveError(null)
                                setConfirmRemove({
                                  studentId: p.user.id,
                                  label: `${p.user.first_name} ${p.user.last_name} (${p.user.matricule})`,
                                })
                              }}
                            >
                              <UserMinus className="size-4" />
                              Remove
                            </Button>
                          )}
                        </div>
                      </div>
                    )
                  })}
                </div>
              )}

              {actionError && <InlineError message={actionError} />}
            </div>
          )}

          <DialogFooter>
            <Button variant="outline" onClick={() => onOpenChange(false)} disabled={anyBusy}>
              Done
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>

      <ConfirmDialog
        open={confirmRemove !== null}
        onOpenChange={open => { if (!open) { setConfirmRemove(null); setRemoveError(null) } }}
        title="Remove Member"
        description={`Remove ${confirmRemove?.label ?? ''} from this team? The team will keep existing — use Dissolve Team if you want to disband the whole team.`}
        confirmLabel="Remove"
        destructive
        isLoading={removeLoading}
        error={removeError}
        onConfirm={handleRemove}
      />
    </>
  )
}

// ─── Row actions ──────────────────────────────────────────────────────────────

function TeamRowActions({
  team,
  onViewDetails,
  onManageMembers,
  onManageSupervisors,
  onDissolve,
}: {
  team: TeamListItem
  onViewDetails: (t: TeamListItem) => void
  onManageMembers: (t: TeamListItem) => void
  onManageSupervisors: (t: TeamListItem) => void
  onDissolve: (t: TeamListItem) => void
}) {
  const canDissolve = team.status !== 'DISSOLVED' && team.status !== 'ARCHIVED'

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon-sm" aria-label="Team actions">
          <MoreHorizontal className="size-4" />
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onSelect={() => onViewDetails(team)}>
          View Details
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => onManageMembers(team)}>
          Manage Members
        </DropdownMenuItem>
        <DropdownMenuItem onSelect={() => onManageSupervisors(team)}>
          Manage Supervisors
        </DropdownMenuItem>
        {canDissolve && (
          <>
            <DropdownMenuSeparator />
            <DropdownMenuItem
              onSelect={() => onDissolve(team)}
              className="text-status-error-fg focus:text-status-error-fg"
            >
              Dissolve Team
            </DropdownMenuItem>
          </>
        )}
      </DropdownMenuContent>
    </DropdownMenu>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function AdminTeamsView() {
  useAuth()

  // ── Filters ────────────────────────────────────────────────────────────────
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(10)
  const [search, setSearch] = useState('')
  const [appliedSearch, setAppliedSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [yearFilter, setYearFilter] = useState('all')

  useEffect(() => {
    const t = setTimeout(() => { setAppliedSearch(search); setPage(1) }, 400)
    return () => clearTimeout(t)
  }, [search])

  function applyFilter(setter: (v: string) => void) {
    return (v: string) => { setter(v); setPage(1) }
  }

  // ── Dialog state ───────────────────────────────────────────────────────────
  const [detailTeamCode, setDetailTeamCode] = useState<string | null>(null)
  const [membersTeamCode, setMembersTeamCode] = useState<string | null>(null)
  const [supervisorTeamCode, setSupervisorTeamCode] = useState<string | null>(null)
  const [dissolveTeam, setDissolveTeam] = useState<TeamListItem | null>(null)
  const [dissolveLoading, setDissolveLoading] = useState(false)
  const [dissolveError, setDissolveError] = useState<string | null>(null)

  // ── Data ───────────────────────────────────────────────────────────────────
  const yearsApi = useApi<PaginatedResponse<AcademicYear>>(
    () => api.get('/api/admin/academic-years/?page_size=100'),
    [],
  )

  const teamsApi = useApi<PaginatedResponse<TeamListItem>>(
    () => {
      const params = new URLSearchParams({ page: String(page), page_size: String(pageSize) })
      if (appliedSearch) params.set('search', appliedSearch)
      if (statusFilter !== 'all') params.set('status', statusFilter)
      if (yearFilter !== 'all') params.set('academic_year', yearFilter)
      return api.get(`/api/admin/teams/?${params}`)
    },
    [page, pageSize, appliedSearch, statusFilter, yearFilter],
  )

  // ── Actions ────────────────────────────────────────────────────────────────
  async function handleDissolve() {
    if (!dissolveTeam) return
    setDissolveLoading(true)
    setDissolveError(null)
    try {
      await api.post(`/api/admin/teams/${dissolveTeam.team_code}/dissolve/`, {})
      setDissolveTeam(null)
      teamsApi.refetch()
    } catch (err) {
      setDissolveError(extractMessage(err))
    } finally {
      setDissolveLoading(false)
    }
  }

  // ── Columns ────────────────────────────────────────────────────────────────
  const years = yearsApi.data?.results ?? []
  const total = teamsApi.data?.count ?? 0

  const columns: Column<TeamListItem>[] = [
    {
      key: 'team_code',
      header: 'Code',
      className: 'w-36',
      render: t => (
        <span className="font-mono text-xs font-semibold text-foreground">{t.team_code}</span>
      ),
    },
    {
      key: 'name',
      header: 'Team',
      render: t => <p className="font-medium text-foreground">{t.name}</p>,
    },
    {
      key: 'selection_round',
      header: 'Round',
      className: 'w-24',
      render: t => (
        <span className="text-sm text-muted-foreground">
          {ROUND_LABELS[t.selection_round] ?? t.selection_round}
        </span>
      ),
    },
    {
      key: 'annual_average',
      header: 'Average',
      className: 'w-24 tabular-nums',
      render: t => (
        <span className="text-sm">{t.annual_average ?? '—'}</span>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      className: 'w-32',
      render: t => <StatusBadge status={t.status} />,
    },
    {
      key: 'actions',
      header: '',
      className: 'w-12',
      render: t => (
        <TeamRowActions
          team={t}
          onViewDetails={item => setDetailTeamCode(item.team_code)}
          onManageMembers={item => setMembersTeamCode(item.team_code)}
          onManageSupervisors={item => setSupervisorTeamCode(item.team_code)}
          onDissolve={item => { setDissolveError(null); setDissolveTeam(item) }}
        />
      ),
    },
  ]

  // ── Render ─────────────────────────────────────────────────────────────────
  return (
    <>
      <PageHeader
        title="Teams"
        description="Manage teams, supervisors, and memberships."
      />

      {/* ── Filters ── */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <div className="relative min-w-56 flex-1">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by team name or code…"
            className="pl-8"
            value={search}
            onChange={e => setSearch(e.target.value)}
          />
        </div>
        <Select value={statusFilter} onValueChange={applyFilter(setStatusFilter)}>
          <SelectTrigger className="w-40">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {STATUS_OPTIONS.map(o => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={yearFilter} onValueChange={applyFilter(setYearFilter)}>
          <SelectTrigger className="w-52">
            <SelectValue placeholder="All years" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All years</SelectItem>
            {years.map(y => (
              <SelectItem key={y.id} value={String(y.id)}>
                {y.year_label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        {total > 0 && !teamsApi.isLoading && (
          <span className="ml-auto text-sm text-muted-foreground">
            {total} {total === 1 ? 'team' : 'teams'}
          </span>
        )}
      </div>

      {/* ── Table ── */}
      {teamsApi.error ? (
        <InlineError message={teamsApi.error} />
      ) : (
        <DataTable<TeamListItem>
          columns={columns}
          data={teamsApi.data?.results ?? []}
          keyField="team_code"
          isLoading={teamsApi.isLoading}
          page={page}
          pageSize={pageSize}
          total={total}
          onPageChange={setPage}
          onPageSizeChange={size => { setPageSize(size); setPage(1) }}
          emptyState={
            <EmptyState
              icon={Users}
              title="No teams found"
              description="Try adjusting your search or filters."
            />
          }
        />
      )}

      {/* ── Dialogs ── */}
      <TeamDetailDialog
        teamCode={detailTeamCode}
        open={detailTeamCode !== null}
        onOpenChange={open => { if (!open) setDetailTeamCode(null) }}
      />

      <ManageMembersDialog
        teamCode={membersTeamCode}
        open={membersTeamCode !== null}
        onOpenChange={open => { if (!open) setMembersTeamCode(null) }}
        onSuccess={teamsApi.refetch}
      />

      <ManageSupervisorsDialog
        teamCode={supervisorTeamCode}
        open={supervisorTeamCode !== null}
        onOpenChange={open => { if (!open) setSupervisorTeamCode(null) }}
        onSuccess={teamsApi.refetch}
      />

      <ConfirmDialog
        open={dissolveTeam !== null}
        onOpenChange={open => { if (!open) { setDissolveTeam(null); setDissolveError(null) } }}
        title="Dissolve Team"
        description={`Dissolve "${dissolveTeam?.name ?? ''}" (${dissolveTeam?.team_code ?? ''})? This cannot be undone — all members will lose their team membership.`}
        confirmLabel="Dissolve"
        destructive
        isLoading={dissolveLoading}
        error={dissolveError}
        onConfirm={handleDissolve}
      />
    </>
  )
}
