import { useMemo } from 'react'
import { Layer, type LayerProps, Source } from 'react-map-gl/maplibre'

import { RISK_META } from '@/lib/risk'
import type { Heatmap } from '@/lib/types'

import { buildHeatmapGeo, cellRadiusAtZoom0, clampHour } from './heatmapData'

interface HeatmapLayerProps {
  heatmap: Heatmap
  hourIndex: number
  visible: boolean
  /** Insert below this layer so routes stay readable on top. */
  beforeId?: string
}

export const HEATMAP_LAYER_ID = 'corridor-heatmap'

/**
 * Corridor risk "heatmap": one blurred, semi-transparent cell per forecast
 * grid point, coloured by the risk level at the selected hour. Scrubbing the
 * slider only swaps the hour index inside the paint expressions, so MapLibre
 * re-styles the existing buffers without re-uploading data.
 */
export function HeatmapLayer({ heatmap, hourIndex, visible, beforeId }: HeatmapLayerProps) {
  const geo = useMemo(() => buildHeatmapGeo(heatmap), [heatmap])

  const layer = useMemo((): LayerProps => {
    // An out-of-range index would make the expression fail and MapLibre would
    // fall back to opaque black circles, so clamp defensively here too.
    const level = ['at', clampHour(hourIndex, heatmap.hours.length - 1), ['get', 'levels']]
    const r0 = cellRadiusAtZoom0(geo.spacingDeg, geo.centerLat)
    const colorByLevel = [
      'match',
      level,
      0,
      RISK_META.low.color,
      1,
      RISK_META.moderate.color,
      2,
      RISK_META.high.color,
      3,
      RISK_META.severe.color,
      4,
      RISK_META.no_travel.color,
      'rgba(0,0,0,0)',
    ]
    const opacityByLevel = ['match', level, 0, 0.14, 1, 0.4, 2, 0.5, 3, 0.58, 4, 0.66, 0]
    return {
      id: HEATMAP_LAYER_ID,
      type: 'circle',
      layout: { visibility: visible ? 'visible' : 'none' },
      paint: {
        'circle-radius': ['interpolate', ['exponential', 2], ['zoom'], 0, r0, 20, r0 * 2 ** 20],
        'circle-blur': 0.9,
        // Expressions are validated by MapLibre at runtime; the style-spec
        // types only model literal values.
        'circle-color': colorByLevel as unknown as string,
        'circle-opacity': opacityByLevel as unknown as number,
      },
    }
  }, [geo, hourIndex, visible, heatmap.hours.length])

  return (
    <Source id="corridor-heatmap-source" type="geojson" data={geo.collection}>
      <Layer {...layer} beforeId={beforeId} />
    </Source>
  )
}
