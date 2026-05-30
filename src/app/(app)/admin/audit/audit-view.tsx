'use client'

import { useMemo, useState } from 'react'
import { AlertCircle, ChevronDown, ChevronRight, ScrollText } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type {
  AuditActionType,
  AuditLogEntry,
  PaginatedResponse,
} from '@/lib/types'
import { DataTable, type Column } from '@/components/shared/data-table'
import { EmptyState } from '@/components/shared/empty-state'
import { PageHeader } from '@/components/layout/page-header'
import { UserPicker, type PickerUser } from '@/components/shared/user-picker'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

// ─── Filter option lists ──────────────────────────────────────────────────────

const ACTION_TYPES: AuditActionType[] = [
  'USER_IMPORT_PREVIEWED',
  'USER_IMPORT_COMPLETED',
  'USER_CREATED_BY_IMPORT',
  'ACADEMIC_YEAR_CLOSED',
  'ACADEMIC_YEAR_FORCE_CLOSED',
  'ACADEMIC_YEAR_REOPENED',
  'ACADEMIC_YEAR_ARCHIVED',
  'USER_CREATED',
  'USER_UPDATED',
  'USER_ARCHIVED',
  'PLATFORM_GRANT_CREATED',
  'PLATFORM_GRANT_REVOKED',
  'TEAM_ADMIN_MODIFIED',
  'TEAM_DISSOLVED',
  'SUBJECT_APPROVED',
  'SUBJECT_REJECTED',
  'ASSIGNMENT_RUN_BY_ADMIN',
  'APPEAL_REVIEWED',
  'DEFENSE_SCHEDULED',
  'DEFENSE_RESCHEDULED',
  'DEFENSE_JURY_UPDATED',
  'DEFENSE_PV_UPLOADED',
]

// Observed target_model strings the backend emits. Not exhaustive — the audit
// service accepts free-form filter values, so users can also leave this blank
// to see every model. Add to this list as new admin hooks land.
const TARGET_MODELS = [
  'accounts.User',
  'academics.AcademicYear',
  'teams.Team',
  'topics.Subject',
  'assignments.Appeal',
  'defenses.Defense',
  'imports.UserImportBatch',
]

// ─── Helpers ──────────────────────────────────────────────────────────────────

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

function humanizeActionType(value: string): string {
  return value
    .split('_')
    .map(w => w.charAt(0) + w.slice(1).toLowerCase())
    .join(' ')
}

function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

// ─── Expandable row body (metadata + UA + IP) ─────────────────────────────────

function ExpandedRowDetails({ entry }: { entry: AuditLogEntry }) {
  return (
    <div className="space-y-2 rounded-lg border border-border bg-muted/30 p-3 text-xs">
      <div className="grid gap-2 sm:grid-cols-2">
        <div>
          <p className="font-medium text-muted-foreground">IP address</p>
          <p className="text-foreground">{entry.ip_address || '—'}</p>
        </div>
        <div>
          <p className="font-medium text-muted-foreground">User agent</p>
          <p className="break-words text-foreground">{entry.user_agent || '—'}</p>
        </div>
      </div>
      <div>
        <p className="font-medium text-muted-foreground">Metadata</p>
        <pre className="overflow-x-auto rounded bg-card p-2 font-mono text-[11px] text-foreground">
          {JSON.stringify(entry.metadata ?? {}, null, 2)}
        </pre>
      </div>
    </div>
  )
}

// ─── View ─────────────────────────────────────────────────────────────────────

export function AuditView() {
  useAuth()

  // Filter state
  const [actionType, setActionType] = useState<'all' | AuditActionType>('all')
  const [targetModel, setTargetModel] = useState<string>('all')
  const [actor, setActor] = useState<PickerUser[]>([])
  const [dateFrom, setDateFrom] = useState('')
  const [dateTo, setDateTo] = useState('')
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)
  const [expanded, setExpanded] = useState<number | null>(null)

  // Filter setters that also reset page to 1 — keeps "filter changed" and
  // "page reset" atomic without bouncing through useEffect.
  function withPageReset<T>(setter: (v: T) => void): (v: T) => void {
    return v => {
      setter(v)
      setPage(1)
    }
  }

  const actorId = actor[0]?.id ?? null

  const logsApi = useApi<PaginatedResponse<AuditLogEntry>>(
    () => {
      const params = new URLSearchParams({
        page: String(page),
        page_size: String(pageSize),
      })
      if (actionType !== 'all') params.set('action_type', actionType)
      if (targetModel !== 'all') params.set('target_model', targetModel)
      if (actorId !== null) params.set('actor_id', String(actorId))
      if (dateFrom) params.set('date_from', new Date(dateFrom).toISOString())
      if (dateTo) params.set('date_to', new Date(dateTo).toISOString())
      return api.get(`/api/super-admin/audit/admin-actions/?${params}`)
    },
    [page, pageSize, actionType, targetModel, actorId, dateFrom, dateTo],
  )

  const data = logsApi.data?.results ?? []
  const total = logsApi.data?.count ?? 0

  const columns = useMemo<Column<AuditLogEntry>[]>(
    () => [
      {
        key: 'expand',
        header: '',
        className: 'w-8',
        render: row => (
          <button
            type="button"
            onClick={() => setExpanded(prev => (prev === row.id ? null : row.id))}
            className="rounded p-1 text-muted-foreground hover:bg-muted hover:text-foreground"
            aria-label={expanded === row.id ? 'Collapse details' : 'Expand details'}
          >
            {expanded === row.id ? (
              <ChevronDown className="size-3.5" />
            ) : (
              <ChevronRight className="size-3.5" />
            )}
          </button>
        ),
      },
      {
        key: 'occurred_at',
        header: 'When',
        render: row => (
          <span className="whitespace-nowrap text-sm text-foreground">
            {formatDateTime(row.occurred_at)}
          </span>
        ),
      },
      {
        key: 'actor',
        header: 'Actor',
        render: row => (
          <div className="min-w-0">
            <p className="truncate text-sm font-medium text-foreground">{row.actor.full_name}</p>
            <p className="truncate text-xs text-muted-foreground">{row.actor.matricule}</p>
          </div>
        ),
      },
      {
        key: 'action_type',
        header: 'Action',
        render: row => (
          <span className="text-sm font-medium text-foreground">
            {humanizeActionType(row.action_type)}
          </span>
        ),
      },
      {
        key: 'target',
        header: 'Target',
        render: row => (
          <div className="min-w-0">
            <p className="truncate text-sm text-foreground">{row.target_repr || '—'}</p>
            <p className="truncate text-xs text-muted-foreground">
              {row.target_model}
              {row.target_id ? ` · ${row.target_id}` : ''}
            </p>
          </div>
        ),
      },
    ],
    [expanded],
  )

  return (
    <>
      <PageHeader
        title="Audit log"
        description="Sensitive admin actions, append-only and filtered by action, actor, target, or date."
      />

      {/* Filters */}
      <div className="mb-4 grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
        <div className="space-y-1">
          <Label className="text-xs">Action type</Label>
          <Select
            value={actionType}
            onValueChange={withPageReset(v => setActionType(v as 'all' | AuditActionType))}
          >
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All actions</SelectItem>
              {ACTION_TYPES.map(t => (
                <SelectItem key={t} value={t}>
                  {humanizeActionType(t)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-xs">Target model</Label>
          <Select value={targetModel} onValueChange={withPageReset(setTargetModel)}>
            <SelectTrigger>
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value="all">All models</SelectItem>
              {TARGET_MODELS.map(m => (
                <SelectItem key={m} value={m}>
                  {m}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>

        <div className="space-y-1">
          <Label className="text-xs">Date from</Label>
          <Input
            type="datetime-local"
            value={dateFrom}
            onChange={e => {
              setDateFrom(e.target.value)
              setPage(1)
            }}
          />
        </div>

        <div className="space-y-1">
          <Label className="text-xs">Date to</Label>
          <Input
            type="datetime-local"
            value={dateTo}
            onChange={e => {
              setDateTo(e.target.value)
              setPage(1)
            }}
          />
        </div>

        <div className="space-y-1 sm:col-span-2 lg:col-span-4">
          <Label className="text-xs">Actor</Label>
          {/* Search across all business identities — actors are usually admins/super-admins
              who may be TEACHER or ADMINISTRATIVE_STAFF by business_identity. */}
          <UserPicker
            value={actor}
            onChange={v => {
              setActor(v)
              setPage(1)
            }}
            multi={false}
            identity="TEACHER"
            placeholder="Search admins by name or matricule…"
          />
        </div>
      </div>

      {(actionType !== 'all' || targetModel !== 'all' || actor.length > 0 || dateFrom || dateTo) && (
        <div className="mb-3">
          <Button
            type="button"
            variant="ghost"
            size="sm"
            onClick={() => {
              setActionType('all')
              setTargetModel('all')
              setActor([])
              setDateFrom('')
              setDateTo('')
            }}
          >
            Clear filters
          </Button>
        </div>
      )}

      {logsApi.error && (
        <div className="mb-4">
          <InlineError message={logsApi.error} />
        </div>
      )}

      <DataTable<AuditLogEntry>
        columns={columns}
        data={data}
        keyField="id"
        isLoading={logsApi.isLoading}
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
            icon={ScrollText}
            title="No log entries"
            description="No admin actions match the current filters."
          />
        }
      />

      {/* Expanded row details (rendered outside the table to avoid colspan plumbing) */}
      {expanded !== null && data.find(d => d.id === expanded) && (
        <div className="mt-3">
          <ExpandedRowDetails entry={data.find(d => d.id === expanded)!} />
        </div>
      )}
    </>
  )
}
