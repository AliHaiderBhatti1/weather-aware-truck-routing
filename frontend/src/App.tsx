import { useCallback, useEffect, useState } from 'react'

import { AppHeader } from '@/components/AppHeader'
import { Alert, Card } from '@/components/ui'
import { ApiStatusBanner } from '@/features/health/ApiStatusBanner'
import { TripForm } from '@/features/trip-form/TripForm'
import { usePlan, usePlanTrip } from '@/features/trip-form/usePlanTrip'
import type { TripPlan } from '@/lib/types'
import { readPlanIdFromUrl, writePlanIdToUrl } from '@/lib/url'

export default function App() {
  const [planId, setPlanId] = useState<string | null>(() => readPlanIdFromUrl())
  const planQuery = usePlan(planId)
  const plan: TripPlan | null = planQuery.data ?? null

  const onPlanned = useCallback((created: TripPlan) => {
    setPlanId(created.id)
    writePlanIdToUrl(created.id)
  }, [])
  const planMutation = usePlanTrip(onPlanned)

  useEffect(() => {
    if (planQuery.isError) writePlanIdToUrl(null)
  }, [planQuery.isError])

  return (
    <div className="flex h-dvh flex-col lg:flex-row">
      <aside className="flex w-full shrink-0 flex-col border-b border-slate-200 bg-white lg:h-full lg:w-[440px] lg:border-r lg:border-b-0">
        <AppHeader />
        <ApiStatusBanner />
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto p-4">
          <Card className="p-4">
            <TripForm
              onSubmit={planMutation.mutate}
              pending={planMutation.isPending}
              error={planMutation.error}
            />
          </Card>
          {planQuery.isError && (
            <Alert tone="warning" title="That shared plan could not be loaded.">
              It may have expired. Plan a new trip above.
            </Alert>
          )}
          {plan && (
            <Card className="p-4 text-sm">
              <p className="font-semibold">
                {plan.routes.length} routes · recommended {plan.recommended_route_id ?? 'none'}
              </p>
              <ul className="mt-2 space-y-1 text-slate-600">
                {plan.routes.map((route) => (
                  <li key={route.id}>
                    #{route.rank} {route.name} · {route.distance_miles} mi · max{' '}
                    {route.summary.max_level}
                  </li>
                ))}
              </ul>
            </Card>
          )}
        </div>
      </aside>
      <main className="relative min-h-[55dvh] flex-1 bg-slate-200 lg:min-h-0" aria-label="Map" />
    </div>
  )
}
