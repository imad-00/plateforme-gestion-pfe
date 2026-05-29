'use client'

import { useCallback, useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { AlertCircle, Bell, CheckCheck, ExternalLink, Loader2 } from 'lucide-react'
import { useAuth } from '@/lib/auth-context'
import { api, ApiClientError } from '@/lib/api-client'
import type { Notification } from '@/lib/types'
import { useUnreadNotifications } from '@/hooks/use-unread-notifications'
import { PageHeader } from '@/components/layout/page-header'
import { Button } from '@/components/ui/button'
import { Card } from '@/components/ui/card'
import { Skeleton } from '@/components/ui/skeleton'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { EmptyState } from '@/components/shared/empty-state'

// ─── Helpers ──────────────────────────────────────────────────────────────────

const PAGE_SIZE = 20

function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) return err.message
  return err instanceof Error ? err.message : 'An unexpected error occurred.'
}

function InlineError({ message }: { message: string }) {
  return (
    <div className="flex items-start gap-2 rounded-lg bg-status-error-bg p-3 text-sm text-status-error-fg">
      <AlertCircle className="mt-0.5 size-4 shrink-0" />
      <span>{message}</span>
    </div>
  )
}

function formatDateTime(iso: string): string {
  return new Date(iso).toLocaleString('en-GB', {
    day: 'numeric',
    month: 'short',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const FILTER_OPTIONS = [
  { value: 'all', label: 'All notifications' },
  { value: 'unread', label: 'Unread only' },
] as const

// ─── View ─────────────────────────────────────────────────────────────────────

export function NotificationsView() {
  useAuth()
  const router = useRouter()
  const { refresh: refreshBellCount, setUnreadCount: setBellCount } = useUnreadNotifications()

  const [filter, setFilter] = useState<'all' | 'unread'>('all')
  const [items, setItems] = useState<Notification[]>([])
  const [offset, setOffset] = useState(0)
  const [hasMore, setHasMore] = useState(true)
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)

  const fetchPage = useCallback(
    async (pageOffset: number, append: boolean) => {
      if (append) {
        setLoadingMore(true)
      } else {
        setLoading(true)
      }
      setError(null)
      try {
        const params = new URLSearchParams({
          limit: String(PAGE_SIZE),
          offset: String(pageOffset),
        })
        if (filter === 'unread') params.set('unread', 'true')
        const res = await api.get<Notification[]>(`/api/notifications/?${params}`)
        setItems(prev => (append ? [...prev, ...res] : res))
        setHasMore(res.length === PAGE_SIZE)
        setOffset(pageOffset + res.length)
      } catch (err) {
        setError(extractMessage(err))
      } finally {
        setLoading(false)
        setLoadingMore(false)
      }
    },
    [filter],
  )

  // Reset + fetch from scratch when the filter changes.
  useEffect(() => {
    setOffset(0)
    setHasMore(true)
    fetchPage(0, false)
  }, [fetchPage])

  async function handleMarkRead(n: Notification) {
    if (n.is_read) return
    setBusyId(n.id)
    setError(null)
    try {
      await api.post(`/api/notifications/${n.id}/read/`)
      // Optimistic local update: flip the flag in-place rather than removing
      // even on the unread filter — gives the user a brief "ack" before the
      // next fetch trims the list.
      setItems(prev => prev.map(x => (x.id === n.id ? { ...x, is_read: true } : x)))
      refreshBellCount()
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setBusyId(null)
    }
  }

  async function handleItemClick(n: Notification) {
    if (busyId !== null) return
    if (!n.is_read) await handleMarkRead(n)
    if (n.link_url) router.push(n.link_url)
  }

  async function handleMarkAllRead() {
    setBusyId(-1)
    setError(null)
    try {
      await api.post('/api/notifications/read-all/')
      setItems(prev => prev.map(x => ({ ...x, is_read: true })))
      setBellCount(0)
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setBusyId(null)
    }
  }

  const hasUnreadInView = items.some(n => !n.is_read)

  return (
    <>
      <PageHeader
        title="Notifications"
        description="Workflow events delivered to you."
        action={
          hasUnreadInView ? (
            <Button
              variant="outline"
              size="sm"
              disabled={busyId !== null}
              onClick={handleMarkAllRead}
            >
              {busyId === -1 ? (
                <Loader2 className="size-4 animate-spin" />
              ) : (
                <CheckCheck className="size-4" />
              )}
              Mark all read
            </Button>
          ) : undefined
        }
      />

      <div className="mb-4 flex items-center gap-3">
        <Select value={filter} onValueChange={v => setFilter(v as 'all' | 'unread')}>
          <SelectTrigger className="w-44">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {FILTER_OPTIONS.map(o => (
              <SelectItem key={o.value} value={o.value}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {error && <div className="mb-4"><InlineError message={error} /></div>}

      {loading ? (
        <div className="space-y-2">
          {Array.from({ length: 5 }).map((_, i) => (
            <Skeleton key={i} className="h-20 w-full rounded-xl" />
          ))}
        </div>
      ) : items.length === 0 ? (
        <EmptyState
          icon={Bell}
          title={filter === 'unread' ? 'No unread notifications' : 'No notifications yet'}
          description={
            filter === 'unread'
              ? "You're all caught up."
              : "When the platform produces events for you, they'll appear here."
          }
        />
      ) : (
        <ul className="space-y-2">
          {items.map(n => (
            <li key={n.id}>
              <NotificationCard
                notification={n}
                busy={busyId === n.id}
                onClick={() => handleItemClick(n)}
                onMarkRead={() => handleMarkRead(n)}
              />
            </li>
          ))}
        </ul>
      )}

      {!loading && hasMore && items.length > 0 && (
        <div className="mt-6 flex justify-center">
          <Button
            variant="outline"
            disabled={loadingMore}
            onClick={() => fetchPage(offset, true)}
          >
            {loadingMore && <Loader2 className="size-4 animate-spin" />}
            Load more
          </Button>
        </div>
      )}
    </>
  )
}

// ─── Notification card ────────────────────────────────────────────────────────

function NotificationCard({
  notification,
  busy,
  onClick,
  onMarkRead,
}: {
  notification: Notification
  busy: boolean
  onClick: () => void
  onMarkRead: () => void
}) {
  const isImportant = notification.importance === 'IMPORTANT'

  return (
    <Card
      className={`relative transition-colors ${
        !notification.is_read ? 'border-primary/40 bg-primary/[0.03]' : ''
      }`}
    >
      <button
        type="button"
        disabled={busy}
        onClick={onClick}
        className="block w-full p-4 text-left disabled:opacity-60"
      >
        <div className="flex items-start gap-3">
          {/* Unread dot */}
          <span
            className={`mt-1.5 size-2 shrink-0 rounded-full ${
              notification.is_read ? 'bg-transparent' : 'bg-primary'
            }`}
            aria-hidden
          />

          {/* Body */}
          <div className="min-w-0 flex-1 space-y-1">
            <div className="flex flex-wrap items-baseline gap-x-2">
              <p className="text-sm font-semibold text-foreground">
                {notification.title}
              </p>
              {isImportant && (
                <span className="rounded border border-status-warning-border bg-status-warning-bg px-1.5 py-0.5 text-[10px] font-semibold uppercase tracking-wider text-status-warning-fg">
                  Important
                </span>
              )}
            </div>
            <p className="whitespace-pre-line text-sm text-muted-foreground">
              {notification.message}
            </p>
            <div className="flex items-center gap-3 pt-1 text-xs text-muted-foreground">
              <span>{formatDateTime(notification.created_at)}</span>
              {notification.link_url && (
                <span className="inline-flex items-center gap-1 text-primary">
                  <ExternalLink className="size-3" />
                  Has a link
                </span>
              )}
            </div>
          </div>
        </div>
      </button>

      {/* Inline "mark as read" — only when link_url is empty so the
          card click can't reach it. Otherwise the click handler does it. */}
      {!notification.is_read && !notification.link_url && (
        <Button
          variant="ghost"
          size="sm"
          className="absolute right-2 top-2 text-xs text-muted-foreground hover:text-foreground"
          disabled={busy}
          onClick={e => {
            e.stopPropagation()
            onMarkRead()
          }}
        >
          {busy ? <Loader2 className="size-3.5 animate-spin" /> : 'Mark read'}
        </Button>
      )}
    </Card>
  )
}
