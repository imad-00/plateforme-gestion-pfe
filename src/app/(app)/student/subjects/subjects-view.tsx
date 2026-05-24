'use client'

import { useEffect, useRef, useState } from 'react'
import {
  BookOpen,
  ChevronDown,
  ChevronUp,
  Loader2,
  Paperclip,
  Plus,
  Search,
  X,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type {
  CampaignStatus,
  PaginatedResponse,
  PublicSubject,
  SubjectType,
  Team,
  Wishlist,
} from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { EmptyState } from '@/components/shared/empty-state'
import { StatusBadge } from '@/components/shared/status-badge'
import { Button } from '@/components/ui/button'
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { Separator } from '@/components/ui/separator'
import { Skeleton } from '@/components/ui/skeleton'

// ─── Subject type badge ───────────────────────────────────────────────────────

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

// ─── Subject card ─────────────────────────────────────────────────────────────

function SubjectCard({
  subject,
  inDraft,
  canAdd,
  onAdd,
}: {
  subject: PublicSubject
  inDraft: boolean
  canAdd: boolean
  onAdd: () => void
}) {
  return (
    <Card>
      <CardHeader className="gap-2 pb-2">
        <div className="flex items-start gap-3">
          <div className="min-w-0 flex-1 space-y-1.5">
            <div className="flex flex-wrap items-center gap-1.5">
              {subject.subject_code && (
                <span className="font-mono text-xs text-muted-foreground">
                  {subject.subject_code}
                </span>
              )}
              <TypeBadge type={subject.subject_type} />
            </div>
            <CardTitle className="text-sm leading-snug">{subject.title}</CardTitle>
          </div>

          {canAdd && (
            <Button
              size="sm"
              variant={inDraft ? 'secondary' : 'outline'}
              className="shrink-0 gap-1"
              disabled={inDraft}
              onClick={onAdd}
            >
              {inDraft ? (
                'Added'
              ) : (
                <>
                  <Plus className="size-3.5" />
                  Add
                </>
              )}
            </Button>
          )}
        </div>
      </CardHeader>

      <CardContent className="space-y-2.5 pt-0">
        <p className="line-clamp-3 text-sm text-muted-foreground">{subject.description}</p>

        <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground">
          <span>
            By{' '}
            <span className="font-medium text-foreground">
              {subject.proposed_by.first_name} {subject.proposed_by.last_name}
            </span>
          </span>
          {subject.attachment_url && (
            <a
              href={subject.attachment_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1 text-primary hover:underline"
            >
              <Paperclip className="size-3" />
              Attachment
            </a>
          )}
        </div>
      </CardContent>
    </Card>
  )
}

// ─── Wishlist row ─────────────────────────────────────────────────────────────

function WishlistRow({
  rank,
  subject,
  canEdit,
  isFirst,
  isLast,
  onMoveUp,
  onMoveDown,
  onRemove,
}: {
  rank: number
  subject: PublicSubject
  canEdit: boolean
  isFirst: boolean
  isLast: boolean
  onMoveUp: () => void
  onMoveDown: () => void
  onRemove: () => void
}) {
  return (
    <li className="flex items-center gap-2 rounded-lg border border-border bg-muted/20 p-2.5">
      <span className="flex size-5 shrink-0 items-center justify-center rounded-full bg-primary/10 text-xs font-semibold text-primary">
        {rank}
      </span>

      <div className="min-w-0 flex-1">
        <p className="truncate text-xs font-medium leading-snug">{subject.title}</p>
        <p className="text-xs text-muted-foreground">
          {TYPE_CONFIG[subject.subject_type].label}
        </p>
      </div>

      {canEdit && (
        <div className="flex shrink-0 items-center">
          <Button
            variant="ghost"
            size="icon-sm"
            className="size-6 text-muted-foreground"
            disabled={isFirst}
            onClick={onMoveUp}
            aria-label="Move up"
          >
            <ChevronUp className="size-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            className="size-6 text-muted-foreground"
            disabled={isLast}
            onClick={onMoveDown}
            aria-label="Move down"
          >
            <ChevronDown className="size-3.5" />
          </Button>
          <Button
            variant="ghost"
            size="icon-sm"
            className="size-6 text-muted-foreground hover:text-status-error-fg"
            onClick={onRemove}
            aria-label="Remove"
          >
            <X className="size-3.5" />
          </Button>
        </div>
      )}
    </li>
  )
}

// ─── Catalog skeleton ─────────────────────────────────────────────────────────

function CatalogSkeleton() {
  return (
    <div className="space-y-3">
      {Array.from({ length: 4 }).map((_, i) => (
        <Skeleton key={i} className="h-36 w-full rounded-xl" />
      ))}
    </div>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function SubjectsView() {
  const { user } = useAuth()

  const teamApi = useApi<Team>(() => api.get('/api/teams/me/'), [])
  const campaignApi = useApi<CampaignStatus>(() => api.get('/api/campaign/current/'), [])
  const subjectsApi = useApi<PaginatedResponse<PublicSubject>>(
    () => api.get('/api/subjects/?page_size=100'),
    [],
  )
  const wishlistsApi = useApi<Wishlist[]>(() => api.get('/api/wishlists/me/'), [])

  const [draft, setDraft] = useState<PublicSubject[]>([])
  const [search, setSearch] = useState('')
  const [typeFilter, setTypeFilter] = useState<SubjectType | 'ALL'>('ALL')
  const [submitLoading, setSubmitLoading] = useState(false)
  const [submitError, setSubmitError] = useState<string | null>(null)
  const [submitSuccess, setSubmitSuccess] = useState(false)

  // Initialize the draft once from the most recent wishlist for the current round
  const draftInitialized = useRef(false)
  useEffect(() => {
    if (!teamApi.data || !wishlistsApi.data || draftInitialized.current) return
    const latest = wishlistsApi.data
      .filter((w) => w.selection_round === teamApi.data!.selection_round)
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0]
    if (latest?.items?.length) {
      setDraft([...latest.items].sort((a, b) => a.rank - b.rank).map((i) => i.subject))
    }
    draftInitialized.current = true
  }, [teamApi.data, wishlistsApi.data])

  const team = teamApi.data
  const campaign = campaignApi.data
  const subjects = subjectsApi.data?.results ?? []

  const isLeader = !!user && team?.active_leader?.user.id === user.id
  const canSubmit = isLeader && !!campaign?.actions.can_submit_first_wishlist

  const draftIds = new Set(draft.map((s) => s.id))

  const filtered = subjects.filter(
    (s) =>
      (typeFilter === 'ALL' || s.subject_type === typeFilter) &&
      (!search ||
        s.title.toLowerCase().includes(search.toLowerCase()) ||
        (s.subject_code ?? '').toLowerCase().includes(search.toLowerCase())),
  )

  // ── Draft mutation helpers ─────────────────────────────────────────────────

  function addToDraft(subject: PublicSubject) {
    if (draftIds.has(subject.id)) return
    setDraft((prev) => [...prev, subject])
  }

  function removeFromDraft(subjectId: number) {
    setDraft((prev) => prev.filter((s) => s.id !== subjectId))
  }

  function moveUp(index: number) {
    if (index <= 0) return
    setDraft((prev) => {
      const next = [...prev]
      ;[next[index - 1], next[index]] = [next[index], next[index - 1]]
      return next
    })
  }

  function moveDown(index: number) {
    setDraft((prev) => {
      if (index >= prev.length - 1) return prev
      const next = [...prev]
      ;[next[index], next[index + 1]] = [next[index + 1], next[index]]
      return next
    })
  }

  // ── Submit ─────────────────────────────────────────────────────────────────

  async function handleSubmit() {
    if (!team || draft.length === 0) return
    setSubmitLoading(true)
    setSubmitError(null)
    setSubmitSuccess(false)
    try {
      await api.post('/api/wishlists/', {
        selection_round: team.selection_round,
        items: draft.map((s, i) => ({ subject_id: s.id, rank: i + 1 })),
      })
      setSubmitSuccess(true)
      wishlistsApi.refetch()
      setTimeout(() => setSubmitSuccess(false), 5000)
    } catch (err) {
      if (err instanceof ApiClientError) {
        const msgs = Object.values(err.data)
          .flat()
          .filter((v): v is string => typeof v === 'string')
        setSubmitError(msgs[0] ?? err.message)
      } else {
        setSubmitError(err instanceof Error ? err.message : 'Submission failed.')
      }
    } finally {
      setSubmitLoading(false)
    }
  }

  // Most recent wishlist submission for this round (to show status)
  const lastSubmission = (wishlistsApi.data ?? [])
    .filter((w) => w.selection_round === team?.selection_round)
    .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime())[0]

  const isLoadingInitial = teamApi.isLoading || subjectsApi.isLoading

  return (
    <>
      <PageHeader
        title="Subjects"
        description="Browse the catalog and build your team wishlist."
      />

      <div className="flex flex-col gap-6 lg:flex-row lg:items-start">
        {/* ── Catalog ── */}
        <div className="min-w-0 flex-1">
          {/* Search + type filter */}
          <div className="mb-4 flex flex-col gap-2 sm:flex-row">
            <div className="relative flex-1">
              <Search className="pointer-events-none absolute left-2.5 top-1/2 size-3.5 -translate-y-1/2 text-muted-foreground" />
              <Input
                placeholder="Search by title or code…"
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-8"
              />
            </div>
            <Select
              value={typeFilter}
              onValueChange={(v) => setTypeFilter(v as SubjectType | 'ALL')}
            >
              <SelectTrigger className="w-full sm:w-44">
                <SelectValue placeholder="All types" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="ALL">All types</SelectItem>
                <SelectItem value="RESEARCH_PROJECT">Research</SelectItem>
                <SelectItem value="APPLIED_PROJECT">Applied</SelectItem>
                <SelectItem value="STARTUP_PROJECT">Startup</SelectItem>
              </SelectContent>
            </Select>
          </div>

          {/* Result count */}
          {!isLoadingInitial && subjects.length > 0 && (
            <p className="mb-3 text-xs text-muted-foreground">
              {filtered.length} subject{filtered.length !== 1 ? 's' : ''}
              {(search || typeFilter !== 'ALL') && ' matching filters'}
            </p>
          )}

          {/* Subject list */}
          {isLoadingInitial ? (
            <CatalogSkeleton />
          ) : subjectsApi.error ? (
            <EmptyState
              title="Failed to load subjects"
              description={subjectsApi.error}
              action={
                <Button variant="outline" size="sm" onClick={subjectsApi.refetch}>
                  Retry
                </Button>
              }
            />
          ) : filtered.length === 0 ? (
            <EmptyState
              icon={BookOpen}
              title={
                search || typeFilter !== 'ALL'
                  ? 'No subjects match your filters'
                  : 'No subjects available'
              }
              description={
                search || typeFilter !== 'ALL'
                  ? 'Try adjusting your search or filter.'
                  : 'No approved subjects have been published yet.'
              }
              action={
                search || typeFilter !== 'ALL' ? (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      setSearch('')
                      setTypeFilter('ALL')
                    }}
                  >
                    Clear filters
                  </Button>
                ) : undefined
              }
            />
          ) : (
            <div className="space-y-3">
              {filtered.map((subject) => (
                <SubjectCard
                  key={subject.id}
                  subject={subject}
                  inDraft={draftIds.has(subject.id)}
                  canAdd={isLeader}
                  onAdd={() => addToDraft(subject)}
                />
              ))}
            </div>
          )}
        </div>

        {/* ── Wishlist panel ── */}
        <div className="w-full shrink-0 lg:sticky lg:top-6 lg:w-80">
          <div className="overflow-hidden rounded-xl border border-border bg-card shadow-card">
            {/* Header */}
            <div className="border-b border-border px-4 py-3">
              <p className="text-sm font-semibold">My Wishlist</p>
              <p className="text-xs text-muted-foreground">
                {team?.selection_round === 'SECOND' ? 'Round 2' : 'Round 1'}
                {' · '}
                {draft.length} {draft.length === 1 ? 'subject' : 'subjects'}
              </p>
            </div>

            {/* Member read-only notice */}
            {!isLeader && team && (
              <div className="border-b border-border bg-muted/30 px-4 py-2">
                <p className="text-xs text-muted-foreground">
                  Only the team leader can edit the wishlist.
                </p>
              </div>
            )}

            {/* Draft items */}
            <div className="px-4 py-3">
              {draft.length === 0 ? (
                <p className="py-4 text-center text-xs text-muted-foreground">
                  {isLeader
                    ? 'Click "Add" on a subject to include it here.'
                    : 'No subjects in the wishlist yet.'}
                </p>
              ) : (
                <ol className="space-y-1.5">
                  {draft.map((subject, i) => (
                    <WishlistRow
                      key={subject.id}
                      rank={i + 1}
                      subject={subject}
                      canEdit={isLeader}
                      isFirst={i === 0}
                      isLast={i === draft.length - 1}
                      onMoveUp={() => moveUp(i)}
                      onMoveDown={() => moveDown(i)}
                      onRemove={() => removeFromDraft(subject.id)}
                    />
                  ))}
                </ol>
              )}
            </div>

            {/* Submit section — leader only */}
            {isLeader && (
              <>
                <Separator />
                <div className="space-y-2 px-4 py-3">
                  {submitSuccess && (
                    <p className="text-xs font-medium text-status-success-fg">
                      Wishlist submitted successfully.
                    </p>
                  )}
                  {submitError && (
                    <p className="text-xs text-status-error-fg">{submitError}</p>
                  )}
                  {!campaign?.actions.can_submit_first_wishlist && (
                    <p className="text-xs text-muted-foreground">
                      Wishlist submission is not open right now.
                    </p>
                  )}
                  <Button
                    className="w-full"
                    disabled={!canSubmit || submitLoading || draft.length === 0}
                    onClick={handleSubmit}
                  >
                    {submitLoading && <Loader2 className="size-4 animate-spin" />}
                    Submit Wishlist
                  </Button>
                </div>
              </>
            )}

            {/* Last submission status */}
            {lastSubmission && (
              <>
                <Separator />
                <div className="flex items-center justify-between px-4 py-3">
                  <div>
                    <p className="text-xs font-medium text-foreground">Last submitted</p>
                    <p className="text-xs text-muted-foreground">
                      {new Date(lastSubmission.submitted_at ?? lastSubmission.created_at).toLocaleDateString('en-GB', {
                        day: 'numeric',
                        month: 'short',
                        year: 'numeric',
                      })}
                    </p>
                  </div>
                  <StatusBadge status={lastSubmission.status} />
                </div>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  )
}
