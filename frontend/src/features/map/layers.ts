import type { LayerProps } from 'react-map-gl/maplibre'

import { RISK_LEVELS, RISK_META, UNKNOWN_RISK_COLOR } from '@/lib/risk'

export const LEVEL_COLOR_EXPRESSION = [
  'match',
  ['get', 'level'],
  ...RISK_LEVELS.flatMap((level) => [level, RISK_META[level].color]),
  UNKNOWN_RISK_COLOR,
] as const

export const ROUTES_HIT_LAYER: LayerProps = {
  id: 'routes-hit',
  type: 'line',
  paint: { 'line-width': 18, 'line-opacity': 0 },
  layout: { 'line-cap': 'round', 'line-join': 'round' },
}

export const ROUTES_OTHER_CASING: LayerProps = {
  id: 'routes-other-casing',
  type: 'line',
  filter: ['!', ['get', 'selected']],
  paint: { 'line-color': '#ffffff', 'line-width': 7, 'line-opacity': 0.9 },
  layout: { 'line-cap': 'round', 'line-join': 'round' },
}

export const ROUTES_OTHER: LayerProps = {
  id: 'routes-other',
  type: 'line',
  filter: ['!', ['get', 'selected']],
  paint: { 'line-color': '#64748b', 'line-width': 3.5, 'line-opacity': 0.75 },
  layout: { 'line-cap': 'round', 'line-join': 'round' },
}

export const SEGMENTS_CASING: LayerProps = {
  id: 'segments-casing',
  type: 'line',
  paint: { 'line-color': '#0f172a', 'line-width': 10, 'line-opacity': 0.35 },
  layout: { 'line-cap': 'round', 'line-join': 'round' },
}

export const SEGMENTS: LayerProps = {
  id: 'segments',
  type: 'line',
  paint: { 'line-color': LEVEL_COLOR_EXPRESSION as unknown as string, 'line-width': 6 },
  layout: { 'line-cap': 'round', 'line-join': 'round' },
}

export const CHECKPOINTS_OTHER: LayerProps = {
  id: 'checkpoints-other',
  type: 'circle',
  filter: ['!', ['get', 'selected']],
  paint: {
    'circle-radius': 3.5,
    'circle-color': LEVEL_COLOR_EXPRESSION as unknown as string,
    'circle-opacity': 0.8,
    'circle-stroke-color': '#ffffff',
    'circle-stroke-width': 1,
  },
}

export const CHECKPOINTS: LayerProps = {
  id: 'checkpoints',
  type: 'circle',
  filter: ['get', 'selected'],
  paint: {
    'circle-radius': ['case', ['get', 'isEndpoint'], 7, 6],
    'circle-color': LEVEL_COLOR_EXPRESSION as unknown as string,
    'circle-stroke-color': '#ffffff',
    'circle-stroke-width': 2,
  },
}

/** Ring drawn around checkpoints whose ETA falls in the slider's current hour. */
export function activeHourLayer(hourIndex: number | null): LayerProps {
  return {
    id: 'checkpoints-active-hour',
    type: 'circle',
    filter: ['all', ['get', 'selected'], ['==', ['get', 'hourIndex'], hourIndex ?? -1]],
    paint: {
      'circle-radius': 13,
      'circle-color': 'rgba(0,0,0,0)',
      'circle-stroke-color': '#0f172a',
      'circle-stroke-width': 2.5,
      'circle-stroke-opacity': 0.9,
    },
  }
}
