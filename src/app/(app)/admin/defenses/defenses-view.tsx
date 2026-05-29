'use client'

import { useState } from 'react'
import Link from 'next/link'
import { AlertCircle, CalendarClock, Eye, Landmark } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type {
  AcademicYear,
  DefenseListItem,
  DefenseStatus,
  PaginatedResponse,
} from '@/lib/types'
import { DataTable, type Column } from '@/components/shared/data-table'
import { EmptyState } from '@/components/shared/empty-state'
import { StatusBadge } from '@/components/shared/status-badge'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

// ─── Constants ────────────────────────────────────────────────────────────────

const STATUS_OPTIONS: Array<{ value: 'all' | DefenseStatus; label: string }> = [
  { value: 'all', label: 'All statuses' },
  { value: 'REQUESTED', label: 'Requested' },
  { value: 'READY_TO_SCHEDULE', label: 'Ready to schedule' },
  { value: 'SCHEDULED', label: 'Scheduled' },
  { value: 'COMPLETED', label: 'Completed' },
  { value: 'CANCELLED', label: 'Cancelled' },
  { value: 'ARCHIVED', label: 'Archived' },
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

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

// ─── View ─────────────────────────────────────────────────────────────────────

export function AdminDefensesView() {
  useAuth()

  const [statusFilter, setStatusFilter] = useState<'all' | DefenseStatus>('all')
  const [yearFilter, setYearFilter] = useState<string>('all')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)

  const yearsApi = useApi<PaginatedResponse<AcademicYear>>(
    () => api.get('/api/admin/academic-years/?page_size=100'),
    [],
  )

  const defensesApi = useApi<PaginatedResponse<DefenseListItem>>(() => {
    const params = new URLSearchParams({
      page: String(page),
      page_size: String(pageSize),
    })
    if (statusFilter !== 'all') params.set('status', statusFilter)
    if (yearFilter !== 'all') params.set('academic_year', yearFilter)
    return api.get(`/api/admin/defenses/?${params}`)
  }, [page, pageSize, statusFilter, yearFilter])

  const columns: Column<DefenseListItem>[] = [
    {
      key: 'team',
      header: 'Team',
      render: row => (
        <div>
          <p className="font-medium text-foreground">{row.team.name}</p>
          <p className="text-xs text-muted-foreground">{row.team.team_code}</p>
        </div>
      ),
    },
    {
      key: 'status',
      header: 'Status',
      render: row => <StatusBadge status={row.status} />,
    },
    {
      key: 'requested_at',
      header: 'Requested',
      render: row => (
        <span className="text-sm text-foreground">{formatDateTime(row.requested_at)}</span>
      ),
    },
    {
      key: 'scheduled_at',
      header: 'Scheduled',
      render: row =>
        row.scheduled_at ? (
          <div className="flex items-center gap-1.5 text-sm text-foreground">
            <CalendarClock className="size-3.5 text-muted-foreground" />
            {formatDateTime(row.scheduled_at)}
          </div>
        ) : (
          <span className="text-sm text-muted-foreground">—</span>
        ),
    },
    {
      key: 'location',
      header: 'Location',
      render: row => (
        <span className="text-sm text-foreground">{row.location || '—'}</span>
      ),
    },
    {
      key: 'actions',
      header: '',
      className: 'w-24 text-right',
      render: row => (
        <Link href={`/admin/defenses/${row.id}`}>
          <Button variant="ghost" size="sm">
            <Eye className="size-3.5" />
            View
          </Button>
        </Link>
      ),
    },
  ]

  const data = defensesApi.data?.results ?? []
  const total = defensesApi.data?.count ?? 0

  return (
    <>
      <PageHeader
        title="Defenses"
        description="All defense workflows across the platform — schedule, jury, files, and PVs."
      />

      {/* Filters */}
      <div className="mb-4 flex flex-wrap items-center gap-3">
        <Select
          value={statusFilter}
          onValueChange={v => {
            setStatusFilter(v as 'all' | DefenseStatus)
            setPage(1)
          }}
        >
          <SelectTrigger className="w-52">
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

        <Select
          value={yearFilter}
          onValueChange={v => {
            setYearFilter(v)
            setPage(1)
          }}
        >
          <SelectTrigger className="w-52">
            <SelectValue placeholder="Academic year" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All years</SelectItem>
            {(yearsApi.data?.results ?? []).map(y => (
              <SelectItem key={y.id} value={String(y.id)}>
                {y.year_label || y.year}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {defensesApi.error && (
        <div className="mb-4">
          <InlineError message={defensesApi.error} />
        </div>
      )}

      <DataTable<DefenseListItem>
        columns={columns}
        data={data}
        keyField="id"
        isLoading={defensesApi.isLoading}
        page={page}
        pageSize={pageSize}
        total={total}
        onPageChange={setPage}
        onPageSizeChange={s => {
          setPageSize(s)
          setPage(1)
        }}
        emptyState={
          <EmptyState
            icon={Landmark}
            title="No defenses match these filters"
            description="Adjust the status or year filter to see other defenses."
          />
        }
      />
    </>
  )
}
