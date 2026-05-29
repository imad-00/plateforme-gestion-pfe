'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { AlertCircle, Bell, CheckCheck } from 'lucide-react'
import { api, ApiClientError } from '@/lib/api-client'
import type { Notification } from '@/lib/types'
import { useUnreadNotifications } from '@/hooks/use-unread-notifications'
import { Button } from '@/components/ui/button'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Skeleton } from '@/components/ui/skeleton'

const PANEL_PAGE_SIZE = 10

function extractMessage(err: unknown): string {
  if (err instanceof ApiClientError) return err.message
  return err instanceof Error ? err.message : 'An unexpected error occurred.'
}

// Relative time formatter — keeps the panel compact ("3m", "2h", "5d").
function formatRelative(iso: string): string {
  const ms = Date.now() - new Date(iso).getTime()
  if (ms < 60_000) return 'just now'
  const mins = Math.floor(ms / 60_000)
  if (mins < 60) return `${mins}m`
  const hours = Math.floor(mins / 60)
  if (hours < 24) return `${hours}h`
  const days = Math.floor(hours / 24)
  if (days < 7) return `${days}d`
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short' })
}

export function NotificationBell() {
  const router = useRouter()
  const { unreadCount, refresh, setUnreadCount } = useUnreadNotifications()
  const [open, setOpen] = useState(false)
  const [items, setItems] = useState<Notification[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [busyId, setBusyId] = useState<number | null>(null)

  // Fetch latest items each time the panel opens — fresh state every visit.
  useEffect(() => {
    if (!open) return
    let cancelled = false
    async function load() {
      setLoading(true)
      setError(null)
      try {
        const res = await api.get<Notification[]>(
          `/api/notifications/?limit=${PANEL_PAGE_SIZE}`,
        )
        if (!cancelled) setItems(res)
      } catch (err) {
        if (!cancelled) setError(extractMessage(err))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    load()
    return () => {
      cancelled = true
    }
  }, [open])

  async function handleItemClick(n: Notification) {
    setBusyId(n.id)
    setError(null)
    try {
      if (!n.is_read) {
        await api.post(`/api/notifications/${n.id}/read/`)
        setItems(prev => prev.map(x => (x.id === n.id ? { ...x, is_read: true } : x)))
        setUnreadCount(Math.max(0, unreadCount - 1))
      }
      if (n.link_url) {
        setOpen(false)
        router.push(n.link_url)
      }
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setBusyId(null)
    }
  }

  async function handleMarkAllRead() {
    setBusyId(-1)
    setError(null)
    try {
      await api.post('/api/notifications/read-all/')
      setItems(prev => prev.map(x => ({ ...x, is_read: true })))
      setUnreadCount(0)
    } catch (err) {
      setError(extractMessage(err))
    } finally {
      setBusyId(null)
    }
  }

  const badge =
    unreadCount > 0 ? (unreadCount > 99 ? '99+' : String(unreadCount)) : null

  return (
    <Popover open={open} onOpenChange={open => { setOpen(open); if (open) refresh() }}>
      <PopoverTrigger asChild>
        <Button
          variant="ghost"
          size="icon-sm"
          className="relative text-muted-foreground hover:text-foreground"
          title="Notifications"
          aria-label={`Notifications${badge ? ` (${badge} unread)` : ''}`}
        >
          <Bell className="size-4" />
          {badge && (
            <span className="absolute -right-0.5 -top-0.5 flex h-4 min-w-4 items-center justify-center rounded-full bg-status-error-fg px-1 text-[10px] font-semibold leading-none text-white">
              {badge}
            </span>
          )}
        </Button>
      </PopoverTrigger>

      <PopoverContent align="end" className="w-96 p-0">
        {/* Header */}
        <div className="flex items-center justify-between gap-2 border-b border-border px-3 py-2">
          <p className="text-sm font-semibold">Notifications</p>
          {unreadCount > 0 && (
            <Button
              variant="ghost"
              size="sm"
              disabled={busyId !== null}
              onClick={handleMarkAllRead}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              <CheckCheck className="size-3.5" />
              Mark all read
            </Button>
          )}
        </div>

        {/* Body */}
        <div className="max-h-96 overflow-y-auto">
          {loading ? (
            <div className="space-y-2 p-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <Skeleton key={i} className="h-14 w-full rounded-md" />
              ))}
            </div>
          ) : error ? (
            <div className="flex items-start gap-2 p-3 text-sm text-status-error-fg">
              <AlertCircle className="mt-0.5 size-4 shrink-0" />
              <span>{error}</span>
            </div>
          ) : items.length === 0 ? (
            <div className="px-3 py-8 text-center">
              <Bell className="mx-auto mb-2 size-5 text-muted-foreground" />
              <p className="text-sm text-muted-foreground">You&apos;re all caught up.</p>
            </div>
          ) : (
            <ul className="divide-y divide-border">
              {items.map(n => (
                <li key={n.id}>
                  <button
                    type="button"
                    disabled={busyId !== null}
                    onClick={() => handleItemClick(n)}
                    className={`block w-full px-3 py-2.5 text-left transition-colors hover:bg-muted disabled:opacity-60 ${
                      !n.is_read ? 'bg-primary/[0.03]' : ''
                    }`}
                  >
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0 flex-1">
                        <p className="flex items-center gap-1.5 text-sm font-medium text-foreground">
                          {!n.is_read && (
                            <span
                              className="inline-block size-1.5 shrink-0 rounded-full bg-primary"
                              aria-label="Unread"
                            />
                          )}
                          <span className="truncate">{n.title}</span>
                        </p>
                        <p className="mt-0.5 line-clamp-2 text-xs text-muted-foreground">
                          {n.message}
                        </p>
                      </div>
                      <span className="shrink-0 text-xs text-muted-foreground">
                        {formatRelative(n.created_at)}
                      </span>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* Footer */}
        <div className="border-t border-border px-3 py-2">
          <Link
            href="/notifications"
            onClick={() => setOpen(false)}
            className="block text-center text-xs font-medium text-primary underline-offset-4 hover:underline"
          >
            View all notifications →
          </Link>
        </div>
      </PopoverContent>
    </Popover>
  )
}
