import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { api } from '@/lib/api'
import type { TripPlan } from '@/lib/types'

export function usePlanTrip(onPlanned: (plan: TripPlan) => void) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: api.createPlan,
    onSuccess: (plan) => {
      queryClient.setQueryData(['plan', plan.id], plan)
      onPlanned(plan)
    },
  })
}

export function usePlan(planId: string | null) {
  return useQuery({
    queryKey: ['plan', planId],
    queryFn: () => api.getPlan(planId!),
    enabled: Boolean(planId),
    staleTime: Infinity,
  })
}
