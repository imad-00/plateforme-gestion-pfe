'use client'

import Link from 'next/link'
import { AlertCircle, CalendarClock, Eye, Gavel, MapPin } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type { DefenseListItem, PaginatedResponse } from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { EmptyState } from '@/components/shared/empty-state'
import { StatusBadge } from '@/components/shared/status-badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

export function JuryDefensesView() {
  useAuth()
  const listApi = useApi<PaginatedResponse<DefenseListItem>>(
    () => api.get('/api/jury/defenses/'),
    [],
  )

  const items = listApi.data?.results ?? []

  return (
    <>
      <PageHeader
        title="Jury defenses"
        description="Defenses where you have been assigned to the jury. Only scheduled and completed defenses appear here."
      />

      {listApi.error && <div className="mb-4"><InlineError message={listApi.error} /></div>}

      {listApi.isLoading ? (
        <div className="space-y-3">
          <Skeleton className="h-28 w-full rounded-xl" />
          <Skeleton className="h-28 w-full rounded-xl" />
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={Gavel}
          title="No defenses to review yet"
          description="Defenses you have been assigned to as jury will appear here once they are scheduled."
        />
      ) : (
        <div className="space-y-3">
          {items.map(d => (
            <Card key={d.id}>
              <CardContent className="flex flex-wrap items-center justify-between gap-4 pt-5">
                <div className="min-w-0 space-y-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-foreground">{d.team.name}</p>
                    <span className="text-xs text-muted-foreground">{d.team.team_code}</span>
                    <StatusBadge status={d.status} />
                  </div>
                  <div className="flex flex-wrap items-center gap-x-4 gap-y-1 text-sm text-muted-foreground">
                    <span className="inline-flex items-center gap-1.5">
                      <CalendarClock className="size-3.5" />
                      {formatDateTime(d.scheduled_at)}
                    </span>
                    {d.location && (
                      <span className="inline-flex items-center gap-1.5">
                        <MapPin className="size-3.5" />
                        {d.location}
                      </span>
                    )}
                  </div>
                </div>
                <Link href={`/jury/defenses/${d.id}`}>
                  <Button variant="outline" size="sm">
                    <Eye className="size-3.5" />
                    View
                  </Button>
                </Link>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </>
  )
}
