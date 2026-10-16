export type LngLat = [number, number]

const EARTH_RADIUS_MILES = 3958.7613

export function haversineMiles(a: LngLat, b: LngLat): number {
  const toRad = (deg: number) => (deg * Math.PI) / 180
  const dLat = toRad(b[1] - a[1])
  const dLon = toRad(b[0] - a[0])
  const lat1 = toRad(a[1])
  const lat2 = toRad(b[1])
  const h = Math.sin(dLat / 2) ** 2 + Math.cos(lat1) * Math.cos(lat2) * Math.sin(dLon / 2) ** 2
  return 2 * EARTH_RADIUS_MILES * Math.asin(Math.sqrt(h))
}

/**
 * Split a polyline into consecutive pieces at the given distances from the
 * start. ``cuts`` are in miles along the *true* route; the polyline may be a
 * simplified version, so its own length is rescaled to ``totalMiles``.
 */
export function splitLineAtDistances(
  coords: LngLat[],
  cuts: number[],
  totalMiles: number,
): LngLat[][] {
  if (coords.length < 2) return [coords]
  const cumulative: number[] = [0]
  for (let i = 1; i < coords.length; i++) {
    cumulative.push(cumulative[i - 1] + haversineMiles(coords[i - 1], coords[i]))
  }
  const lineLength = cumulative[cumulative.length - 1]
  const scale = lineLength > 0 ? totalMiles / lineLength : 1

  const pieces: LngLat[][] = []
  let current: LngLat[] = [coords[0]]
  let segment = 0
  const sortedCuts = cuts.filter((c) => c > 0 && c < totalMiles).sort((a, b) => a - b)

  for (const cut of sortedCuts) {
    const target = cut / scale
    while (segment < coords.length - 2 && cumulative[segment + 1] < target) {
      segment++
      current.push(coords[segment])
    }
    const segLen = cumulative[segment + 1] - cumulative[segment]
    const t = segLen > 0 ? (target - cumulative[segment]) / segLen : 0
    const point: LngLat = [
      coords[segment][0] + (coords[segment + 1][0] - coords[segment][0]) * t,
      coords[segment][1] + (coords[segment + 1][1] - coords[segment][1]) * t,
    ]
    current.push(point)
    pieces.push(current)
    current = [point]
  }
  for (let i = segment + 1; i < coords.length; i++) current.push(coords[i])
  pieces.push(current)
  return pieces
}
