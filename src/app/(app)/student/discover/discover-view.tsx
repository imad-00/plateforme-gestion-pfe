'use client'

import { useEffect, useMemo, useState } from 'react'
import {
  AlertCircle,
  CheckCircle2,
  ChevronLeft,
  ChevronRight,
  FileText,
  Mail,
  Search,
  UserPlus,
  Users,
} from 'lucide-react'
import { api, ApiClientError } from '@/lib/api-client'
import { buildFileUrl } from '@/lib/config'
import { useApi } from '@/hooks/use-api'
import { useAuth } from '@/lib/auth-context'
import type {
  PaginatedResponse,
  StudentAvailability,
  StudentDirectoryDetail,
  StudentDirectoryItem,
  StudentSpecialitiesResponse,
  Team,
} from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

const PAGE_SIZE = 12
const SEARCH_DEBOUNCE_MS = 350

type AvailabilityFilter = 'all' | 'available' | 'in_team'

function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) {
    const data = err.data as Record<string, unknown>
    const flat = Object.values(data).flat().find(v => typeof v === 'string')
    return (flat as string | undefined) ?? err.message
  }
  return err instanceof Error ? err.message : 'An unexpected error occurred.'
}

function initials(first: string, last: string): string {
  const f = first?.trim()[0] ?? ''
  const l = last?.trim()[0] ?? ''
  return (f + l).toUpperCase() || '?'
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function DiscoverStudentsView() {
  useAuth()

  // Filters
  const [searchInput, setSearchInput] = useState('')
  const [search, setSearch] = useState('')
  const [speciality, setSpeciality] = useState<string>('')
  const [availability, setAvailability] = useState<AvailabilityFilter>('all')
  const [page, setPage] = useState(1)

  // Debounce search input → search query
  useEffect(() => {
    const t = setTimeout(() => {
      setSearch(searchInput.trim())
      setPage(1)
    }, SEARCH_DEBOUNCE_MS)
    return () => clearTimeout(t)
  }, [searchInput])

  // Reset page when filters change
  useEffect(() => {
    setPage(1)
  }, [speciality, availability])

  const listQuery = useMemo(() => {
    const params = new URLSearchParams()
    params.set('page', String(page))
    params.set('page_size', String(PAGE_SIZE))
    if (search) params.set('search', search)
    if (speciality) params.set('speciality', speciality)
    if (availability !== 'all') params.set('availability', availability)
    return params.toString()
  }, [page, search, speciality, availability])

  const studentsApi = useApi<PaginatedResponse<StudentDirectoryItem>>(
    () => api.get(`/api/students/?${listQuery}`),
    [listQuery],
  )

  const specialitiesApi = useApi<StudentSpecialitiesResponse>(
    () => api.get('/api/students/specialities/'),
    [],
  )

  // The student's own team — used to know whether we can invite, and to which
  // team_code to POST the invitation. Refetched after each successful invite
  // so the "Invite" button reflects the updated participation list.
  const teamApi = useApi<Team>(() => api.get('/api/teams/me/'), [])

  const [selectedId, setSelectedId] = useState<number | null>(null)

  const team = teamApi.data
  const { user } = useAuth()
  const isLeader = !!user && team?.active_leader?.user.id === user.id
  const canInvite = isLeader && team?.status === 'FORMING'

  const items = studentsApi.data?.results ?? []
  const total = studentsApi.data?.count ?? 0
  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  return (
    <>
      <PageHeader
        title="Discover students"
        description="Browse other students, check their profile, and invite them to your team."
      />

      <Filters
        searchInput={searchInput}
        onSearchChange={setSearchInput}
        speciality={speciality}
        onSpecialityChange={setSpeciality}
        availability={availability}
        onAvailabilityChange={setAvailability}
        specialities={specialitiesApi.data?.specialities ?? []}
        resultCount={total}
      />

      {studentsApi.isLoading ? (
        <LoadingGrid />
      ) : studentsApi.error ? (
        <InlineError message={studentsApi.error} />
      ) : items.length === 0 ? (
        <EmptyState />
      ) : (
        <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
          {items.map(item => (
            <StudentCard
              key={item.id}
              item={item}
              onOpen={() => setSelectedId(item.id)}
            />
          ))}
        </div>
      )}

      {!studentsApi.isLoading && !studentsApi.error && items.length > 0 && (
        <Pagination
          page={page}
          totalPages={totalPages}
          total={total}
          onChange={setPage}
        />
      )}

      <StudentDetailDialog
        studentId={selectedId}
        onClose={() => setSelectedId(null)}
        teamCode={team?.team_code ?? null}
        canInvite={!!canInvite}
        onInvited={() => {
          studentsApi.refetch()
          teamApi.refetch()
        }}
      />
    </>
  )
}

// ─── Filters ──────────────────────────────────────────────────────────────────

interface FiltersProps {
  searchInput: string
  onSearchChange: (value: string) => void
  speciality: string
  onSpecialityChange: (value: string) => void
  availability: AvailabilityFilter
  onAvailabilityChange: (value: AvailabilityFilter) => void
  specialities: string[]
  resultCount: number
}

function Filters({
  searchInput,
  onSearchChange,
  speciality,
  onSpecialityChange,
  availability,
  onAvailabilityChange,
  specialities,
  resultCount,
}: FiltersProps) {
  return (
    <Card>
      <CardContent className="space-y-3 pt-5">
        <div className="grid grid-cols-1 gap-3 md:grid-cols-[1fr_auto]">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search by name, matricule, email or skills…"
              value={searchInput}
              onChange={e => onSearchChange(e.target.value)}
              className="pl-9"
            />
          </div>
          <select
            value={speciality}
            onChange={e => onSpecialityChange(e.target.value)}
            className="h-9 rounded-md border border-input bg-background px-3 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
          >
            <option value="">All specialities</option>
            {specialities.map(s => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs font-medium text-muted-foreground">Availability:</span>
          {([
            { key: 'all', label: 'Everyone' },
            { key: 'available', label: 'Available' },
            { key: 'in_team', label: 'In a team' },
          ] as const).map(opt => (
            <button
              key={opt.key}
              type="button"
              onClick={() => onAvailabilityChange(opt.key)}
              className={[
                'rounded-full border px-2.5 py-0.5 text-xs font-medium transition-colors',
                availability === opt.key
                  ? 'border-primary bg-primary text-primary-foreground'
                  : 'border-border bg-background text-muted-foreground hover:text-foreground',
              ].join(' ')}
            >
              {opt.label}
            </button>
          ))}
          <span className="ml-auto text-xs text-muted-foreground tabular-nums">
            {resultCount} student{resultCount === 1 ? '' : 's'}
          </span>
        </div>
      </CardContent>
    </Card>
  )
}

// ─── Card ─────────────────────────────────────────────────────────────────────

function AvailabilityBadge({ value }: { value: StudentAvailability }) {
  const isAvailable = value === 'available'
  return (
    <Badge
      variant="outline"
      className={
        isAvailable
          ? 'border-status-success-border bg-status-success-bg text-status-success-fg'
          : 'border-status-warning-border bg-status-warning-bg text-status-warning-fg'
      }
    >
      {isAvailable ? 'Available' : 'In a team'}
    </Badge>
  )
}

function StudentCard({
  item,
  onOpen,
}: {
  item: StudentDirectoryItem
  onOpen: () => void
}) {
  const fullName = `${item.first_name} ${item.last_name}`.trim() || item.matricule
  const previewInterests = item.interests.slice(0, 3)
  const moreInterests = item.interests.length - previewInterests.length

  return (
    <Card
      className="group cursor-pointer transition-colors hover:border-primary/50"
      onClick={onOpen}
      role="button"
      tabIndex={0}
      onKeyDown={e => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onOpen()
        }
      }}
    >
      <CardContent className="space-y-3 pt-5">
        <div className="flex items-start gap-3">
          <div className="flex size-10 shrink-0 items-center justify-center rounded-full bg-muted text-sm font-semibold text-foreground">
            {initials(item.first_name, item.last_name)}
          </div>
          <div className="min-w-0 flex-1">
            <div className="truncate text-sm font-semibold text-foreground">
              {fullName}
            </div>
            <div className="truncate font-mono text-xs text-muted-foreground">
              {item.matricule}
            </div>
          </div>
          <AvailabilityBadge value={item.availability} />
        </div>

        {item.speciality && (
          <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <span className="font-medium text-foreground">{item.speciality}</span>
            {item.academic_year && (
              <>
                <span>·</span>
                <span>{item.academic_year}</span>
              </>
            )}
          </div>
        )}

        {item.bio && (
          <p className="line-clamp-2 text-xs text-muted-foreground">
            {item.bio}
          </p>
        )}

        {previewInterests.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {previewInterests.map(i => (
              <Badge key={i} variant="secondary" className="text-[10px]">{i}</Badge>
            ))}
            {moreInterests > 0 && (
              <span className="text-[10px] text-muted-foreground">
                +{moreInterests} more
              </span>
            )}
          </div>
        )}
      </CardContent>
    </Card>
  )
}

// ─── Detail dialog ────────────────────────────────────────────────────────────

function StudentDetailDialog({
  studentId,
  onClose,
  teamCode,
  canInvite,
  onInvited,
}: {
  studentId: number | null
  onClose: () => void
  teamCode: string | null
  canInvite: boolean
  onInvited: () => void
}) {
  const [detail, setDetail] = useState<StudentDirectoryDetail | null>(null)
  const [loading, setLoading] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [inviteLoading, setInviteLoading] = useState(false)
  const [inviteError, setInviteError] = useState<string | null>(null)
  const [inviteSuccess, setInviteSuccess] = useState(false)

  useEffect(() => {
    if (studentId == null) {
      setDetail(null)
      setLoadError(null)
      setInviteError(null)
      setInviteSuccess(false)
      return
    }
    let cancelled = false
    setLoading(true)
    setLoadError(null)
    setInviteError(null)
    setInviteSuccess(false)
    api
      .get<StudentDirectoryDetail>(`/api/students/${studentId}/`)
      .then(data => {
        if (!cancelled) setDetail(data)
      })
      .catch(err => {
        if (!cancelled) setLoadError(extractMessage(err))
      })
      .finally(() => {
        if (!cancelled) setLoading(false)
      })
    return () => {
      cancelled = true
    }
  }, [studentId])

  async function handleInvite() {
    if (!teamCode || !detail) return
    setInviteLoading(true)
    setInviteError(null)
    try {
      await api.post(`/api/teams/${teamCode}/invite/`, {
        student_id: detail.id,
      })
      setInviteSuccess(true)
      onInvited()
    } catch (err) {
      setInviteError(extractMessage(err))
    } finally {
      setInviteLoading(false)
    }
  }

  const open = studentId != null
  const cvUrl = detail?.cv_file_url ? buildFileUrl(detail.cv_file_url) : null
  const fullName = detail
    ? `${detail.first_name} ${detail.last_name}`.trim() || detail.matricule
    : ''
  const alreadyInTeam = detail?.availability === 'in_team'

  return (
    <Dialog open={open} onOpenChange={v => { if (!v) onClose() }}>
      <DialogContent className="max-w-2xl">
        <DialogHeader>
          <DialogTitle>Student profile</DialogTitle>
          <DialogDescription>
            Review the profile before sending a team invitation.
          </DialogDescription>
        </DialogHeader>

        {loading ? (
          <div className="space-y-3 py-4">
            <Skeleton className="h-12 w-12 rounded-full" />
            <Skeleton className="h-5 w-48" />
            <Skeleton className="h-4 w-32" />
            <Skeleton className="h-20 w-full" />
          </div>
        ) : loadError ? (
          <InlineError message={loadError} />
        ) : detail ? (
          <div className="space-y-4 py-2">
            <div className="flex items-start gap-3">
              <div className="flex size-12 shrink-0 items-center justify-center rounded-full bg-muted text-base font-semibold text-foreground">
                {initials(detail.first_name, detail.last_name)}
              </div>
              <div className="min-w-0 flex-1">
                <div className="text-base font-semibold text-foreground">
                  {fullName}
                </div>
                <div className="flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-muted-foreground">
                  <span className="font-mono">{detail.matricule}</span>
                  <span className="inline-flex items-center gap-1">
                    <Mail className="size-3" />
                    {detail.email}
                  </span>
                </div>
              </div>
              <AvailabilityBadge value={detail.availability} />
            </div>

            <dl className="grid grid-cols-1 gap-x-6 gap-y-2 text-sm sm:grid-cols-2">
              <div>
                <dt className="text-xs text-muted-foreground">Speciality</dt>
                <dd className="font-medium">{detail.speciality ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Academic year</dt>
                <dd className="font-medium">{detail.academic_year ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">Annual average</dt>
                <dd className="font-medium">{detail.annual_average ?? '—'}</dd>
              </div>
              <div>
                <dt className="text-xs text-muted-foreground">CV</dt>
                <dd>
                  {cvUrl ? (
                    <a
                      href={cvUrl}
                      target="_blank"
                      rel="noopener noreferrer"
                      className="inline-flex items-center gap-1 text-sm text-primary hover:underline"
                    >
                      <FileText className="size-3.5" />
                      View CV
                    </a>
                  ) : (
                    <span className="text-sm font-medium">—</span>
                  )}
                </dd>
              </div>
            </dl>

            {detail.bio && (
              <div>
                <div className="mb-1 text-xs text-muted-foreground">Bio</div>
                <p className="whitespace-pre-line text-sm">{detail.bio}</p>
              </div>
            )}

            {detail.skills_summary && (
              <div>
                <div className="mb-1 text-xs text-muted-foreground">Skills</div>
                <p className="whitespace-pre-line text-sm">{detail.skills_summary}</p>
              </div>
            )}

            {detail.interests.length > 0 && (
              <div>
                <div className="mb-1.5 text-xs text-muted-foreground">Interests</div>
                <div className="flex flex-wrap gap-1.5">
                  {detail.interests.map(i => (
                    <Badge key={i} variant="secondary">{i}</Badge>
                  ))}
                </div>
              </div>
            )}

            {inviteSuccess && (
              <div className="flex items-start gap-2 rounded-lg bg-status-success-bg p-3 text-sm text-status-success-fg">
                <CheckCircle2 className="mt-0.5 size-4 shrink-0" />
                <span>Invitation sent. The student will receive a notification.</span>
              </div>
            )}
            {inviteError && <InlineError message={inviteError} />}
          </div>
        ) : null}

        <DialogFooter>
          <Button type="button" variant="ghost" onClick={onClose}>
            Close
          </Button>
          {detail && !inviteSuccess && (
            <Button
              type="button"
              onClick={handleInvite}
              disabled={
                inviteLoading ||
                !canInvite ||
                !teamCode ||
                alreadyInTeam
              }
              title={
                !canInvite
                  ? 'Only the team leader of a forming team can invite.'
                  : alreadyInTeam
                    ? 'This student already belongs to another team.'
                    : undefined
              }
            >
              <UserPlus className="size-4" />
              {inviteLoading ? 'Sending…' : 'Invite to my team'}
            </Button>
          )}
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}

// ─── Misc ─────────────────────────────────────────────────────────────────────

function Pagination({
  page,
  totalPages,
  total,
  onChange,
}: {
  page: number
  totalPages: number
  total: number
  onChange: (page: number) => void
}) {
  return (
    <div className="mt-6 flex items-center justify-between text-sm">
      <span className="text-muted-foreground tabular-nums">
        Page {page} of {totalPages} · {total} student{total === 1 ? '' : 's'}
      </span>
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange(page - 1)}
          disabled={page <= 1}
        >
          <ChevronLeft className="size-4" />
          Previous
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => onChange(page + 1)}
          disabled={page >= totalPages}
        >
          Next
          <ChevronRight className="size-4" />
        </Button>
      </div>
    </div>
  )
}

function LoadingGrid() {
  return (
    <div className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {Array.from({ length: 8 }).map((_, i) => (
        <Skeleton key={i} className="h-40 w-full rounded-xl" />
      ))}
    </div>
  )
}

function EmptyState() {
  return (
    <Card className="mt-4">
      <CardContent className="flex flex-col items-center justify-center gap-2 py-12 text-center">
        <Users className="size-8 text-muted-foreground" />
        <p className="text-sm font-medium">No students match your filters.</p>
        <p className="text-xs text-muted-foreground">
          Try clearing the search or switching the availability filter.
        </p>
      </CardContent>
    </Card>
  )
}

function InlineError({ message }: { message: string }) {
  return (
    <div className="mt-4 flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}
