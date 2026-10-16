import { Marker } from 'react-map-gl/maplibre'

import { cn } from '@/lib/cn'
import { formatDuration, formatMiles } from '@/lib/format'
import { RISK_META } from '@/lib/risk'
import type { PlannedRoute } from '@/lib/types'

interface RouteLabelsProps {
  routes: PlannedRoute[]
  selectedRouteId: string | null
  onSelectRoute: (routeId: string) => void
}

/** Position each label at a different fraction of its route so they rarely overlap. */
const ANCHOR_FRACTIONS = [0.5, 0.36, 0.64, 0.25, 0.75]

/** Compact per-route summary pinned to the route line itself. */
export function RouteLabels({ routes, selectedRouteId, onSelectRoute }: RouteLabelsProps) {
  return (
    <>
      {routes.map((route, index) => {
        const coords = route.geometry.coordinates
        if (coords.length === 0) return null
        const fraction = ANCHOR_FRACTIONS[index % ANCHOR_FRACTIONS.length]
        const [lon, lat] = coords[Math.min(coords.length - 1, Math.floor(coords.length * fraction))]
        const selected = route.id === selectedRouteId
        const peak = RISK_META[route.summary.max_level]
        return (
          <Marker key={route.id} longitude={lon} latitude={lat} anchor="center">
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation()
                onSelectRoute(route.id)
              }}
              aria-label={`Select route ${route.rank}: ${route.name}`}
              title={route.name}
              className={cn(
                'flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium whitespace-nowrap shadow-md transition-colors',
                selected
                  ? 'border-slate-900 bg-slate-900 text-white'
                  : 'border-slate-200 bg-white/95 text-slate-700 hover:bg-white',
              )}
            >
              <span
                className={cn(
                  'flex h-4 w-4 items-center justify-center rounded-full text-[10px] font-bold',
                  selected ? 'bg-white text-slate-900' : 'bg-slate-900 text-white',
                )}
              >
                {route.rank}
              </span>
              <span>{formatMiles(route.distance_miles)}</span>
              <span className={selected ? 'text-slate-300' : 'text-slate-400'}>·</span>
              <span>{formatDuration(route.duration_seconds)}</span>
              <span
                className="ml-0.5 h-2 w-2 rounded-full ring-1 ring-white"
                style={{ backgroundColor: peak.color }}
                title={`Peak risk: ${peak.label}`}
              />
            </button>
          </Marker>
        )
      })}
    </>
  )
}
