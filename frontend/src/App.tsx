import { useCallback, useEffect, useState } from 'react'

import { AppHeader } from '@/components/AppHeader'
import { Alert, Card } from '@/components/ui'
import { ApiStatusBanner } from '@/features/health/ApiStatusBanner'
import { MapLegend } from '@/features/map/MapLegend'
import { MapView } from '@/features/map/MapView'
import { RouteList } from '@/features/routes/RouteList'
import { TripForm } from '@/features/trip-form/TripForm'
import { TripSummary } from '@/features/trip-form/TripSummary'
import { usePlan, usePlanTrip } from '@/features/trip-form/usePlanTrip'
import type { TripPlan } from '@/lib/types'
import { readPlanIdFromUrl, writePlanIdToUrl } from '@/lib/url'

export default function App() {
  const [planId, setPlanId] = useState<string | null>(() => readPlanIdFromUrl())
  const [editing, setEditing] = useState(false)
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null)

  const planQuery = usePlan(planId)
  const plan: TripPlan | null = planQuery.data ?? null

  const onPlanned = useCallback((created: TripPlan) => {
    setPlanId(created.id)
    writePlanIdToUrl(created.id)
    setEditing(false)
    setSelectedRouteId(created.recommended_route_id ?? created.routes[0]?.id ?? null)
  }, [])
  const planMutation = usePlanTrip(onPlanned)

  // A plan loaded from a shared URL needs a default selection too.
  const [syncedPlanId, setSyncedPlanId] = useState<string | null>(null)
  if (plan && plan.id !== syncedPlanId) {
    setSyncedPlanId(plan.id)
    setSelectedRouteId(plan.recommended_route_id ?? plan.routes[0]?.id ?? null)
  }

  useEffect(() => {
    if (planQuery.isError) writePlanIdToUrl(null)
  }, [planQuery.isError])

  const showForm = editing || !plan

  return (
    <div className="flex h-dvh flex-col lg:flex-row">
      <aside className="flex w-full shrink-0 flex-col border-b border-slate-200 bg-white lg:h-full lg:w-[440px] lg:border-r lg:border-b-0">
        <AppHeader />
        <ApiStatusBanner />
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto bg-slate-50/60 p-4">
          {showForm ? (
            <Card className="p-4">
              <TripForm
                onSubmit={planMutation.mutate}
                pending={planMutation.isPending}
                error={planMutation.error}
              />
            </Card>
          ) : (
            <TripSummary plan={plan} onEdit={() => setEditing(true)} />
          )}

          {planQuery.isError && (
            <Alert tone="warning" title="That shared plan could not be loaded.">
              It may have expired. Plan a new trip above.
            </Alert>
          )}

          {plan && (
            <RouteList
              plan={plan}
              selectedRouteId={selectedRouteId}
              onSelectRoute={setSelectedRouteId}
            />
          )}
        </div>
      </aside>

      <main className="relative min-h-[55dvh] flex-1 lg:min-h-0" aria-label="Map">
        <MapView
          plan={plan}
          selectedRouteId={selectedRouteId}
          onSelectRoute={setSelectedRouteId}
          activeHourIndex={null}
        />
        <div className="pointer-events-none absolute bottom-8 left-3 z-10 hidden sm:block">
          <MapLegend />
        </div>
        {planMutation.isPending && (
          <div className="absolute inset-x-0 top-3 z-10 flex justify-center">
            <div className="shadow-panel rounded-full bg-slate-900/90 px-4 py-1.5 text-xs font-medium text-white">
              Fetching routes and forecasts…
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
