import { useCallback, useEffect, useRef, useState } from 'react'

interface UseApiResult<T> {
  data: T | null
  isLoading: boolean
  error: string | null
  refetch: () => void
}

export function useApi<T>(
  fetcher: () => Promise<T>,
  deps: React.DependencyList = [],
): UseApiResult<T> {
  const [data, setData] = useState<T | null>(null)
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  // Stable ref so refetch() always calls the latest fetcher without
  // needing to be recreated when the fetcher closure changes.
  const fetcherRef = useRef(fetcher)
  fetcherRef.current = fetcher

  const run = useCallback(async (cancelled: { value: boolean }) => {
    setIsLoading(true)
    setError(null)
    try {
      const result = await fetcherRef.current()
      if (!cancelled.value) setData(result)
    } catch (err) {
      if (!cancelled.value) {
        setError(err instanceof Error ? err.message : 'An unexpected error occurred.')
      }
    } finally {
      if (!cancelled.value) setIsLoading(false)
    }
  }, [])

  useEffect(() => {
    const cancelled = { value: false }
    run(cancelled)
    return () => {
      cancelled.value = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps)

  const refetch = useCallback(() => {
    const cancelled = { value: false }
    run(cancelled)
  }, [run])

  return { data, isLoading, error, refetch }
}
