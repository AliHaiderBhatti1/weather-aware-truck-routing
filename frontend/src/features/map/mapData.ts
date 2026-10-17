import type { Feature, FeatureCollection, LineString, Point } from 'geojson'

import { splitLineAtDistances, type LngLat } from '@/lib/geometry'
import type { RiskLevel } from '@/lib/risk'
import type { Checkpoint, PlannedRoute, TripPlan } from '@/lib/types'

export interface RouteFeatureProps {
  routeId: string
  rank: number
}

export interface SegmentFeatureProps {
  routeId: string
  level: RiskLevel | 'unknown'
  checkpointIndex: number
}

export interface CheckpointFeatureProps {
  routeId: string
  index: number
  level: RiskLevel | 'unknown'
  /** Hour offset from the forecast window start, used to sync with the slider. */
  hourIndex: number
  isEndpoint: boolean
}

/** Sources that depend only on the plan; selection is applied with layer filters. */
export interface PlanSources {
  routes: FeatureCollection<LineString, RouteFeatureProps>
  checkpoints: FeatureCollection<Point, CheckpointFeatureProps>
}

export function hourIndexFor(eta: string, windowStart: string): number {
  const diff = new Date(eta).getTime() - new Date(windowStart).getTime()
  return Math.max(0, Math.floor(diff / 3_600_000))
}

function routeLine(route: PlannedRoute): Feature<LineString, RouteFeatureProps> {
  return {
    type: 'Feature',
    geometry: route.geometry,
    properties: { routeId: route.id, rank: route.rank },
  }
}

function riskSegments(route: PlannedRoute): Feature<LineString, SegmentFeatureProps>[] {
  // Each checkpoint represents the road half-way to its neighbours (same rule
  // the API uses for risk miles), so cut the line at the midpoints.
  const cuts = route.checkpoints
    .slice(0, -1)
    .map(
      (c, i) =>
        (c.distance_from_start_miles + route.checkpoints[i + 1].distance_from_start_miles) / 2,
    )
  const pieces = splitLineAtDistances(
    route.geometry.coordinates as LngLat[],
    cuts,
    route.distance_miles,
  )
  return pieces.map((coords, index) => {
    const checkpoint: Checkpoint | undefined = route.checkpoints[index]
    return {
      type: 'Feature',
      geometry: { type: 'LineString', coordinates: coords },
      properties: {
        routeId: route.id,
        level: checkpoint?.risk?.level ?? 'unknown',
        checkpointIndex: index,
      },
    }
  })
}

function checkpointPoints(
  route: PlannedRoute,
  windowStart: string,
): Feature<Point, CheckpointFeatureProps>[] {
  return route.checkpoints.map((checkpoint) => ({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [checkpoint.lon, checkpoint.lat] },
    properties: {
      routeId: route.id,
      index: checkpoint.index,
      level: checkpoint.risk?.level ?? 'unknown',
      hourIndex: hourIndexFor(checkpoint.eta, windowStart),
      isEndpoint: checkpoint.index === 0 || checkpoint.index === route.checkpoints.length - 1,
    },
  }))
}

/** The selected route's id, falling back to the first route. */
export function resolveSelectedRouteId(
  plan: TripPlan,
  selectedRouteId: string | null,
): string | null {
  return plan.routes.find((r) => r.id === selectedRouteId)?.id ?? plan.routes[0]?.id ?? null
}

/** Route lines and checkpoints for every route, built once per plan. */
export function buildPlanSources(plan: TripPlan): PlanSources {
  const windowStart = plan.forecast_window.start
  return {
    routes: { type: 'FeatureCollection', features: plan.routes.map(routeLine) },
    checkpoints: {
      type: 'FeatureCollection',
      features: plan.routes.flatMap((route) => checkpointPoints(route, windowStart)),
    },
  }
}

/** Risk-coloured segments for the selected route only. */
export function buildSegments(
  plan: TripPlan,
  selectedRouteId: string | null,
): FeatureCollection<LineString, SegmentFeatureProps> {
  const id = resolveSelectedRouteId(plan, selectedRouteId)
  const route = plan.routes.find((r) => r.id === id)
  return { type: 'FeatureCollection', features: route ? riskSegments(route) : [] }
}
