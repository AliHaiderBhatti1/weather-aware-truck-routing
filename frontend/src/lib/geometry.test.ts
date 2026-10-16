import { describe, expect, it } from 'vitest'

import { haversineMiles, splitLineAtDistances, type LngLat } from './geometry'

describe('geometry helpers', () => {
  it('measures great-circle distance', () => {
    const denver: LngLat = [-104.99, 39.74]
    const slc: LngLat = [-111.89, 40.76]
    expect(haversineMiles(denver, slc)).toBeCloseTo(371, 0)
  })

  it('splits a line into pieces at cumulative distances', () => {
    const line: LngLat[] = [
      [0, 0],
      [1, 0],
      [2, 0],
    ]
    const total = haversineMiles(line[0], line[2])
    const pieces = splitLineAtDistances(line, [total / 4, total / 2], total)

    expect(pieces).toHaveLength(3)
    expect(pieces[0][0]).toEqual([0, 0])
    expect(pieces[0].at(-1)![0]).toBeCloseTo(0.5, 2)
    expect(pieces[1][0]).toEqual(pieces[0].at(-1))
    expect(pieces[1].at(-1)![0]).toBeCloseTo(1, 2)
    expect(pieces[2].at(-1)).toEqual([2, 0])
  })

  it('ignores cuts outside the line and keeps a single piece', () => {
    const line: LngLat[] = [
      [0, 0],
      [1, 0],
    ]
    const total = haversineMiles(line[0], line[1])
    expect(splitLineAtDistances(line, [0, total, total + 5], total)).toEqual([line])
  })
})
