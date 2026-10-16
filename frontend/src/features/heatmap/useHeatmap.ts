import { useQuery } from '@tanstack/react-query'

import { api } from '@/lib/api'

export function useHeatmap(planId: string | null, enabled = true) {
  return useQuery({
    queryKey: ['heatmap', planId],
    queryFn: () => api.getHeatmap(planId!),
    enabled: Boolean(planId) && enabled,
    staleTime: Infinity,
    retry: 2,
  })
}
