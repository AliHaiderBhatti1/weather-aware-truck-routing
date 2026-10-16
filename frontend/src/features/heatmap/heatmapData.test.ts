import { describe, expect, it } from 'vitest'

import { buildHeatmapGeo, cellRadiusAtZoom0 } from './heatmapData'

describe('heatmap geo', () => {
  it('derives grid spacing from the smallest coordinate gap', () => {
    const geo = buildHeatmapGeo({
      start: '',
      hours: [],
      points: [
        { lat: 40.0, lon: -105.0, levels: [0], wind_mph: [1] },
        { lat: 40.1, lon: -105.0, levels: [1], wind_mph: [2] },
        { lat: 40.0, lon: -104.8, levels: [2], wind_mph: [3] },
      ],
    })
    expect(geo.spacingDeg).toBeCloseTo(0.1)
    expect(geo.centerLat).toBeCloseTo(40.05)
    expect(geo.collection.features).toHaveLength(3)
    expect(geo.collection.features[2].properties.levels).toEqual([2])
  })

  it('grows the cell radius away from the equator', () => {
    expect(cellRadiusAtZoom0(0.1, 60)).toBeGreaterThan(cellRadiusAtZoom0(0.1, 0))
    expect(cellRadiusAtZoom0(0, 0)).toBeGreaterThan(0)
  })
})
