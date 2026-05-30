'use client'

import Link from 'next/link'
import { CheckCircle2, Clock, ListChecks } from 'lucide-react'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type { Wishlist } from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { StatusBadge } from '@/components/shared/status-badge'
import { EmptyState } from '@/components/shared/empty-state'
import { Skeleton } from '@/components/ui/skeleton'

function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) {
    const d = err.data as Record<string, unknown>
    const first = Object.values(d).flat().find(v => typeof v === 'string')
    return (first as string | undefined) ?? err.message
  }
  return err instanceof Error ? err.message : 'An unexpected error occurred.'
}

function formatDate(iso: string | null) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString(undefined, {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export function WishlistView() {
  const { data, isLoading, error } = useApi<Wishlist[]>(
    () => api.get('/api/wishlists/me/'),
    [],
  )

  return (
    <div className="space-y-6">
      <PageHeader
        title="My wishlists"
        description="Review every wishlist your team has submitted, round by round."
      />

      {isLoading && (
        <div className="space-y-4">
          <Skeleton className="h-32 w-full rounded-xl" />
          <Skeleton className="h-32 w-full rounded-xl" />
        </div>
      )}

      {error && <p className="text-sm text-status-error-fg">{extractMessage(error)}</p>}

      {data && data.length === 0 && (
        <EmptyState
          icon={ListChecks}
          title="No wishlist yet"
          description="Once your team submits a wishlist, it will appear here."
          action={
            <Link
              href="/student/subjects"
              className="text-sm font-medium text-primary hover:underline"
            >
              Browse the subjects catalog →
            </Link>
          }
        />
      )}

      {data?.map(wishlist => (
        <Card key={wishlist.wishlist_id}>
          <CardHeader className="space-y-2">
            <div className="flex flex-wrap items-center justify-between gap-2">
              <CardTitle className="text-base">
                {wishlist.selection_round === 'SECOND' ? 'Round 2' : 'Round 1'}
                <span className="ml-2 text-sm font-normal text-muted-foreground">
                  {wishlist.items.length} subject{wishlist.items.length === 1 ? '' : 's'}
                </span>
              </CardTitle>
              <StatusBadge status={wishlist.status} />
            </div>
            <div className="flex flex-wrap gap-x-4 gap-y-1 text-xs text-muted-foreground">
              <span className="inline-flex items-center gap-1">
                {wishlist.status === 'SUBMITTED' ? (
                  <CheckCircle2 className="size-3.5 text-status-success-fg" />
                ) : (
                  <Clock className="size-3.5" />
                )}
                Submitted: {formatDate(wishlist.submitted_at)}
              </span>
              <span>Last update: {formatDate(wishlist.updated_at)}</span>
              <span>Team: {wishlist.team.name}</span>
            </div>
          </CardHeader>
          <CardContent>
            {wishlist.items.length === 0 ? (
              <p className="text-sm text-muted-foreground">No subjects on this wishlist.</p>
            ) : (
              <ol className="space-y-2">
                {[...wishlist.items]
                  .sort((a, b) => a.rank - b.rank)
                  .map(item => (
                    <li
                      key={item.wishitem_id}
                      className="flex items-start gap-3 rounded-lg border border-border bg-muted/20 p-3"
                    >
                      <span className="flex size-7 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">
                        {item.rank}
                      </span>
                      <div className="min-w-0 flex-1">
                        <div className="flex flex-wrap items-center gap-2">
                          <Link
                            href={`/student/subjects/${item.subject.id}`}
                            className="text-sm font-medium text-foreground hover:text-primary hover:underline"
                          >
                            {item.subject.title}
                          </Link>
                          {item.subject.subject_code && (
                            <span className="font-mono text-xs text-muted-foreground">
                              {item.subject.subject_code}
                            </span>
                          )}
                          <Badge variant="outline" className="text-xs">
                            {item.subject.subject_type.replace('_', ' ').toLowerCase()}
                          </Badge>
                        </div>
                        <p className="mt-1 line-clamp-2 text-xs text-muted-foreground">
                          {item.subject.description}
                        </p>
                        <p className="mt-1 text-xs text-muted-foreground">
                          By {item.subject.proposed_by.first_name}{' '}
                          {item.subject.proposed_by.last_name}
                        </p>
                      </div>
                    </li>
                  ))}
              </ol>
            )}
          </CardContent>
        </Card>
      ))}
    </div>
  )
}
