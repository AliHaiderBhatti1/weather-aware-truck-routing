import { describe, expect, it } from 'vitest'

import type { TripPlan } from '@/lib/types'

import { buildMapData, hourIndexFor } from './mapData'

const plan = {
  id: 'p',
  request: {} as TripPlan['request'],
  recommended_route_id: 'a',
  recommendation_reasons: [],
  warnings: [],
  bounds: [
    [0, 0],
    [2, 0],
  ],
  forecast_window: { start: '2026-10-20T08:00:00+00:00', end: '', hours: 48 },
  routes: [
    {
      id: 'a',
      name: 'A',
      source: 'fastest',
      rank: 1,
      recommended: true,
      distance_miles: 138.2,
      duration_seconds: 7200,
      arrival_time: '',
      geometry: {
        type: 'LineString',
        coordinates: [
          [0, 0],
          [1, 0],
          [2, 0],
        ],
      },
      summary: {} as TripPlan['routes'][number]['summary'],
      checkpoints: [
        {
          index: 0,
          lat: 0,
          lon: 0,
          distance_from_start_miles: 0,
          segment_miles: 69,
          eta: '2026-10-20T08:30:00+00:00',
          weather: null,
          risk: { level: 'low' },
        },
        {
          index: 1,
          lat: 0,
          lon: 1,
          distance_from_start_miles: 69.1,
          segment_miles: 69,
          eta: '2026-10-20T09:45:00+00:00',
          weather: null,
          risk: { level: 'severe' },
        },
        {
          index: 2,
          lat: 0,
          lon: 2,
          distance_from_start_miles: 138.2,
          segment_miles: 0,
          eta: '2026-10-20T11:00:00+00:00',
          weather: null,
          risk: null,
        },
      ],
    },
    {
      id: 'b',
      name: 'B',
      source: 'alternative',
      rank: 2,
      recommended: false,
      distance_miles: 10,
      duration_seconds: 100,
      arrival_time: '',
      geometry: {
        type: 'LineString',
        coordinates: [
          [0, 0],
          [0, 0.1],
        ],
      },
      summary: {} as TripPlan['routes'][number]['summary'],
      checkpoints: [],
    },
  ],
} as unknown as TripPlan

describe('buildMapData', () => {
  it('gives each checkpoint the road half-way to its neighbours', () => {
    const data = buildMapData(plan, 'a')
    const segments = data.segments.features
    expect(segments.map((f) => f.properties.level)).toEqual(['low', 'severe', 'unknown'])
    expect(segments[0].geometry.coordinates[0]).toEqual([0, 0])
    // Cuts at the midpoints between checkpoints (lon 0.5 and 1.5 on this line).
    expect(segments[0].geometry.coordinates.at(-1)![0]).toBeCloseTo(0.5, 2)
    expect(segments[1].geometry.coordinates.at(-1)![0]).toBeCloseTo(1.5, 2)
    expect(segments[2].geometry.coordinates.at(-1)).toEqual([2, 0])
  })

  it('marks the selected route and orders its checkpoints last', () => {
    const data = buildMapData(plan, 'a')
    expect(data.routes.features.map((f) => f.properties.selected)).toEqual([true, false])
    expect(data.checkpoints.features.every((f) => f.properties.selected)).toBe(true)
    expect(data.checkpoints.features.map((f) => f.properties.hourIndex)).toEqual([0, 1, 3])
    expect(data.checkpoints.features.map((f) => f.properties.isEndpoint)).toEqual([
      true,
      false,
      true,
    ])
  })

  it('falls back to the first route when the selection is unknown', () => {
    const data = buildMapData(plan, 'nope')
    expect(data.segments.features).toHaveLength(3)
  })

  it('computes hour offsets from the forecast window start', () => {
    expect(hourIndexFor('2026-10-20T07:00:00+00:00', '2026-10-20T08:00:00+00:00')).toBe(0)
    expect(hourIndexFor('2026-10-20T10:59:00+00:00', '2026-10-20T08:00:00+00:00')).toBe(2)
  })
})
