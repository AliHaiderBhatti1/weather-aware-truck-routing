import type { FeatureCollection, Point } from 'geojson'

import type { Heatmap } from '@/lib/types'

export interface HeatmapCellProps {
  levels: (number | null)[]
  winds: (number | null)[]
}

export interface HeatmapGeo {
  collection: FeatureCollection<Point, HeatmapCellProps>
  /** Grid spacing in degrees, used to size cells so they tile the corridor. */
  spacingDeg: number
  centerLat: number
}

/** Smallest positive gap between sorted unique values. */
function minGap(values: number[]): number {
  const sorted = [...new Set(values.map((v) => Math.round(v * 1e4) / 1e4))].sort((a, b) => a - b)
  let gap = Infinity
  for (let i = 1; i < sorted.length; i++) gap = Math.min(gap, sorted[i] - sorted[i - 1])
  return Number.isFinite(gap) ? gap : 0.1
}

export function buildHeatmapGeo(heatmap: Heatmap): HeatmapGeo {
  const lats = heatmap.points.map((p) => p.lat)
  const lons = heatmap.points.map((p) => p.lon)
  const spacingDeg = Math.min(minGap(lats), minGap(lons))
  const centerLat = lats.length ? (Math.min(...lats) + Math.max(...lats)) / 2 : 0
  return {
    spacingDeg,
    centerLat,
    collection: {
      type: 'FeatureCollection',
      features: heatmap.points.map((p) => ({
        type: 'Feature',
        geometry: { type: 'Point', coordinates: [p.lon, p.lat] },
        properties: { levels: p.levels, winds: p.wind_mph },
      })),
    },
  }
}

/**
 * Pixel radius at zoom 0 such that neighbouring cells overlap into a
 * continuous field (radius ≈ 1.2× the grid spacing). Web Mercator: 512 px per
 * 360° at zoom 0 (MapLibre's 512 px tiles), scaled by 1/cos(lat) so cells
 * stay round away from the equator.
 */
export function cellRadiusAtZoom0(spacingDeg: number, centerLat: number): number {
  const pxPerDeg = 512 / 360
  const latScale = 1 / Math.max(Math.cos((centerLat * Math.PI) / 180), 0.2)
  return Math.max(spacingDeg * pxPerDeg * latScale * 1.2, 0.05)
}

/** Keep a forecast hour index inside the heatmap's window (0..maxHour). */
export function clampHour(hour: number, maxHour: number): number {
  if (!Number.isFinite(hour)) return 0
  return Math.min(Math.max(0, Math.round(hour)), Math.max(0, maxHour))
}
