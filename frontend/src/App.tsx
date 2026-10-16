import { useCallback, useEffect, useState } from 'react'

import { AppHeader } from '@/components/AppHeader'
import { Alert, Card } from '@/components/ui'
import { ApiStatusBanner } from '@/features/health/ApiStatusBanner'
import { ForecastSlider } from '@/features/heatmap/ForecastSlider'
import { HeatmapLayer } from '@/features/heatmap/HeatmapLayer'
import { useHeatmap } from '@/features/heatmap/useHeatmap'
import { MapLegend } from '@/features/map/MapLegend'
import { MapView } from '@/features/map/MapView'
import { RouteList } from '@/features/routes/RouteList'
import { TripForm } from '@/features/trip-form/TripForm'
import { TripSummary } from '@/features/trip-form/TripSummary'
import { usePlan, usePlanTrip } from '@/features/trip-form/usePlanTrip'
import { usePlanningProgress } from '@/features/trip-form/usePlanningProgress'
import type { TripPlan } from '@/lib/types'
import { readPlanIdFromUrl, writePlanIdToUrl } from '@/lib/url'

export default function App() {
  const [planId, setPlanId] = useState<string | null>(() => readPlanIdFromUrl())
  const [editing, setEditing] = useState(false)
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null)
  const [hour, setHour] = useState(0)
  const [heatmapVisible, setHeatmapVisible] = useState(true)

  const planQuery = usePlan(planId)
  const plan: TripPlan | null = planQuery.data ?? null

  const onPlanned = useCallback((created: TripPlan) => {
    setPlanId(created.id)
    writePlanIdToUrl(created.id)
    setEditing(false)
    setSelectedRouteId(created.recommended_route_id ?? created.routes[0]?.id ?? null)
  }, [])
  const planMutation = usePlanTrip(onPlanned)
  const heatmapQuery = useHeatmap(plan?.id ?? null)
  const progress = usePlanningProgress(planMutation.isPending)
  const selectedRoute = plan?.routes.find((r) => r.id === selectedRouteId) ?? null

  // A plan loaded from a shared URL needs a default selection too.
  const [syncedPlanId, setSyncedPlanId] = useState<string | null>(null)
  if (plan && plan.id !== syncedPlanId) {
    setSyncedPlanId(plan.id)
    setSelectedRouteId(plan.recommended_route_id ?? plan.routes[0]?.id ?? null)
    setHour(0)
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
          onCheckpointClick={setHour}
          activeHourIndex={plan ? hour : null}
          underlay={
            heatmapQuery.data ? (
              <HeatmapLayer heatmap={heatmapQuery.data} hourIndex={hour} visible={heatmapVisible} />
            ) : null
          }
        />
        <div className="pointer-events-none absolute top-3 left-3 z-10 hidden md:block">
          <MapLegend />
        </div>
        {plan && (
          <div className="pointer-events-none absolute inset-x-0 bottom-3 z-10 flex justify-center px-3 lg:bottom-8">
            <ForecastSlider
              plan={plan}
              selectedRoute={selectedRoute}
              hour={hour}
              onHourChange={setHour}
              visible={heatmapVisible}
              onToggleVisible={() => setHeatmapVisible((v) => !v)}
              loading={heatmapQuery.isPending}
              error={heatmapQuery.isError}
            />
          </div>
        )}
        {!plan && !planMutation.isPending && !planQuery.isLoading && (
          <div className="pointer-events-none absolute inset-x-0 top-1/2 z-10 flex -translate-y-1/2 justify-center px-4">
            <div className="shadow-panel max-w-sm rounded-2xl border border-slate-200 bg-white/90 p-5 text-center backdrop-blur">
              <p className="text-sm font-semibold text-slate-900">Plan a trip to see routes here</p>
              <p className="mt-1 text-xs leading-relaxed text-slate-500">
                Three route options, weather sampled at the truck's ETA along each one, risk scored
                against your load, and a 48-hour corridor heatmap.
              </p>
            </div>
          </div>
        )}
        {progress && (
          <div className="absolute inset-x-0 top-3 z-10 flex justify-center" role="status">
            <div className="shadow-panel flex items-center gap-2 rounded-full bg-slate-900/90 px-4 py-1.5 text-xs font-medium text-white">
              <span className="h-1.5 w-1.5 animate-pulse rounded-full bg-sky-300" />
              {progress}
            </div>
          </div>
        )}
      </main>
    </div>
  )
}
