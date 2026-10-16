import { useQuery } from '@tanstack/react-query'

import { api } from '@/lib/api'

/**
 * Polls the API's health endpoint until it answers. Free-tier hosts put idle
 * services to sleep, so the UI shows a "warming up" notice instead of a
 * confusing failure on the first request.
 */
export function useApiHealth() {
  return useQuery({
    queryKey: ['health'],
    queryFn: api.health,
    retry: 20,
    retryDelay: (attempt) => Math.min(1000 * 1.5 ** attempt, 5000),
    staleTime: 5 * 60 * 1000,
    refetchOnWindowFocus: false,
  })
}
