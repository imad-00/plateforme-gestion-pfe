'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { api } from '@/lib/api-client'
import type { UnreadCountResponse } from '@/lib/types'

const POLL_INTERVAL_MS = 30_000

interface UseUnreadNotificationsResult {
  unreadCount: number
  refresh: () => void
  setUnreadCount: (count: number) => void
}

// Polls GET /api/notifications/unread-count/ every 30s. Pauses when the tab
// is hidden (Page Visibility API) to avoid burning bandwidth on background
// tabs, and re-fetches immediately when the tab becomes visible again.
//
// Components that mutate read state (mark-read, mark-all-read) can call
// `refresh()` to re-sync immediately, or `setUnreadCount(n)` to apply an
// optimistic update without a network round trip.

export function useUnreadNotifications(): UseUnreadNotificationsResult {
  const [unreadCount, setUnreadCount] = useState(0)
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const fetchInFlightRef = useRef(false)

  const fetchCount = useCallback(async () => {
    if (fetchInFlightRef.current) return
    fetchInFlightRef.current = true
    try {
      const res = await api.get<UnreadCountResponse>('/api/notifications/unread-count/')
      setUnreadCount(res.unread_count)
    } catch {
      // Silent — the bell is a background feature; surface only if the
      // dedicated page errors out.
    } finally {
      fetchInFlightRef.current = false
    }
  }, [])

  // Start/stop polling alongside tab visibility.
  useEffect(() => {
    function start() {
      if (intervalRef.current !== null) return
      fetchCount()
      intervalRef.current = setInterval(fetchCount, POLL_INTERVAL_MS)
    }
    function stop() {
      if (intervalRef.current === null) return
      clearInterval(intervalRef.current)
      intervalRef.current = null
    }

    if (typeof document === 'undefined') return

    if (!document.hidden) start()

    function onVisibilityChange() {
      if (document.hidden) {
        stop()
      } else {
        start()
      }
    }

    document.addEventListener('visibilitychange', onVisibilityChange)
    return () => {
      document.removeEventListener('visibilitychange', onVisibilityChange)
      stop()
    }
  }, [fetchCount])

  return { unreadCount, refresh: fetchCount, setUnreadCount }
}
