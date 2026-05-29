'use client'

import { useState } from 'react'
import Link from 'next/link'
import {
  AlertCircle,
  ArrowLeft,
  CalendarClock,
  FileText,
  Gavel,
  Lock,
  MapPin,
  Upload,
} from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type {
  CampaignStatus,
  DefenseDetail,
  DefenseJuryAssignment,
} from '@/lib/types'
import { PageHeader } from '@/components/layout/page-header'
import { StatusBadge } from '@/components/shared/status-badge'
import { UploadPVDialog } from '@/components/shared/upload-pv-dialog'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'

// ─── Constants ────────────────────────────────────────────────────────────────

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? 'http://localhost:8000'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function buildFileUrl(path: string): string {
  return path.startsWith('http') ? path : `${API_BASE}${path}`
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1_048_576) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / 1_048_576).toFixed(1)} MB`
}

function formatDateTime(iso: string | null): string {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('en-GB', {
    day: 'numeric', month: 'short', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  })
}

function initials(first: string, last: string): string {
  return `${first[0] ?? ''}${last[0] ?? ''}`.toUpperCase()
}

function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

function JuryRow({ a, isMe }: { a: DefenseJuryAssignment; isMe: boolean }) {
  return (
    <div
      className={[
        'flex items-center gap-3 rounded-lg border px-3 py-2',
        isMe ? 'border-primary/40 bg-primary/5' : 'border-border bg-card',
      ].join(' ')}
    >
      <Avatar size="sm">
        <AvatarFallback className="bg-primary/10 text-xs font-medium text-primary">
          {initials(a.user.first_name, a.user.last_name)}
        </AvatarFallback>
      </Avatar>
      <div className="min-w-0 flex-1">
        <p className="truncate text-sm font-medium text-foreground">
          {a.user.first_name} {a.user.last_name}
          {isMe && <span className="ml-2 text-xs font-normal text-primary">(you)</span>}
        </p>
        <p className="text-xs text-muted-foreground">{a.user.matricule}</p>
      </div>
      <StatusBadge status={a.role} />
    </div>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function JuryDefenseDetailView({ defenseId }: { defenseId: string }) {
  const { user } = useAuth()
  const campaignApi = useApi<CampaignStatus>(() => api.get('/api/campaign/current/'), [])
  const defenseApi = useApi<DefenseDetail>(
    () => api.get(`/api/jury/defenses/${defenseId}/`),
    [defenseId],
  )

  const [pvOpen, setPvOpen] = useState(false)

  if (defenseApi.isLoading || campaignApi.isLoading) {
    return (
      <>
        <PageHeader title="Defense" description="Jury workspace" />
        <Skeleton className="h-64 w-full rounded-xl" />
      </>
    )
  }

  if (defenseApi.error) {
    return (
      <>
        <PageHeader title="Defense" description="Jury workspace" />
        <InlineError message={defenseApi.error} />
      </>
    )
  }

  const defense = defenseApi.data
  if (!defense) return null

  const openPhases = campaignApi.data?.open_phases ?? []
  const phaseOpen = openPhases.includes('DEFENSE_WINDOW')

  const myAssignment = user
    ? defense.jury_assignments.find(a => a.user.id === user.id) ?? null
    : null
  const isPresident = myAssignment?.role === 'PRESIDENT'
  const canUploadPV = phaseOpen && isPresident && defense.status === 'SCHEDULED'

  return (
    <>
      <div className="mb-2">
        <Link
          href="/jury/defenses"
          className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground"
        >
          <ArrowLeft className="size-3.5" />
          Jury defenses
        </Link>
      </div>
      <PageHeader
        title={defense.team.name}
        description={`${defense.team.team_code} · ${myAssignment ? `Your role: ${myAssignment.role.toLowerCase()}` : 'Not in jury'}`}
        action={<StatusBadge status={defense.status} />}
      />

      {!phaseOpen && (
        <div className="mb-4 flex items-start gap-2.5 rounded-lg border border-border bg-muted/40 p-3 text-sm text-muted-foreground">
          <Lock className="mt-0.5 size-4 shrink-0" />
          <span>The defense workflow is not open right now. This is a read-only view.</span>
        </div>
      )}

      <div className="space-y-4">
        {/* ── Schedule + PV action ── */}
        <Card>
          <CardHeader className="flex flex-row items-center justify-between gap-3 space-y-0">
            <CardTitle className="text-base">Schedule</CardTitle>
            {canUploadPV && (
              <Button size="sm" onClick={() => setPvOpen(true)}>
                <Upload className="size-3.5" />
                Upload PV
              </Button>
            )}
          </CardHeader>
          <CardContent>
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="flex items-center gap-2 text-sm">
                <CalendarClock className="size-4 shrink-0 text-muted-foreground" />
                <span className="text-foreground">{formatDateTime(defense.scheduled_at)}</span>
              </div>
              <div className="flex items-center gap-2 text-sm">
                <MapPin className="size-4 shrink-0 text-muted-foreground" />
                <span className="text-foreground">{defense.location || '—'}</span>
              </div>
            </div>
          </CardContent>
        </Card>

        {/* ── PV summary if COMPLETED ── */}
        {defense.status === 'COMPLETED' && (
          <Card>
            <CardHeader>
              <CardTitle className="text-base">PV (procès-verbal)</CardTitle>
            </CardHeader>
            <CardContent className="space-y-2">
              {defense.final_grade && (
                <p className="text-sm text-foreground">
                  Final grade: <span className="font-semibold">{defense.final_grade}</span> / 20
                </p>
              )}
              {defense.deliberation && (
                <p className="whitespace-pre-line text-sm text-foreground">{defense.deliberation}</p>
              )}
              {defense.pv_uploaded_by && defense.pv_uploaded_at && (
                <p className="text-xs text-muted-foreground">
                  Uploaded by {defense.pv_uploaded_by.first_name} {defense.pv_uploaded_by.last_name} ·{' '}
                  {formatDateTime(defense.pv_uploaded_at)}
                </p>
              )}
              {defense.pv_file_url && (
                <a
                  href={buildFileUrl(defense.pv_file_url)}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1.5 text-sm font-medium text-primary hover:underline"
                >
                  <FileText className="size-3.5" />
                  Download PV
                </a>
              )}
            </CardContent>
          </Card>
        )}

        {/* ── Jury composition ── */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-1.5 text-base">
              <Gavel className="size-4 text-muted-foreground" />
              Jury
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1.5">
              {defense.jury_assignments.map(a => (
                <JuryRow key={a.id} a={a} isMe={!!user && a.user.id === user.id} />
              ))}
            </div>
          </CardContent>
        </Card>

        {/* ── Attached files ── */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Attached files
              <span className="ml-2 font-normal text-muted-foreground">
                ({defense.attached_files.length})
              </span>
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="space-y-1.5">
              {defense.attached_files.map(af => (
                <div
                  key={af.id}
                  className="flex items-center gap-2 rounded-lg border border-border bg-card p-2.5"
                >
                  <span className="size-6 shrink-0 rounded-md bg-muted text-center text-xs font-medium leading-6 text-muted-foreground">
                    {af.order}
                  </span>
                  <FileText className="size-4 shrink-0 text-muted-foreground" />
                  <div className="min-w-0 flex-1">
                    <p className="truncate text-sm font-medium text-foreground">
                      {af.deliverable_file.original_filename}
                    </p>
                    <p className="text-xs text-muted-foreground">
                      {formatSize(af.deliverable_file.file_size)}
                    </p>
                  </div>
                  <a
                    href={buildFileUrl(af.deliverable_file.file_url)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-xs font-medium text-primary hover:underline"
                  >
                    Open
                  </a>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>
      </div>

      <UploadPVDialog
        open={pvOpen}
        onOpenChange={setPvOpen}
        endpoint={`/api/jury/defenses/${defense.id}/pv/`}
        onSuccess={() => defenseApi.refetch()}
      />
    </>
  )
}
