'use client'

import type { ReactNode } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table'

// ─── Types ────────────────────────────────────────────────────────────────────

export interface Column<T> {
  key: string
  header: string
  /** Custom cell renderer. Falls back to String(row[key]) when omitted. */
  render?: (row: T) => ReactNode
  /** Extra className applied to both <th> and <td> — useful for width control. */
  className?: string
}

interface DataTableProps<T> {
  columns: Column<T>[]
  data: T[]
  /** Field used as the React row key — must be unique across rows. */
  keyField: keyof T
  isLoading?: boolean
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  /** Omit to hide the page-size selector. */
  onPageSizeChange?: (size: number) => void
  /** Shown inside the table body when data is empty and not loading. */
  emptyState?: ReactNode
}

const PAGE_SIZE_OPTIONS = [10, 25, 50] as const
const SKELETON_ROWS = 5

// ─── Component ────────────────────────────────────────────────────────────────

export function DataTable<T>({
  columns,
  data,
  keyField,
  isLoading = false,
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
  emptyState,
}: DataTableProps<T>) {
  // Defensive guard: callers must pass T[] but a runtime undefined can arrive
  // during the brief window before useApi resolves. Default to [] so the table
  // never crashes before data arrives.
  const rows: T[] = data ?? []
  const totalPages = Math.max(1, Math.ceil(total / pageSize))
  const rangeStart = total === 0 ? 0 : (page - 1) * pageSize + 1
  const rangeEnd = Math.min(page * pageSize, total)
  const isEmpty = !isLoading && rows.length === 0

  return (
    <div className="overflow-hidden rounded-xl border border-border bg-card shadow-card">
      {/* ── Table ── */}
      <Table>
        <TableHeader>
          <TableRow className="bg-muted/30 hover:bg-muted/30">
            {columns.map(col => (
              <TableHead key={col.key} className={col.className}>
                {col.header}
              </TableHead>
            ))}
          </TableRow>
        </TableHeader>

        <TableBody>
          {isLoading ? (
            Array.from({ length: SKELETON_ROWS }).map((_, i) => (
              <TableRow key={i} className="hover:bg-transparent">
                {columns.map(col => (
                  <TableCell key={col.key} className={col.className}>
                    <Skeleton className="h-4 w-full max-w-40" />
                  </TableCell>
                ))}
              </TableRow>
            ))
          ) : isEmpty ? (
            <TableRow className="hover:bg-transparent">
              <TableCell
                colSpan={columns.length}
                className="py-12 text-center text-sm text-muted-foreground"
              >
                {emptyState ?? 'No results.'}
              </TableCell>
            </TableRow>
          ) : (
            rows.map(row => (
              <TableRow key={String(row[keyField])}>
                {columns.map(col => (
                  <TableCell key={col.key} className={col.className}>
                    {col.render
                      ? col.render(row)
                      : String(
                          (row as Record<string, unknown>)[col.key] ?? '',
                        )}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>

      {/* ── Pagination footer ── */}
      <div className="flex items-center justify-between border-t border-border bg-muted/20 px-4 py-2.5">
        {/* Page-size selector */}
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <span>Rows per page</span>
          {onPageSizeChange ? (
            <select
              value={pageSize}
              onChange={e => onPageSizeChange(Number(e.target.value))}
              disabled={isLoading}
              className="h-7 rounded-md border border-input bg-transparent px-1.5 text-sm text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring disabled:opacity-50"
            >
              {PAGE_SIZE_OPTIONS.map(s => (
                <option key={s} value={s}>
                  {s}
                </option>
              ))}
            </select>
          ) : (
            <span className="font-medium text-foreground">{pageSize}</span>
          )}
        </div>

        {/* Range label + prev/next */}
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">
            {total === 0
              ? '0 results'
              : `${rangeStart}–${rangeEnd} of ${total}`}
          </span>
          <div className="flex items-center gap-1">
            <Button
              variant="outline"
              size="icon-sm"
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1 || isLoading}
              aria-label="Previous page"
            >
              <ChevronLeft className="size-4" />
            </Button>
            <Button
              variant="outline"
              size="icon-sm"
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages || isLoading}
              aria-label="Next page"
            >
              <ChevronRight className="size-4" />
            </Button>
          </div>
        </div>
      </div>
    </div>
  )
}
