import { useCallback, useEffect, useState } from 'react'

import { AppHeader } from '@/components/AppHeader'
import { MobileTabs, type MobileView } from '@/components/MobileTabs'
import { Alert, Card } from '@/components/ui'
import { ApiStatusBanner } from '@/features/health/ApiStatusBanner'
import { ForecastSlider } from '@/features/heatmap/ForecastSlider'
import { clampHour } from '@/features/heatmap/heatmapData'
import { HeatmapLayer } from '@/features/heatmap/HeatmapLayer'
import { useHeatmap } from '@/features/heatmap/useHeatmap'
import { MapLegend } from '@/features/map/MapLegend'
import { MapView } from '@/features/map/MapView'
import { PlanSkeleton } from '@/features/routes/PlanSkeleton'
import { RouteList } from '@/features/routes/RouteList'
import { TripForm } from '@/features/trip-form/TripForm'
import { TripSummary } from '@/features/trip-form/TripSummary'
import { usePlan, usePlanTrip } from '@/features/trip-form/usePlanTrip'
import { usePlanningProgress } from '@/features/trip-form/usePlanningProgress'
import { cn } from '@/lib/cn'
import { toDateTimeLocal } from '@/lib/format'
import type { TripPlan } from '@/lib/types'
import { readPlanIdFromUrl, writePlanIdToUrl } from '@/lib/url'

export default function App() {
  const [planId, setPlanId] = useState<string | null>(() => readPlanIdFromUrl())
  const [editing, setEditing] = useState(false)
  const [selectedRouteId, setSelectedRouteId] = useState<string | null>(null)
  const [hour, setHour] = useState(0)
  const [heatmapVisible, setHeatmapVisible] = useState(true)
  const [mobileView, setMobileView] = useState<MobileView>('plan')

  const planQuery = usePlan(planId)
  const plan: TripPlan | null = planQuery.data ?? null

  const onPlanned = useCallback((created: TripPlan) => {
    setPlanId(created.id)
    writePlanIdToUrl(created.id)
    setEditing(false)
    setSelectedRouteId(created.recommended_route_id ?? created.routes[0]?.id ?? null)
    setMobileView('map')
  }, [])
  const planMutation = usePlanTrip(onPlanned)
  const heatmapQuery = useHeatmap(plan?.id ?? null)

  // Checkpoints can be reached after the 48 h window on long trips; never let
  // the slider (or the heatmap expression) go past its end.
  const maxHour = plan?.forecast_window.hours ?? 48
  const changeHour = useCallback((next: number) => setHour(clampHour(next, maxHour)), [maxHour])

  const resetMutation = planMutation.reset
  const resetTrip = useCallback(() => {
    resetMutation()
    setPlanId(null)
    writePlanIdToUrl(null)
    setEditing(false)
    setSelectedRouteId(null)
    setHour(0)
    setMobileView('plan')
  }, [resetMutation])
  const startEditing = useCallback(() => setEditing(true), [])

  const editDefaults = plan
    ? {
        origin: { ...plan.request.origin, full_name: plan.request.origin.full_name },
        destination: {
          ...plan.request.destination,
          full_name: plan.request.destination.full_name,
        },
        departure: toDateTimeLocal(new Date(plan.request.departure_time)),
        loadWeightLb: plan.request.load_weight_lb,
        intervalMiles: plan.request.checkpoint_interval_miles,
      }
    : undefined
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

  const loadingSharedPlan = Boolean(planId) && planQuery.isLoading
  const showForm = editing || (!plan && !loadingSharedPlan)

  return (
    <div className="flex h-dvh flex-col lg:flex-row">
      <aside
        className={cn(
          'w-full shrink-0 flex-col bg-white lg:flex lg:h-full lg:w-[480px] lg:border-r lg:border-slate-200',
          mobileView === 'map' ? 'hidden' : 'flex min-h-0 flex-1 lg:flex-none',
        )}
      >
        <AppHeader />
        <ApiStatusBanner />
        <div className="flex flex-1 flex-col gap-4 overflow-y-auto bg-slate-50/60 p-4">
          {loadingSharedPlan && <PlanSkeleton />}
          {showForm ? (
            <Card className="p-4">
              <TripForm
                onSubmit={planMutation.mutate}
                pending={planMutation.isPending}
                error={planMutation.error}
                defaultValues={editing ? editDefaults : undefined}
                onCancel={editing && plan ? () => setEditing(false) : undefined}
                pendingLabel={progress}
              />
            </Card>
          ) : (
            plan && <TripSummary plan={plan} onEdit={startEditing} onReset={resetTrip} />
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

      <main
        className={cn(
          'relative min-h-0 flex-1',
          mobileView === 'plan' ? 'hidden lg:block' : 'block',
        )}
        aria-label="Map"
      >
        <MapView
          plan={plan}
          selectedRouteId={selectedRouteId}
          onSelectRoute={setSelectedRouteId}
          onCheckpointClick={changeHour}
          activeHourIndex={plan ? hour : null}
          renderUnderlay={(beforeId) =>
            heatmapQuery.data ? (
              <HeatmapLayer
                heatmap={heatmapQuery.data}
                hourIndex={hour}
                visible={heatmapVisible}
                beforeId={beforeId}
              />
            ) : null
          }
        />
        <div className="pointer-events-none absolute top-3 left-3 z-10 hidden md:block [@media(max-height:520px)]:hidden">
          <MapLegend />
        </div>
        {plan && (
          <div className="pointer-events-none absolute inset-x-0 bottom-3 z-10 flex justify-center px-3 lg:bottom-8">
            <ForecastSlider
              plan={plan}
              selectedRoute={selectedRoute}
              hour={hour}
              onHourChange={changeHour}
              visible={heatmapVisible}
              onToggleVisible={() => setHeatmapVisible((v) => !v)}
              loading={heatmapQuery.isPending}
              error={heatmapQuery.isError}
              partial={heatmapQuery.data?.complete === false}
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
      <MobileTabs
        view={mobileView}
        onChange={setMobileView}
        routeCount={plan?.routes.length ?? 0}
      />
    </div>
  )
}
