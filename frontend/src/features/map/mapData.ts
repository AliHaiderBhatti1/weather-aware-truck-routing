import type { Feature, FeatureCollection, LineString, Point } from 'geojson'

import { splitLineAtDistances, type LngLat } from '@/lib/geometry'
import type { RiskLevel } from '@/lib/risk'
import type { Checkpoint, PlannedRoute, TripPlan } from '@/lib/types'

export interface RouteFeatureProps {
  routeId: string
  rank: number
  selected: boolean
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
  selected: boolean
  /** Hour offset from the forecast window start, used to sync with the slider. */
  hourIndex: number
  isEndpoint: boolean
}

export interface MapData {
  routes: FeatureCollection<LineString, RouteFeatureProps>
  segments: FeatureCollection<LineString, SegmentFeatureProps>
  checkpoints: FeatureCollection<Point, CheckpointFeatureProps>
}

export function hourIndexFor(eta: string, windowStart: string): number {
  const diff = new Date(eta).getTime() - new Date(windowStart).getTime()
  return Math.max(0, Math.floor(diff / 3_600_000))
}

function routeLine(route: PlannedRoute, selected: boolean): Feature<LineString, RouteFeatureProps> {
  return {
    type: 'Feature',
    geometry: route.geometry,
    properties: { routeId: route.id, rank: route.rank, selected },
  }
}

function riskSegments(route: PlannedRoute): Feature<LineString, SegmentFeatureProps>[] {
  const cuts = route.checkpoints.slice(1, -1).map((c) => c.distance_from_start_miles)
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
  selected: boolean,
  windowStart: string,
): Feature<Point, CheckpointFeatureProps>[] {
  return route.checkpoints.map((checkpoint) => ({
    type: 'Feature',
    geometry: { type: 'Point', coordinates: [checkpoint.lon, checkpoint.lat] },
    properties: {
      routeId: route.id,
      index: checkpoint.index,
      level: checkpoint.risk?.level ?? 'unknown',
      selected,
      hourIndex: hourIndexFor(checkpoint.eta, windowStart),
      isEndpoint: checkpoint.index === 0 || checkpoint.index === route.checkpoints.length - 1,
    },
  }))
}

/** Build every GeoJSON source the map needs from a plan and the selected route. */
export function buildMapData(plan: TripPlan, selectedRouteId: string | null): MapData {
  const selected = plan.routes.find((r) => r.id === selectedRouteId) ?? plan.routes[0]
  const windowStart = plan.forecast_window.start
  return {
    routes: {
      type: 'FeatureCollection',
      features: plan.routes.map((route) => routeLine(route, route.id === selected?.id)),
    },
    segments: {
      type: 'FeatureCollection',
      features: selected ? riskSegments(selected) : [],
    },
    checkpoints: {
      type: 'FeatureCollection',
      // Selected route last so its markers draw on top.
      features: [...plan.routes]
        .sort((a) => (a.id === selected?.id ? 1 : -1))
        .flatMap((route) => checkpointPoints(route, route.id === selected?.id, windowStart)),
    },
  }
}
