'use client'

import { useState } from 'react'
import { AlertCircle, Download, FileSpreadsheet, Loader2 } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import { useApi } from '@/hooks/use-api'
import type {
  AcademicYear,
  DefenseReportRow,
  JuryPlanningReportRow,
  PaginatedResponse,
  ReportEnvelope,
  StudentResultReportRow,
  TeamAssignmentReportRow,
} from '@/lib/types'
import { DataTable, type Column } from '@/components/shared/data-table'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from '@/components/ui/tabs'

// ─── Helpers ──────────────────────────────────────────────────────────────────

function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) return err.message
  return err instanceof Error ? err.message : 'An unexpected error occurred.'
}

function fileLabel(year: AcademicYear): string {
  return (year.year_label || year.year || String(year.id)).replace(/[ /]/g, '-')
}

// ─── Download buttons ─────────────────────────────────────────────────────────
// One pair (CSV + Excel) per report. Both hit blob-download endpoints that
// require the JWT, so we go through `api.download` rather than naked <a> tags.

function DownloadButtons({
  csvPath,
  xlsxPath,
  baseName,
}: {
  csvPath: string
  xlsxPath: string
  baseName: string
}) {
  const [busy, setBusy] = useState<'csv' | 'xlsx' | null>(null)
  const [error, setError] = useState<string | null>(null)

  async function trigger(kind: 'csv' | 'xlsx') {
    setBusy(kind)
    setError(null)
    try {
      await api.download(kind === 'csv' ? csvPath : xlsxPath, `${baseName}.${kind}`)
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setBusy(null)
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex flex-wrap gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => trigger('csv')}
          disabled={busy !== null}
        >
          {busy === 'csv' ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <Download className="size-3.5" />
          )}
          CSV
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => trigger('xlsx')}
          disabled={busy !== null}
        >
          {busy === 'xlsx' ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <FileSpreadsheet className="size-3.5" />
          )}
          Excel
        </Button>
      </div>
      {error && <p className="text-xs text-status-error-fg">{error}</p>}
    </div>
  )
}

// ─── Column definitions (mirrored from backend ReportService constants) ───────

const DEFENSE_COLUMNS: Column<DefenseReportRow>[] = [
  { key: 'team_code', header: 'Team', render: r => (
    <div className="min-w-0">
      <p className="truncate text-sm font-medium text-foreground">{r.team_name || '—'}</p>
      <p className="text-xs text-muted-foreground">{r.team_code}</p>
    </div>
  ) },
  { key: 'subject_title', header: 'Subject', render: r => r.subject_title || '—' },
  { key: 'defense_status', header: 'Status' },
  { key: 'jury_president', header: 'President', render: r => r.jury_president || '—' },
  { key: 'jury_examiners', header: 'Examiners', render: r => r.jury_examiners || '—' },
  { key: 'scheduled_at', header: 'Scheduled', render: r => r.scheduled_at || '—' },
  { key: 'location', header: 'Location', render: r => r.location || '—' },
  { key: 'final_grade', header: 'Grade', render: r => r.final_grade || '—' },
]

const TEAM_ASSIGNMENT_COLUMNS: Column<TeamAssignmentReportRow>[] = [
  { key: 'team_code', header: 'Team', render: r => (
    <div className="min-w-0">
      <p className="truncate text-sm font-medium text-foreground">{r.team_name}</p>
      <p className="text-xs text-muted-foreground">{r.team_code}</p>
    </div>
  ) },
  { key: 'team_status', header: 'Status' },
  { key: 'selection_round', header: 'Round' },
  { key: 'annual_average', header: 'Average', render: r => r.annual_average || '—' },
  { key: 'leader', header: 'Leader', render: r => r.leader || '—' },
  { key: 'subject_title', header: 'Subject', render: r => r.subject_title || '—' },
  { key: 'assignment_status', header: 'Assignment' },
]

const STUDENT_RESULTS_COLUMNS: Column<StudentResultReportRow>[] = [
  { key: 'student_matricule', header: 'Matricule' },
  { key: 'student_full_name', header: 'Student' },
  { key: 'team_code', header: 'Team', render: r => r.team_code || '—' },
  { key: 'team_role', header: 'Role', render: r => r.team_role || '—' },
  { key: 'subject_title', header: 'Subject', render: r => r.subject_title || '—' },
  { key: 'defense_status', header: 'Defense', render: r => r.defense_status || '—' },
  { key: 'final_grade', header: 'Grade', render: r => r.final_grade || '—' },
  { key: 'result_status', header: 'Outcome' },
]

const JURY_PLANNING_COLUMNS: Column<JuryPlanningReportRow>[] = [
  { key: 'scheduled_at', header: 'Scheduled', render: r => r.scheduled_at || '—' },
  { key: 'location', header: 'Location', render: r => r.location || '—' },
  { key: 'team_code', header: 'Team', render: r => (
    <div className="min-w-0">
      <p className="truncate text-sm font-medium text-foreground">{r.team_name}</p>
      <p className="text-xs text-muted-foreground">{r.team_code}</p>
    </div>
  ) },
  { key: 'subject_title', header: 'Subject', render: r => r.subject_title || '—' },
  { key: 'president', header: 'President', render: r => r.president || '—' },
  { key: 'examiners', header: 'Examiners', render: r => r.examiners || '—' },
  { key: 'pv_uploaded', header: 'PV' },
]

// ─── Generic report panel ─────────────────────────────────────────────────────

function ReportPanel<TRow>({
  year,
  endpointKey,
  columns,
  keyField,
  rowsFromResponse,
}: {
  year: AcademicYear
  endpointKey: 'defenses' | 'team-assignments' | 'student-results' | 'jury-planning'
  columns: Column<TRow>[]
  keyField: keyof TRow
  // Some rows have natural ids, some don't — let each report tell us how to key them.
  rowsFromResponse: (env: ReportEnvelope<TRow>) => TRow[]
}) {
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(25)

  const reportApi = useApi<ReportEnvelope<TRow>>(
    () => api.get(`/api/admin/reports/academic-years/${year.id}/${endpointKey}/`),
    [year.id, endpointKey],
  )

  const allRows = reportApi.data ? rowsFromResponse(reportApi.data) : []
  // Backend returns the full result set on one page; we paginate client-side
  // for navigability since reports can be long.
  const total = allRows.length
  const start = (page - 1) * pageSize
  const pageRows = allRows.slice(start, start + pageSize)

  const baseName = `${endpointKey}_${fileLabel(year)}`

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <p className="text-sm text-muted-foreground">
          {reportApi.isLoading ? 'Loading…' : `${total} row${total === 1 ? '' : 's'}`}
        </p>
        <DownloadButtons
          csvPath={`/api/admin/reports/academic-years/${year.id}/${endpointKey}.csv`}
          xlsxPath={`/api/admin/reports/academic-years/${year.id}/${endpointKey}.xlsx`}
          baseName={baseName}
        />
      </div>

      {reportApi.error && <InlineError message={reportApi.error} />}

      <DataTable<TRow>
        columns={columns}
        data={pageRows}
        keyField={keyField}
        isLoading={reportApi.isLoading}
        page={page}
        pageSize={pageSize}
        total={total}
        onPageChange={setPage}
        onPageSizeChange={s => {
          setPageSize(s)
          setPage(1)
        }}
        emptyState="No data for this report yet."
      />
    </div>
  )
}

// ─── Main view ────────────────────────────────────────────────────────────────

export function ReportsView() {
  useAuth()
  const yearsApi = useApi<PaginatedResponse<AcademicYear>>(
    () => api.get('/api/admin/academic-years/?page_size=100'),
    [],
  )

  const [yearId, setYearId] = useState<string>('')

  // Auto-select the first year once they load (preferring ACTIVE).
  const years = yearsApi.data?.results ?? []
  const fallbackYearId =
    yearId ||
    String(
      years.find(y => y.status === 'ACTIVE')?.id ?? years[0]?.id ?? '',
    )
  const selectedYear = years.find(y => String(y.id) === fallbackYearId) ?? null

  return (
    <>
      <PageHeader
        title="Reports"
        description="Institutional outputs by academic year — preview and download as CSV or Excel."
      />

      <div className="mb-4 flex flex-wrap items-end gap-3">
        <div className="space-y-1">
          <p className="text-xs font-medium text-muted-foreground">Academic year</p>
          <Select
            value={fallbackYearId}
            onValueChange={setYearId}
            disabled={yearsApi.isLoading}
          >
            <SelectTrigger className="w-56">
              <SelectValue placeholder="Select a year" />
            </SelectTrigger>
            <SelectContent>
              {years.map(y => (
                <SelectItem key={y.id} value={String(y.id)}>
                  {y.year_label || y.year} ({y.status.toLowerCase()})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      </div>

      {selectedYear ? (
        <Tabs defaultValue="defenses">
          <TabsList className="mb-4">
            <TabsTrigger value="defenses">Defenses & PVs</TabsTrigger>
            <TabsTrigger value="assignments">Team assignments</TabsTrigger>
            <TabsTrigger value="results">Student results</TabsTrigger>
            <TabsTrigger value="jury">Jury planning</TabsTrigger>
          </TabsList>

          <TabsContent value="defenses">
            <ReportPanel<DefenseReportRow>
              year={selectedYear}
              endpointKey="defenses"
              columns={DEFENSE_COLUMNS}
              keyField="defense_id"
              rowsFromResponse={env => env.results}
            />
          </TabsContent>

          <TabsContent value="assignments">
            <ReportPanel<TeamAssignmentReportRow>
              year={selectedYear}
              endpointKey="team-assignments"
              columns={TEAM_ASSIGNMENT_COLUMNS}
              keyField="team_code"
              rowsFromResponse={env => env.results}
            />
          </TabsContent>

          <TabsContent value="results">
            <ReportPanel<StudentResultReportRow>
              year={selectedYear}
              endpointKey="student-results"
              columns={STUDENT_RESULTS_COLUMNS}
              keyField="student_matricule"
              rowsFromResponse={env => env.results}
            />
          </TabsContent>

          <TabsContent value="jury">
            <ReportPanel<JuryPlanningReportRow>
              year={selectedYear}
              endpointKey="jury-planning"
              columns={JURY_PLANNING_COLUMNS}
              // jury planning has no natural id; fall back to scheduled_at + team_code
              // which is unique within a single year's jury schedule.
              keyField="team_code"
              rowsFromResponse={env => env.results}
            />
          </TabsContent>
        </Tabs>
      ) : (
        <p className="text-sm text-muted-foreground">Select an academic year above to preview reports.</p>
      )}
    </>
  )
}
